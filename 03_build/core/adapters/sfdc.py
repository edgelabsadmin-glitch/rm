"""
SPEC-012 — Salesforce Signal Source Adapter (read-only).

Polls eight in-scope objects via the `sf` CLI (Decision 14: --target-org
production, API v62) and normalizes each record into an Episode. SOQL field
sets + the 14-value risk-Case taxonomy are lifted from
rm-intelligence-agent/src/sfdc_pull.py and extended with Case Description +
Details__c as first-class content (Decision 35) and Account.Segment__c (tier).

Read-only by contract (§6 rule 6): no SFDC writes here — those go through the
Action Queue dispatch handlers (spec 032) with per-write human approval.

Triggered in production by the Activepieces `sfdc_poll_changes` flow (5-min
cron) which fans each changed record out to /webhooks/sfdc → receive_webhook.
list_recent_events is the poll/backfill path (also used directly in tests).
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
UTC = timezone.utc
from uuid import uuid4

from core.adapters.base import SignalSourceAdapter
from core.adapters.episode import EntityRef, Episode, RawEvent

# Risk-tagged Case categories (rm-intelligence-agent/src/sfdc_pull.py:109-115).
RISK_CATEGORIES: tuple[str, ...] = (
    "Risk - Talent Competency",
    "Risk - Poor Talent Experience",
    "Risk - Resignation",
    "Risk - Talent Professionalism",
    "Risk - Customer Payment Failure",
    "Risk - ADP",
    "Risk – Role Change",  # en-dash, per SFDC taxonomy
    "Risk – Emergency Leaves",  # en-dash
    "Poor Experience with Edge",
    "Competitor",
    "Performance",
    "Relationship Management",
    "Business Performance",
    "Business Needs",
)


@dataclass
class _ObjectSpec:
    fields: tuple[str, ...]
    account_field: str | None  # field holding the Account Id (for candidate entity)
    name_field: str  # field used for the Episode subject
    is_talent: bool = False  # Associates__c → also emit a Talent candidate entity


# Eight in-scope objects (Design 02 / spec 012). Field sets lifted + extended.
OBJECTS: dict[str, _ObjectSpec] = {
    "Account": _ObjectSpec(
        fields=("Id", "Name", "LastModifiedDate", "Segment__c", "Industry", "Type"),
        account_field="Id",
        name_field="Name",
    ),
    "Contact": _ObjectSpec(
        fields=("Id", "Name", "LastModifiedDate", "AccountId", "Title", "Email"),
        account_field="AccountId",
        name_field="Name",
    ),
    "Opportunity": _ObjectSpec(
        fields=("Id", "Name", "LastModifiedDate", "AccountId", "StageName", "Type", "CloseDate"),
        account_field="AccountId",
        name_field="Name",
    ),
    "RM_Outreach__c": _ObjectSpec(
        fields=(
            "Id",
            "Name",
            "CreatedDate",
            "LastModifiedDate",
            "Account__c",
            "Customer_Health__c",
            "Expansion_Sentiment__c",
            "Satisfaction_with_Talent__c",
            "Churn_Probability__c",
            "Expansion_Probability__c",
            "EBR_Date__c",
            "EBR_Description__c",
            "Description__c",
            "Competitor_Analysis__c",
        ),
        account_field="Account__c",
        name_field="Name",
    ),
    "Associates__c": _ObjectSpec(
        fields=(
            "Id",
            "Name",
            "CreatedDate",
            "LastModifiedDate",
            "Account__c",
            "Stage__c",
            "Risk_level__c",
            "Risk_Details__c",
            "Type__c",
            "Role__c",
            "Start_Date__c",
            "End_Date__c",
            "Prior_Associate_Replaced__c",
            "Description__c",
        ),
        account_field="Account__c",
        name_field="Name",
        is_talent=True,
    ),
    "Account_Plan__c": _ObjectSpec(
        fields=("Id", "Name", "CreatedDate", "LastModifiedDate", "Account__c"),
        account_field="Account__c",
        name_field="Name",
    ),
    "Case": _ObjectSpec(
        fields=(
            "Id",
            "CaseNumber",
            "CreatedDate",
            "ClosedDate",
            "IsClosed",
            "Subject",
            "Status",
            "Categories__c",
            "Description",
            "Details__c",
            "Associate__c",
            "AccountId",
        ),
        account_field="AccountId",
        name_field="CaseNumber",
    ),
    "affectlayer__Engagement__c": _ObjectSpec(
        fields=("Id", "Name", "CreatedDate", "LastModifiedDate"),
        account_field=None,
        name_field="Name",
    ),
}


def _soql_datetime(dt: datetime) -> str:
    """SOQL datetime literal (unquoted, UTC, e.g. 2026-05-01T00:00:00Z)."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _quote_list(values: tuple[str, ...]) -> str:
    return "(" + ",".join("'" + v.replace("'", "\\'") + "'" for v in values) + ")"


