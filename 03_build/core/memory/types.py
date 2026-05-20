"""
SPEC-005 — Three-Graph composition: typed entities + edges (Design 01).

One physical Kuzu graph, three logical lenses (Temporal Context / Skills-lite /
Account-Talent Relationship) discriminated by node-type and edge-type filters.
This module declares the Phase-1-locked schema as Pydantic models and the
registries Graphiti consumes at ``add_episode`` time:

    - ENTITY_TYPES   dict[str, type[BaseModel]]                (8 entities)
    - EDGE_TYPES     dict[str, type[BaseModel]]                (10 edges)
    - EDGE_TYPE_MAP  dict[tuple[str, str], list[str]]          (allowed endpoints)

Design 01 §"Entity types"/§"Edge types" is the source of truth; the models below
map 1:1 to those tables. Custom *attributes* (properties beyond Graphiti's
built-in name/summary/fact + the bi-temporal interval) are kept deliberately
small in Phase 1 — the graph stores *facts and relationships*, not opinions
(Design 01 §"What this is NOT").

Reserved attribute names (uuid, name, summary, fact, created_at, valid_at,
invalid_at, group_id, …) are owned by Graphiti and must never appear as fields
here, so every property below uses a Pulse-specific name.

Q151 (filed during the spec-005 harness run): enum-shaped attributes are typed
as ``str | None`` with the allowed values documented in the field description,
NOT as strict ``Literal``. Graphiti's extractor emits a ``'<UNKNOWN>'`` sentinel
when it cannot determine a value, which fails a strict Literal and forces a
costly LLM retry. Documented strings keep the Design 01 intent (the description
guides extraction) while making ingestion robust.
"""

from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# Entity types (Design 01 §"Entity types") — 8 Phase-1-locked nodes.
# Each model's docstring guides LLM extraction; fields become node attributes.
# The dict KEY is the type name Graphiti uses (also the key in EDGE_TYPE_MAP).
# ─────────────────────────────────────────────────────────────────────────────


class Customer(BaseModel):
    """An EDGE client account (SFDC Account). The entity a book-of-business is built around."""

    tier: str | None = Field(
        default=None, description="Account tier, when stated: SMB | Mid-Market | Enterprise."
    )


class Talent(BaseModel):
    """A placed associate (SFDC Associates__c) — EDGE-supplied talent working at a Customer."""

    stage: str | None = Field(
        default=None, description="Current placement stage: Active | Replaced | Terminated."
    )
    role: str | None = Field(default=None, description="Placement role, e.g. 'Dental Coder II'.")


class RM(BaseModel):
    """A Relationship Manager (SFDC User with role=RM) who owns Customer and Talent records."""


class Contact(BaseModel):
    """A customer-side stakeholder (SFDC Contact): champion, decision-maker, or detractor."""

    stakeholder_role: str | None = Field(
        default=None,
        description="Relationship posture toward EDGE, when discernible: "
        "champion | decision-maker | detractor | other.",
    )


class Case(BaseModel):
    """A risk-tagged formal issue (SFDC Case). The formal-issue layer over talent/customers."""

    risk_category: str | None = Field(
        default=None, description="Risk category, e.g. 'Risk - Talent Competency'."
    )
    case_status: str | None = Field(
        default=None, description="Case lifecycle status: Open | Closed | Escalated."
    )


class Opportunity(BaseModel):
    """A renewal or expansion pipeline item (SFDC Opportunity)."""

    opportunity_type: str | None = Field(
        default=None, description="Pipeline category: Renewal | Expansion | New."
    )
    stage: str | None = Field(default=None, description="Sales stage, when stated.")


class Skill(BaseModel):
    """A normalized occupational tag (role-catalog code), e.g. 'medical-coder-ii'. Phase-1 lite."""

    catalog_code: str | None = Field(
        default=None, description="Role-catalog code; canonical key for the skill."
    )
    vertical: str | None = Field(
        default=None,
        description="EDGE vertical the skill belongs to: Insurance | Medical | Dental.",
    )


class AccountPlan(BaseModel):
    """A strategic account plan (SFDC Account_Plan__c). Read-only in Phase 1."""


# ─────────────────────────────────────────────────────────────────────────────
# Edge types (Design 01 §"Edge types") — 10 Phase-1-locked, bi-temporal edges.
# Graphiti owns valid_at/invalid_at/created_at/expired_at; models add only the
# Pulse-specific attributes. Per Q27 the `manages` two-flavor distinction is
# carried as a `side` property (keeps the locked count at 10) and is also
# expressed structurally in EDGE_TYPE_MAP (RM→Customer vs RM→Talent).
# ─────────────────────────────────────────────────────────────────────────────


