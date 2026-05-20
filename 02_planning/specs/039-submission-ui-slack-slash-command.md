# Spec 039 — Submission UI (Slack slash command)

**Maps to:** §14 UI surfaces (submission UI in v1); §13.2 row "Submit voice note or text summary (30 sec)."
**Depends on:** specs 001, 011, 012, 020.
**Effort:** 0.75 day.

## Description

Per §14 (v1 submission UI = Slack slash command per EDGE Workflow 1's "submit voice note or text summary (30 sec)" ask). `/pulse note <text>` from any RM channel → posts to Pulse webhook → ingested as Episode → Skill 01 extracts → surfaces in Action Queue.

## Inputs

- Slack app + slash command configured (admin task; user provisions the Slack workspace).
- RM-to-User-Id mapping (Q63 yaml or SFDC).

## Outputs

- A Slack app config (`pulse_workflows/slack_app_manifest.json`) for the slash command.
- FastAPI endpoint `/webhooks/slack/slash-command`.
- The submitted note becomes an Episode tagged `["slack-submission", "rm-note"]`.

## Definition of Done

- [ ] `/pulse note <text>` from a configured channel produces an Episode within 5s.
- [ ] Slash command signature verified (Slack signing secret).
- [ ] RM identity verified against the workspace; non-RM users receive a "not authorized" response.
- [ ] Submitted notes flow through Skill 01 like any other Episode.
- [ ] Confirmation reply in Slack within 2s ("Captured. Pulse will process and surface in your queue.").

## Tests

- **Unit:** signature verification; RM-identity mapping.
- **Integration:** simulate Slack slash command POST → Episode emitted → assert visible in queue within 30s.

## Signal definitions involved

Skill 01 (signal extraction) consumes these Episodes the same as any other Episode source.

## Open questions

None new — Slack-as-input is in scope; Slack-as-Pulse-output is OUT per `feedback_dont_flood_slack`.

## What this is NOT

- Not Slack notifications outbound (out per `feedback_dont_flood_slack`).
- Not the only submission surface — RM can also type a note via the Pulse web UI (a smaller secondary surface, deferred to v1.5+ if not pulled forward).