class SFDCAdapter(SignalSourceAdapter):
    SOURCE_NAME = "salesforce"
    SUPPORTS_WEBHOOKS = True  # via the Activepieces poll→/webhooks/sfdc fan-out
    SUPPORTS_BACKFILL = True

    def __init__(self, target_org: str | None = None, sf_bin: str = "sf") -> None:
        self.target_org = target_org or os.environ.get("PULSE_SFDC_TARGET_ORG", "production")
        self.sf_bin = sf_bin

    # ── SOQL via sf CLI ──────────────────────────────────────────────────────
    def build_query(self, object_name: str, since: datetime) -> str:
        spec = OBJECTS[object_name]
        where = [f"LastModifiedDate >= {_soql_datetime(since)}"]
        if object_name == "Case":
            where.append(f"Categories__c IN {_quote_list(RISK_CATEGORIES)}")
        return (
            f"SELECT {','.join(spec.fields)} FROM {object_name} "
            f"WHERE {' AND '.join(where)} ORDER BY LastModifiedDate DESC"
        )

    def _run_soql(self, query: str) -> list[dict]:
        cmd = [
            self.sf_bin,
            "data",
            "query",
            "--target-org",
            self.target_org,
            "--query",
            query,
            "--json",
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if p.returncode != 0:
            raise RuntimeError(f"SOQL failed ({p.returncode}): {p.stderr[:300]} | {query[:160]}")
        return json.loads(p.stdout)["result"].get("records", [])

    # ── Adapter contract ─────────────────────────────────────────────────────
    async def list_recent_events(self, since: datetime) -> list[RawEvent]:
        """Poll all in-scope objects for records modified since `since`.

        Resilient per object: a failing object (schema gap on the org) is skipped
        rather than aborting the whole poll. Associates__c records also record a
        stage observation (Q142)."""
        events: list[RawEvent] = []
        for object_name, spec in OBJECTS.items():
            try:
                records = self._run_soql(self.build_query(object_name, since))
            except (RuntimeError, KeyError, ValueError):
                continue  # schema gap / empty object — skip, don't abort the poll
            for rec in records:
                rec.pop("attributes", None)
                events.append(
                    {
                        "source": self.SOURCE_NAME,
                        "source_event_id": rec.get("Id", ""),
                        "source_url": None,
                        "payload": {"object_type": object_name, "record": rec},
                    }
                )
                if spec.is_talent and rec.get("Stage__c"):
                    await record_associate_stage(
                        associate_id=rec["Id"],
                        account_id=rec.get("Account__c"),
                        stage=rec["Stage__c"],
                        observed_at=rec.get("LastModifiedDate"),
                    )
        return events

    async def receive_webhook(self, payload: dict, headers: dict) -> list[RawEvent]:
        """Activepieces posts one changed record: {object_type, record}."""
        object_type = payload.get("object_type")
        record = payload.get("record")
        if not object_type or object_type not in OBJECTS or not isinstance(record, dict):
            raise ValueError(f"malformed sfdc webhook payload: {str(payload)[:120]}")
        record.pop("attributes", None)
        return [
            {
                "source": self.SOURCE_NAME,
                "source_event_id": record.get("Id", ""),
                "source_url": None,
                "payload": {"object_type": object_type, "record": record},
            }
        ]

    async def fetch_full(self, event: RawEvent) -> RawEvent:
        # SFDC poll/webhook records already carry full field sets — no hydration.
        return event

    def normalize(self, raw: RawEvent) -> Episode:
        payload = raw.get("payload", {})
        object_type: str = payload["object_type"]
        record: dict = payload["record"]
        spec = OBJECTS[object_type]
        record_id = record.get("Id", "")

        content: dict = {"object_type": object_type, "record_id": record_id, "fields": record}
        tags = ["sfdc", object_type.lower()]
        if object_type == "Case":
            # Decision 35: full narrative, not truncated.
            content["description_text"] = record.get("Description") or ""
            content["details_text"] = record.get("Details__c") or ""
            if record.get("Categories__c"):
                tags.append("risk-tagged")

        return Episode(
            episode_id=uuid4(),
            dedup_key=self.dedup_key(raw),
            source=self.SOURCE_NAME,
            source_event_id=record_id,
            source_url=None,
            source_timestamp=_parse_dt(record.get("LastModifiedDate")),
            content_type="json",
            content=content,
            subject=f"{object_type} {record.get(spec.name_field) or record_id}",
            description=f"Salesforce {object_type} change",
            candidate_entities=_candidate_entities(object_type, record, spec),
            tags=tags,
            ingested_at=datetime.now().astimezone(),
            processing_state="normalized",
        )

    def dedup_key(self, raw: RawEvent) -> str:
        payload = raw.get("payload", {})
        object_type = payload["object_type"]
        record = payload["record"]
        last_mod = record.get("LastModifiedDate") or record.get("CreatedDate") or ""
        return f"sfdc:{object_type}:{record.get('Id', '')}:{last_mod}"


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now().astimezone()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now().astimezone()


def _candidate_entities(object_type: str, record: dict, spec: _ObjectSpec) -> list[EntityRef]:
    out: list[EntityRef] = []
    if spec.account_field and record.get(spec.account_field):
        out.append({"type": "Customer", "sfdc_id": record[spec.account_field]})
    if spec.is_talent and record.get("Id"):
        ref: EntityRef = {"type": "Talent", "sfdc_id": record["Id"]}
        if record.get("Name"):
            ref["name"] = record["Name"]
        out.append(ref)
    if object_type == "Case" and record.get("Associate__c"):
        out.append({"type": "Talent", "sfdc_id": record["Associate__c"]})
    return out


async def record_associate_stage(
    associate_id: str, account_id: str | None, stage: str, observed_at: str | None
) -> None:
    """Record an observed Associates__c stage (Q142). Idempotent per
    (associate_id, stage, observed_at)."""
    from core.db import get_pool

    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO pulse.associate_stage_history "
            "(associate_id, account_id, stage, observed_at) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (associate_id, stage, observed_at) DO NOTHING;",
            (associate_id, account_id, stage, _parse_dt(observed_at)),
        )