class placed_at(BaseModel):  # noqa: N801 — Graphiti edge-type names are snake_case verbs.
    """Talent → Customer. A placement: this associate works (or worked) at this client."""

    role: str | None = Field(default=None, description="Role held in the placement.")


class manages(BaseModel):  # noqa: N801
    """RM → Customer or Talent. Books-of-business ownership."""

    side: str | None = Field(
        default=None,
        description="Which side of the book this edge represents: 'customer' or 'talent' "
        "(Q27: distinct so an RM can be reassigned independently on each side).",
    )


class raised_concern_about(BaseModel):  # noqa: N801
    """Customer/Talent → Customer/Talent/Topic. A specific worry surfaced in a call or note."""

    concern: str | None = Field(default=None, description="The concern in a short phrase.")


class replaced_by(BaseModel):  # noqa: N801
    """Talent → Talent. Chain of replacement (from Prior_Associate_Replaced__c)."""

    reason: str | None = Field(default=None, description="Why the replacement happened.")


class speaks_in_call(BaseModel):  # noqa: N801
    """Contact/RM → Episode. Provenance: which human said what in which call."""

    speaker_role: str | None = Field(
        default=None, description="The speaker's role/title, when stated."
    )


class has_skill(BaseModel):  # noqa: N801
    """Talent → Skill. Phase-1 lite (no drift tracking yet)."""


class reports_to(BaseModel):  # noqa: N801
    """Contact → Contact. Customer-side org chart, when known."""


class mentions(BaseModel):  # noqa: N801
    """Episode → Customer/Talent/Topic. Extracted by the LLM during ingestion."""


class escalated_via(BaseModel):  # noqa: N801
    """Case → Talent or Customer. Joins a risk-tagged Case to the entity it is about."""


class has_plan(BaseModel):  # noqa: N801
    """Customer → AccountPlan. Strategic-plan attachment."""


# ─────────────────────────────────────────────────────────────────────────────
# Registries — passed to Graphiti.add_episode (see core/memory/graph.py).
# ─────────────────────────────────────────────────────────────────────────────

ENTITY_TYPES: dict[str, type[BaseModel]] = {
    "Customer": Customer,
    "Talent": Talent,
    "RM": RM,
    "Contact": Contact,
    "Case": Case,
    "Opportunity": Opportunity,
    "Skill": Skill,
    "AccountPlan": AccountPlan,
}

EDGE_TYPES: dict[str, type[BaseModel]] = {
    "placed_at": placed_at,
    "manages": manages,
    "raised_concern_about": raised_concern_about,
    "replaced_by": replaced_by,
    "speaks_in_call": speaks_in_call,
    "has_skill": has_skill,
    "reports_to": reports_to,
    "mentions": mentions,
    "escalated_via": escalated_via,
    "has_plan": has_plan,
}

# Which edge types may connect a given (source_entity, target_entity) pair.
# Keys use the ENTITY_TYPES names; "Entity" is Graphiti's default/un-typed node
# (used here for LLM-extracted Topics, which are not a Phase-1 typed entity —
# see Q29/Q149). The ("Entity", "Entity") catch-all keeps every Pulse edge type
# reachable when an endpoint is extracted without a Pulse type, so demo
# extraction degrades gracefully rather than dropping a relationship.
EDGE_TYPE_MAP: dict[tuple[str, str], list[str]] = {
    ("Talent", "Customer"): ["placed_at", "raised_concern_about"],
    ("RM", "Customer"): ["manages"],
    ("RM", "Talent"): ["manages"],
    ("Customer", "Customer"): ["raised_concern_about"],
    ("Customer", "Talent"): ["raised_concern_about"],
    ("Talent", "Talent"): ["raised_concern_about", "replaced_by"],
    ("Customer", "Entity"): ["raised_concern_about"],
    ("Talent", "Entity"): ["raised_concern_about"],
    ("Talent", "Skill"): ["has_skill"],
    ("Contact", "Contact"): ["reports_to"],
    ("Case", "Talent"): ["escalated_via"],
    ("Case", "Customer"): ["escalated_via"],
    ("Customer", "AccountPlan"): ["has_plan"],
    # Catch-all: keep all Pulse edge types reachable for un-typed endpoints
    # (provenance edges speaks_in_call/mentions are episode-centric and surface
    #  here rather than as entity-pair constraints).
    ("Entity", "Entity"): list(EDGE_TYPES.keys()),
}
