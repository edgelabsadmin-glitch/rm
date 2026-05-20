# Design 09 — Three-Tier Role Model

**Phase:** 2 (Design)
**Tier:** 3 — late Phase 2 / extending into Phase 3
**Status:** Draft, Phase 2

---

## Purpose

Pulse has three user tiers and a deliberately shared cross-tier view. PM_CONTEXT memory `project_role_model` locks the shape: **Admin / Manager / RM scoped via SFDC ownership + shared Overall view.** This spec turns that into concrete scope rules, the RBAC enforcement layer, and the Admin console surface for tuning the policy module (Design 04).

---

## Inputs

- **Salesforce ownership data:** `User.Id`, `Account.OwnerId`, `Associates__c.RM_Manager__c`, `RM_Outreach__c.Account_Owner_Name__c`. Pulse's tier mapping is **derived from SFDC**, not duplicated.
- **EDGE-supplied tier-membership lists:** Admin user list, Manager-to-RM reporting structure (if not already in SFDC).
- **Authentication identity** from the auth provider (OAuth via Google or Microsoft for Phase 1).

## Outputs

- **Per-request scope filter** that bounds every read/write to what the caller is authorized to see.
- **The Overall view** — a deliberately shared, cross-tier surface for the entire book of business.
- **The Admin console** — tier-aware policy tuning, kill switch, observability.

---

## Behavior

### The three tiers + the Overall surface

| Tier | Who | Sees |
|---|---|---|
| **Admin** | Senior engineering, VP of Client Success, CEO, designated EDGE leadership | Everything. Read/write to policy, kill switch, observability, all RMs' queues, all Customer/Talent/RM profiles. |
| **Manager** | RM leads / VP of CS as RM lead | Their **direct reports' books of business**: action queues, profiles, health rollups, event log scoped to their reports' RM owners. Cannot edit policy. Can edit their direct reports' RM profiles (coaching notes). |
| **RM** | The relationship managers themselves | Their **own book of business**: their assigned customers and the talent placed at those customers. Action queue scoped to actions they own. Profiles of their customers / talent (and their own RM profile). |
| **Overall view** (shared across all tiers) | Everyone | Cross-tier aggregates: portfolio health distribution, cross-account patterns (Skill 10 outputs), advocacy candidates, leadership-report-style summaries. **Designed to invite cross-RM collaboration.** Tier-bounded details (e.g., specific RM's pending escalations) are hidden; cross-account themes and aggregate health are surfaced. |

**Why a shared Overall view:** PM_CONTEXT `project_role_model` is explicit that this surface should exist. RMs benefit from seeing what's happening *across* the book — patterns surfaced by Skill 10, advocacy candidates, leadership reports. Manager-only or Admin-only versions would silo information that's intentionally shared.

### Scope derivation

**Phase 1 scope-derivation logic** (pseudocode, lives in `03_build/auth/scope.py`):

```python
def derive_scope(user: AuthedUser) -> Scope:
    if user.is_admin():
        return Scope.everything()

    if user.is_manager():
        # Manager sees the books of all RMs reporting to them
        direct_report_user_ids = lookup_direct_reports(user.user_id)
        owned_customer_ids = sfdc_query(
            "SELECT Id FROM Account WHERE OwnerId IN :ids",
            ids=direct_report_user_ids,
        )
        return Scope(
            customer_ids=owned_customer_ids,
            talent_ids=lookup_talents_at_customers(owned_customer_ids),
            rm_ids=direct_report_user_ids + [user.user_id],
        )

    # RM tier
    owned_customer_ids = sfdc_query(
        "SELECT Id FROM Account WHERE OwnerId = :id",
        id=user.user_id,
    )
    return Scope(
        customer_ids=owned_customer_ids,
        talent_ids=lookup_talents_at_customers(owned_customer_ids),
        rm_ids=[user.user_id],
    )
```

**Notes:**
- `lookup_direct_reports()` reads from a small `pulse_managers.yaml` config in Phase 1, deferring to a SFDC user-hierarchy field in v1.5+.
- The scope is **derived per-request**, not cached aggressively, so SFDC ownership changes flow through within ~1 minute (SFDC adapter poll cadence).
- **Talent scope follows customer scope:** an RM sees talent at their customers, not based on `RM_Manager__c` directly. Reasoning: if `RM_Manager__c` differs from the customer's `OwnerId` (it can — Associate Managers are sometimes separate), Pulse defaults to customer-side ownership because RM-of-the-customer is the primary surface relationship. The dual-management is captured at the Action Queue layer via routing (Skill 09 cc's Associate Manager).

### Enforcement layer

**Single chokepoint:** every retriever (Design 01 `get_customer_context`, `get_talent_context`, `get_rm_context`) and every event-log query is wrapped in a scope check. The chokepoint is a Python decorator or middleware (Phase 4 implementation detail).

```python
@scope_required
async def get_customer_context(customer_id, *, scope: Scope, ...):
    if customer_id not in scope.customer_ids:
        raise ForbiddenError(...)
    # proceed
```

