# Findings: skills-ml

## What it is
skills-ml is a Python library from the Workforce Data Initiative (University of Chicago, Data Science and Public Policy) that supports the Open Skills API. It provides machine-learning utilities for jobs-and-skills taxonomy work: occupation classifiers, skill extractors, job-title cleaners, embedding-based job/skill comparisons, geocoders, and adapters to the **ESCO** (European Skills, Competences, Qualifications and Occupations) and **O*NET** ontologies. Inputs are job postings (a sample of 50 is bundled); outputs are normalized job titles, extracted skill terms, and embedding spaces for similarity queries.

## License
**University of Chicago non-commercial research license.** **No — not usable as-is in EDGE Pulse as a closed-source commercial product.** The license explicitly limits use to "educational and not-for-profit research purposes" and **specifically excludes "any service or part of selling a service that uses the Program."** A commercial license requires negotiation with the Polsky Center at U-Chicago. **Conditional path:** EDGE Pulse may (a) use the library *internally for research* during Phase 1 to study the ontologies and methods, (b) re-implement equivalent functionality from scratch, or (c) consume the underlying public ontology data (ESCO is CC BY 4.0, O*NET is public-domain US Government work) directly without using skills-ml code. We must **not** ship skills-ml code in any production binary.

## Maturity signal
- Last commit date: 2023-05-05 (LICENSE-only update; meaningful code activity is older still).
- Stars (if external repo): Not pulled in this session.
- Open issues count (if available): Not pulled; project appears abandoned upstream.
- Published papers / notable adopters: Yes — Open Skills Project, U-Chicago Data Science and Public Policy program, integrated into the Open Skills API.
- Subjective maturity: **Stagnant.** Code targets Python 3.6, depends on older scientific Python stack, last meaningful activity predates 2023. The *ideas* and *ontology adapters* are still valuable; the *code* is not a live dependency candidate.

## Data model / schema
- **JobPosting** (JSON-LD shaped) — title, description, hiring organization, location.
- **CompetencyOntology** — base class with `Competency`, `Occupation`, and edges between them. Concrete implementations: `ESCOOntology`, `ONetOntology`, plus a `from_candidate_skills` builder for emergent ontologies.
- **Skill extractor** outputs: lists of `CandidateSkill` objects with provenance back to the source posting and the matched ontology node.
- **Embedding spaces** — pretrained or trained Word2Vec / FastText / Doc2Vec representations over job postings, used for similarity and clustering.

## Architectural patterns worth stealing
- **Ontology-as-abstraction.** A common `CompetencyOntology` base lets the same downstream code (skill extraction, similarity, classification) target ESCO or O*NET interchangeably. Pulse's "Skills Layer" can adopt this pattern: a thin internal ontology interface backed by ESCO data, swappable later.
- **Skill-extraction pipeline shape.** Tokenization → candidate-skill generation → ontology match → confidence scoring. Useful blueprint when we later need to extract talent skills from Salesforce free-text fields, Chorus transcripts, or case descriptions.
- **Occupation-classifier pattern.** Maps a free-text title (e.g. "Sr. Medical Coder III") onto a canonical occupation code. EDGE places healthcare/insurance talent — a canonical role taxonomy is exactly what an RM needs to compare placements across customers.
- **Sample-based evaluation harness.** The `Skills-ML Tour.ipynb` walks through the pipeline on a small bundled sample. Good model for our own Design-phase evaluation harness.

## Specific code modules to reference later
- `skills_ml/ontologies/base.py` — abstract competency-ontology interface; the shape we want to mirror for Pulse's internal Skills Layer.
- `skills_ml/ontologies/esco.py` — concrete ESCO adapter (loader, edges, occupations). Read for ontology *shape*, then implement our own loader against ESCO's CC BY 4.0 data.
- `skills_ml/ontologies/onet.py` — O*NET adapter; same logic.
- `skills_ml/algorithms/skill_extractors/` — extraction strategies (exact-match, fuzzy, semantic). Useful reference for our own extractor design.
- `skills_ml/algorithms/jobtitle_cleaner/` — title normalization heuristics; lightweight win for the Talent Layer in Pulse.
- `Skills-ML Tour.ipynb` — best single artifact to read for the gestalt of the project.

## What we explicitly are NOT taking from this
- **Any production code.** License blocks it. Re-implement what we need.
- **Python 3.6 / aging dependency tree.** Our stack targets current Python; we will not pin to skills-ml's requirements.
- **Word2Vec/Doc2Vec embedding spaces.** Modern dense embeddings from OpenAI/Anthropic/sentence-transformers will outperform what skills-ml produces. Adopt the *idea* of an embedding-based skill similarity; do not adopt skills-ml's specific models.
- **The Open Skills API surface itself.** Pulse is not a public skills API.

## Relevance to EDGE Pulse
**Medium-low for code, medium-high for design ideas.** The license disqualifies skills-ml as a runtime dependency, which is the dominant constraint. As a *research* input it is still useful: it teaches the shape of a competency-ontology adapter, validates ESCO/O*NET as the canonical taxonomies to target, and offers a working precedent for the skill-extraction pipeline that Pulse's Skills Layer (PM_CONTEXT §11 glossary) will need in Phase 2 for talent drift detection. For Phase 1 (Graph Architecture Option C — lite skills layer) we likely don't need to extract skills at all; we just need a place to *attach* skills to talent and customer-role records. For Phase 2 (full skills drift) we will need a real extractor — and at that point we'll write our own against fresh embeddings + ESCO data directly.

## Open questions raised by this repo
- **ESCO data licensing in production.** ESCO is CC BY 4.0 — clean for commercial use with attribution. Need to confirm the attribution surface (internal-only is easy; user-facing requires care given the white-label rule).
- **O*NET vs. ESCO for US healthcare/insurance roles.** O*NET is US-centric and very deep on healthcare occupational categories; ESCO is EU-origin but global in scope. Pulse's customer base is US — does O*NET actually map better here? Filed for Phase 2 design.
- **Where the skills extractor runs.** Phase 1 may skip extraction entirely. Phase 2 needs a placement: as an offline batch job, as part of the episode-ingestion pipeline, or as a separate service. Filed for Phase 2 design.
