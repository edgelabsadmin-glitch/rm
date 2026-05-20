# Findings: monica

## What it is
Monica is an open-source **Personal Relationship Management (PRM)** application — Laravel + Vue/Inertia, MySQL/Postgres — that helps individuals document and maintain personal relationships with family and friends. Features include contacts, relationships between contacts, reminders (including automatic birthday reminders), notes per contact, activities, tasks, addresses, pet management, a "how we met" log, a diary, document/photo upload, custom genders, custom activity types, labels, multiple vaults and users, 27 language translations. The current `main` branch is a beta v5 rewrite; the stable production version is `4.x`.

## License
**GNU AGPL v3.** **No — not usable for code embedding in EDGE Pulse as a closed-source commercial product.** AGPL applies the strongest copyleft requirement: any networked derivative work must offer source under AGPL. Self-hosting Monica internally as a separate application is permitted; lifting code is not.

## Maturity signal
- Last commit date: 2025-08-30 on the beta `main` branch (older than the rest of this audit; stable `4.x` continues to receive maintenance separately).
- Stars (if external repo): Not pulled in this session; Monica is widely known to be in the tens of thousands of stars.
- Open issues count (if available): Not pulled.
- Published papers / notable adopters: None applicable.
- Subjective maturity: **Production-ready 4.x, beta 5.x.** The product is well-established for personal use; the v5 rewrite is in flux. Not a typical "AI-native CRM" reference — Monica is intentionally NOT a sales tool.

## Data model / schema
- **Contact** — a person you know (the central entity).
- **Relationship** — typed edges between contacts (e.g. spouse, parent, friend).
- **Activity** — something you did with one or more contacts.
- **Note** — free-form text attached to a contact.
- **Reminder** — scheduled prompt (recurring or one-off), with automatic birthday derivations.
- **Diary entry** — daily log; *how your day went*.
- **Document / Photo** — file attachments to contacts.
- **Pet, Address, Contact field** (phone/email/social) — sub-entities under a contact.
- **Vault** — multi-tenant container; a user can own multiple vaults and invite collaborators.
- **Custom genders, custom activity types, labels** — user-extensible taxonomies.

## Architectural patterns worth stealing
- **Relationship-typing as a first-class concept.** Monica's relationships are typed and bidirectional (spouse-of, parent-of, friend-of). EDGE Pulse needs the same for the Account/Talent Relationship Graph (PM_CONTEXT §11 glossary): *placed_at, manages, raised_concern_about, replaced*, etc. Validates that typed edges with bidirectional inverses are the right shape.
- **"How we met" provenance per contact.** A small but powerful pattern: every contact has a recorded origin story. Translate to Pulse: every Customer record and every Talent record should have a *how-this-relationship-started* field — the original placement, the original opportunity, the original referral.
- **Diary as ambient context.** Monica's daily diary feeds into reminder logic ("you saw Alice yesterday, want to log it?"). Translate to Pulse: ambient signal logs that feed action proposals.
- **Multiple vaults per user with collaborators.** Maps onto Pulse's role tiers (Admin / Manager / RM, PM_CONTEXT memory `role_model`) — a Manager has visibility into multiple RM "vaults" of customers.
- **Reminder system with automatic derivations** (birthdays). Maps onto Pulse's "remember to check in on this customer X days after their last conversation" cadence logic.
- **Custom field types for contact properties.** Less impactful than Relaticle's version but the same idea.

## Specific code modules to reference later
- Monica's relationship-type model and its bidirectional-inverse logic (path to confirm during Phase 2 if needed).
- Reminder scheduling / automatic-derivation pipeline.
- Vault + collaborator authorization model.
- 27-language i18n setup (irrelevant for Phase 1 — English only — but a reference if EDGE ever localizes).

## What we explicitly are NOT taking from this
- **Any code.** AGPL.
- **The "document your life" framing.** Monica is for personal relationships; Pulse is for B2B revenue. The framing must not bleed into Pulse copy.
- **PHP/Laravel/Vue/Inertia stack.** Wrong language for Pulse.
- **The beta v5 unfinished surface.** Even as a reference, prefer reading the stable `4.x` branch for ideas; we're not on this branch.
- **Pet management and similar consumer features.** Not applicable.

## Relevance to EDGE Pulse
**Low — narrow but real.** Monica is the *least* directly relevant repo in this audit because it is consumer PRM and not enterprise CRM/sales-intelligence. Its real contribution is two patterns: **typed bidirectional relationships** (validating Pulse's Account/Talent Relationship Graph shape) and **"how we met" provenance** (a per-relationship origin record that Pulse should adopt — every customer and every talent should have a recorded relationship genesis). The reminder pattern is reusable for cadence logic. Beyond these, Monica is a "read once, take notes, move on" reference. License blocks any code embedding even if we wanted it.

## Open questions raised by this repo
- **Should Pulse record explicit relationship genesis per customer and per talent?** This would carve out a small "origin" field in the data model (e.g., `customer_acquired_via`, `talent_referred_by`) that surfaces in agent context for relationship-aware actions. Filed for Phase 2.
- **Cadence and reminder logic.** Pulse needs to decide whether reminders live in Salesforce (existing tasks/events) or are Pulse-native. If Pulse-native, Monica's reminder model is the cleanest reference. Filed for Phase 2.
- **Bidirectional relationship inverses.** When Pulse stores a `placed_at(talent, customer)` edge, does it also store the inverse `has_placed(customer, talent)` explicitly or derive it on read? Graphiti has its own opinion here; needs to be reconciled. Filed for Phase 2.