**Why a single chokepoint** (not per-skill or per-handler checks):
- Skills don't see scope filtering; they receive only allowed data. Reduces accidental-leak surface.
- Audit log records every authorized retriever call + every denied call. Failed-access events are visible to Admin.
- Schema changes (new entity types) need scope updates in one place.

### The Overall view's filtering rules

The Overall view is *not* "everything"; it's "everything that's safe to share cross-tier." Specifically:

| Surfaced on Overall | Hidden on Overall |
|---|---|
| Aggregate health tier distribution | Specific Customer names tied to escalations |
| Cross-account patterns (Skill 10 outputs) — with pseudonymization toggle | Per-RM throughput numbers (those belong on the Manager / Admin view) |
| Advocacy candidates | Per-Talent welfare details |
| Movers (Customer health-tier transitions) — Customer names visible | Reasons for transitions (sensitive — sensitive data link is RM-scoped only) |
| CEO View (Design 08) | RM-specific coaching notes |

**Pseudonymization toggle:** Skill 10's pattern cards include a switch that admins set per pattern card — "show actual customer names" or "show as Customer-A/B/C." Default: show actual names within EDGE-internal Overall (everyone with Pulse access works at EDGE); pseudonymize on export.

### The Admin console (Phase 1 minimum)

Admin-only surface accessible at `/admin`. Four pages:

1. **Policy** — toggles auto-approve list per skill, tier-threshold adjustments, dampening rules (Design 04 policy module).
2. **Kill switch** — global / per-skill / per-customer kill toggles.
3. **Event log explorer** — filterable search of the event log; useful for debugging and audit.
4. **RM profiles** — Admin can edit any RM profile (coaching notes from VP of CS).

Phase 1 implementation is **deliberately minimal** — the four pages above, no more. Adding admin tooling is a v1.5+ candidate when concrete needs surface.

### Authentication

OAuth via Google Workspace (primary) or Microsoft (fallback if EDGE is on Outlook). Phase 1 single-tenant: only `@onedge.co` emails (or whatever EDGE's primary domain is) are authorized. Login → derive tier from a hardcoded admin list + the SFDC user record + the `pulse_managers.yaml` config.

**No multi-factor in Phase 1** — relies on the SSO provider's MFA. Re-evaluate if the auth provider is changed at AWS migration.

---

## EDGE Coverage references

- **§13.5 JD area "Strategy & Operations"** row "Ensure compliance" — RBAC enforcement is a compliance-posture element (scoped access prevents inadvertent cross-RM disclosure).
- **§13.5 row "Effective communication channels"** — Manager visibility into reports' books enables the bridge role.
- **§13.5 row "Bridge customers / Talent / internal teams"** — cross-tier visibility paired with the Action Queue routing.
- **§6 rule 4** "Tier-aware behavior" — RM/Manager/Admin tiers are the user-side counterpart to the Customer SMB/Mid/Enterprise tiers; both shape Pulse's defaults.
- **§13.6 (implicit)** — Pulse's intentionally collaborative Overall view exceeds the EDGE doc's RM-scoped framing.

---

## Open questions

- **Q95** — `pulse_managers.yaml` source of truth. Phase 1 = a hand-maintained yaml. v1.5+ = SFDC user-hierarchy field. PM proposes: yaml for Phase 1, migrate.
- **Q96** — VP of Client Success role mapping. VP is sometimes Manager (over the RM team), sometimes Admin (policy authority). PM proposes: VP = Admin tier. User to confirm.
- **Q97** — Cross-RM collaboration in Overall view: should there be an "ask a teammate" surface (e.g., RM A sees a pattern in B's book and wants to flag it)? PM proposes: v1.5+; Phase 1 keeps Overall read-only across teams.
- **Q98** — Audit-log read access for non-admins. Should Managers see their reports' event-log entries? PM proposes: yes, scoped to their reports' actions.
- **Q99** — Departures handling. When an RM leaves EDGE, their owned customers are re-assigned in SFDC. Does Pulse's scope follow within seconds, hours, or only on re-login? PM proposes: ~5-minute lag via SFDC poll; on-demand admin re-derivation available.

---

## What this is NOT

- **Not a generic RBAC system.** Three roles + an Overall view. Adding more roles is a v1.5+ design exercise.
- **Not custom-permission-set surface.** No "per-Customer ACL" controls. Scope is derived from SFDC ownership.
- **Not a multi-tenant scheme.** Pulse is single-tenant for EDGE in Phase 1. Multi-tenant is v1.5+ (Q43).
- **Not where the Salesforce write-permission is granted.** Pulse holds a single Salesforce service account credential for reads. Writes go through the Action Queue handler (Design 03) with the *RM's* Salesforce identity for OAuth-on-behalf-of, so writes appear in SFDC under the RM's name. (Phase 4 implementation detail.)
- **Not where the kill switch lives.** The kill switch is in the policy module (Design 04); the Admin console *exposes* the toggle.
- **Not an auth-provider lock-in.** OAuth is the primary mechanism; the provider (Google / Microsoft / future) is a config choice.
