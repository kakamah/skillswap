# ALIP — Architecture Review and Rewrite
**Reviewer Role:** Senior Backend Engineer / ML Systems Architect / Agri-Tech Technical Reviewer / College Application Positioning Expert
**Subject:** AI-Driven Livestock Intelligence Platform (ALIP) — Developer-Facing Architecture Brief

---

# 1. Brutal Technical Critique

## 1.1 High-Level Verdict

This document is structurally ambitious but architecturally hollow. It reads like someone read three ML papers and one agricultural startup pitch deck, then assembled bullet lists that gesture at real engineering without committing to any of it. The visual formatting is confident. The engineering underneath it is not.

The most damning problem: the document defines what the system does in nearly every section, but almost never defines **how** the system does it. "Computer vision health models" appears repeatedly — but there is no input specification, no label schema, no training data source, no inference contract, no failure policy. "Tamper-evident logging" is mentioned in five different places — but the hash chain is only partially defined and the actual verification workflow is never specified. "Telegram bot for interaction" is claimed as a UX layer — but the actual message flow, state machine, and error recovery are absent.

What the document achieves: a reasonable list of capabilities a livestock intelligence platform should have. What it fails at: explaining how any individual engineer would actually implement those capabilities without inventing 60% of the architecture on their own.

For a college portfolio, this is a serious problem. Admissions technical reviewers who have any engineering background will see the gap between vocabulary and depth immediately. The document currently reads like a well-formatted concept, not a system design.

The core failure is this: **the document describes outputs, not systems**. It tells you what you will see — "BCS score," "health risk band," "pasture alert" — but does not tell you what process produces those results, what data it depends on, what it does when that data is missing, or how you validate it.

---

## 1.2 Major Weaknesses

### W1 — The Computer Vision Module Has No Data Plan (Critical)

The CV module is the flagship technical claim of the entire project. Yet the document never answers the most important question: **where does the labeled training data come from?**

BCS estimation is a regression task that requires images annotated with body condition scores assigned by trained livestock assessors. These are not available in a generic ImageNet-style dataset. The paper-citation standard in this domain involves datasets from the University of Edinburgh, CSIRO (Australia), and a handful of European veterinary research institutions. You cannot train a BCS model without expert-labeled images, period.

The document says "YOLO for detection, EfficientNet for classification." That is not a data plan. That is two model names. A real CV module specification would say: what is the training dataset, how many images, what annotation schema, what class distribution, what is the fallback when training data is insufficient for a species, and what does the model output when image quality is below threshold.

Without this, the CV module is vaporware. The document implies it can be built. It cannot be built from this specification.

### W2 — The Forecasting Module Assumes Data That Does Not Exist at V1 (Critical)

The forecasting module lists "historical weights, time gaps, feed quantity, feed type, weather summary, pasture NDVI trend, animal age, breed" as inputs. For a new farm deployment, essentially none of this historical data exists. A farmer who just installed the system has zero historical weight records, zero feed history in the system, and zero linked NDVI trends.

The document never addresses the **cold-start problem**. How does the forecasting model produce anything useful during the first 30, 60, or 90 days of operation? The honest answer is: it doesn't, at least not with high-quality ML inference. You would need either population-level priors (breed-average growth curves), manual expert baselines, or a degraded fallback mode that uses simple linear extrapolation until the data window is sufficient.

None of this is mentioned. The forecasting module reads as if the data pipeline is already populated. That is architecturally dishonest.

### W3 — Traceability Is Named But Not Designed (Serious)

The hash-chain structure appears in multiple sections. The formula `event_hash = SHA256(prev_hash + event_data + timestamp)` is given. But the following critical questions are never answered:

- Where is the chain stored? Same DB table? Separate? External?
- Who verifies the chain and when? On-demand? Scheduled audit?
- What happens if an event is rejected after insertion — is the chain invalidated?
- What is the exact serialization order for the hash input? JSON with sorted keys? Byte stream?
- What happens to the chain if the backend migrates databases?
- Is there any external anchor (timestamping service, even just a public log) that makes the tamper-evidence meaningful, or is it purely in-database self-attestation?

Without these answers, the "tamper-evident" claim is marketing language applied to a SHA256 call. Anyone can regenerate a chain by recomputing all hashes after edits. The document never explains why that is prevented.

The current implementation implies that only in-database hash consistency is checked. That is a weak integrity guarantee, not a tamper-evident audit system.

### W4 — The Pasture Monitoring Module Has No Satellite Data Pipeline (Serious)

"Fetch Sentinel-2 imagery, clip to polygon, compute NDVI" is listed as a workflow. But the Sentinel-2 ingestion problem is non-trivial:

- Sentinel-2 imagery has a 5-day revisit cycle at best, and cloud cover can eliminate usable images for weeks in agricultural regions.
- The Copernicus Open Access Hub API was migrated to the Copernicus Data Space Ecosystem in 2023. API calls, authentication, and product download processes have changed. Is the document using the old Hub API?
- Processing raw L1C Sentinel-2 imagery to L2A (surface reflectance, required for meaningful NDVI) requires either the sen2cor processor or access to pre-processed L2A products. This is a non-trivial preprocessing step that is completely absent from the document.
- Band math for NDVI uses Band 8 (NIR, 10m) and Band 4 (Red, 10m). Clipping to a farm polygon requires coordinate system alignment, reprojection, and masking. None of this is specified.
- NDVI values alone without seasonal normalization are nearly meaningless. NDVI 0.43 in July for a semi-arid steppe is not the same condition as NDVI 0.43 in March. Without phenological baselines, the output is noise.

The document uses the word "fetch" as if Sentinel-2 is a weather API you call with a date and get a number back. It is not.

### W5 — The Multi-Modal Fusion Section Is a Placeholder (Serious)

Section 10 proposes a "per-animal feature snapshot" that combines BCS, weight trend, feed pattern, weather, pasture condition, and history. The output example shows a `risk_score: 0.78`. But the document never explains:

- What model produces this risk score?
- Is it a learned model, a rule-based scoring function, or a weighted linear combination?
- How are the heterogeneous input types (image embeddings, time series, categorical events) combined?
- What is the training signal? What labeled "risk" outcomes exist?
- If the CV module has not run recently (no fresh image), what happens to the fusion output?

"Multimodal fusion" is one of the most technically involved problems in applied ML. Treating it as a list of features that feed into some implied black box, producing a confidence score, is not architecture — it is a wireframe drawing of an architecture.

### W6 — The MVP Is Still Too Wide (Serious)

The document lists what is "not in first prototype" but still includes BCS estimation, growth forecasting, NDVI pipeline, and multimodal risk ranking in the MVP column. That is not an MVP. A credible V1 for a solo developer or small team is:

- Animal registration
- Event logging with hash chain
- Image upload (stored, not yet inferred)
- Telegram bot for the above three operations
- Basic manual dashboard

That is a buildable V1 in realistic scope. Everything else is V2+. Claiming all of ALIP in MVP scope is how projects never ship.

### W7 — No Offline / Sync Architecture (Serious)

The document repeatedly states the system must work under "limited connectivity" and "low-connectivity field conditions." This appears in the problem statement, design principles, and user workflow. But there is no architecture for how this is actually achieved.

Questions that are never answered:

- Does the Telegram bot work offline? (No — Telegram requires internet.)
- Is there a local mobile component that caches events and syncs later?
- What is the conflict resolution policy when the same animal record is modified on two disconnected devices?
- Is the image upload queue persistent across connection drops?
- What happens to the hash chain if events are inserted out of order due to delayed sync?

The "offline-tolerant" design principle is stated in section 4 and then architecturally ignored in every subsequent section. The backend is a standard online REST API. The Telegram bot is online-only. There is no local storage, no sync protocol, no conflict resolution, and no offline queue anywhere in the document.

This is the most dishonest gap in the document. The problem statement explicitly names connectivity as the primary operational constraint. The architecture never solves it.

### W8 — Authentication and Authorization Are One Line (Moderate)

"JWT + role-based permissions" in the stack list is not an auth design. Who are the roles? What can each role do? Can a field worker see another farm's data? Can the farm manager override an AI flag? Can an auditor export records? What is the token expiration policy? What happens on token revocation? What is the multi-farm isolation model?

These are not edge cases. In an agricultural platform used by multiple farms, tenant isolation and role logic are core backend requirements, not footnotes.

### W9 — No Evaluation Strategy for the Core Claims (Moderate)

Section 16 lists evaluation metrics, which is positive. But the evaluation plan has no numbers, no baselines, no datasets, and no methodology.

"Classification accuracy" for the CV module — against what labeled dataset? "Human-review agreement" — using what process, what annotators, what sample size? "MAE / RMSE / MAPE" for forecasting — compared against what baseline, on what held-out period?

Metrics listed without methodology are just vocabulary. A real evaluation plan says: what data, what split, what baseline comparison, what acceptance threshold, and what decision is made if the model fails that threshold.

### W10 — The ESG / Emissions Section Is Embarrassing (Moderate)

Section 15.2 lists "water proxy, emissions proxy, sustainability score" as experimental metrics. These are flagged as "only if methodology is documented." But the document never hints at what that methodology would be.

Livestock emissions estimation is a field with active IPCC working groups, mandatory national inventory reporting, and domain-specific models (like the GLEAM model from FAO). A system that produces an "emissions proxy" without specifying the methodology, inputs, emission factors, and validation is not doing emissions modeling — it is producing a number that looks like science and is not.

Listing this without qualification damages the credibility of the rest of the document. Cut it from V1 entirely.

### W11 — The Folder Structure Is Cosmetic (Minor)

The folder layout in section 12.3 is a reasonable convention, but it is not architecture. It does not explain service boundaries, inter-service communication, data access patterns, or how the ML pipeline interfaces with the API. The folder structure should be derived from the architecture, not presented as a substitute for it.

### W12 — The Final Positioning Statement Is Marketing Copy (Minor)

Section 20 reads like a pitch deck conclusion: "modular AI-assisted livestock management platform that integrates computer vision, forecasting, satellite-based pasture monitoring, and tamper-evident event logging." This is a capabilities list dressed as a positioning statement. It says what the system has, not what problem it solves at what scale with what constraints. Reframe as an engineering scope statement.

---

## 1.3 Severity Table

| # | Problem | Severity |
|---|---------|----------|
| W1 | CV module has no training data plan | Critical |
| W2 | Forecasting cold-start problem not addressed | Critical |
| W3 | Traceability chain not fully specified | Serious |
| W4 | Satellite pipeline vastly undersimplified | Serious |
| W5 | Multimodal fusion is a placeholder | Serious |
| W6 | MVP scope is too wide to be credible | Serious |
| W7 | Offline architecture is claimed but never designed | Serious |
| W8 | Auth/roles not designed | Moderate |
| W9 | Evaluation plan has no methodology or numbers | Moderate |
| W10 | ESG/emissions claims are unsupported | Moderate |
| W11 | Folder structure substituted for service architecture | Minor |
| W12 | Positioning statement is marketing copy | Minor |

---

## 1.4 What Makes It Sound Weaker Than It Could

The document is weakest where it is most specific-sounding but least grounded. "YOLO + EfficientNet" sounds like technical depth but without a data plan those model names are decoration. "Sentinel-2 NDVI" sounds like satellite expertise but without preprocessing pipeline details it is a citation, not architecture. "Tamper-evident hash-linked records" sounds like security expertise but without a verification workflow it is a SHA256 call.

The pattern throughout is: **name a real technology or methodology, describe its output, skip the implementation**. This pattern is recognizable to any engineer who has reviewed junior-level architecture documents. It is the hallmark of a person who has read about systems without having built them.

The fix is not more sophistication. It is more honesty about constraints, more specificity about interfaces, and more explicit acknowledgment of what is deferred.

---

# 2. What a Programmer Still Needs

## 2.1 Missing Architecture Details

**Service boundaries and communication contracts**
The document lists "API service, inference service, scheduler/ETL, audit service" but never defines how they communicate. Are they separate processes? Separate containers? Do they share a database? Does the inference service call back to the API, or does the API poll? What is the message contract if a background task fails?

**Async pipeline contract**
When an image is uploaded, what exactly happens? The document says "queue the image for model processing" but does not specify:
- What queue system (Celery, RQ, ARQ, raw Redis pub/sub)?
- What is the task schema (what fields are in the message)?
- What is the retry policy on inference failure?
- How does the bot know inference is complete — polling or push notification?
- What is the SLA on inference completion?

**Storage layout**
Images are stored in "S3-compatible bucket or local blob storage." But:
- What is the path convention? `/farm_id/animal_id/image_id.jpg`?
- Are original and processed images stored separately?
- What is the retention policy?
- Is there a CDN layer for serving images to the dashboard?
- What metadata is stored in DB vs. in the object store?

**Database schema completeness**
The entity definitions in section 7 are a start. Missing:
- `Farm` entity (who owns `farm_id`?)
- `User` entity with role, farm membership, auth fields
- `Tag` entity (QR/RFID tags with assignment history — tags get reused or retired)
- `AlertRule` entity (configurable thresholds per farm)
- `Alert` entity (generated alert instances, delivery status)
- Foreign key and indexing strategy (which columns are indexed, and why?)
- Soft delete strategy vs. hard delete for animals, events

**Multi-tenancy model**
Complete absence. Can one user belong to multiple farms? Can one farm have multiple managers? Is there a platform admin role? How is data partitioned — by `farm_id` filter or by database schema?

**Event sourcing vs. CRUD**
The document uses append-only `AnimalEvent` for the audit trail but also defines mutable entities like `Animal` (with a `status` field). Are animal attributes also event-sourced (each attribute change generates an event) or only lifecycle events? This distinction fundamentally changes the schema and query patterns.

## 2.2 Missing Data/ML Details

**Training data source and labeling protocol**
For the CV module: what dataset? Options include CEVA (cattle body condition datasets from UK/Ireland), Australian CSIRO cattle datasets, or self-collected data. For self-collected data: who labels, what label schema, what inter-rater reliability protocol? Without labeled data, no model ships.

**BCS label schema**
BCS scoring is species-specific and scale-specific. Cattle: 1–9 scale (USDA) or 1–5 scale (UK/European). Sheep: 0–5 scale. What scale is used? How are continuous estimates handled vs. integer scores? The document never specifies.

**Model input normalization**
What image resolution is the CV model trained on? What preprocessing transforms (resize, normalize, augment)? What view is required — side view only, or can rear/rear-quarter work? What if the animal is in motion?

**Confidence calibration**
The outputs include confidence scores, but what do they mean? Raw softmax probability? Calibrated probability (Platt scaling, temperature scaling)? An uncalibrated softmax confidence of 0.74 is meaningless without calibration. This is a critical omission for a system meant to guide health decisions.

**Cold-start fallback for forecasting**
What does the forecasting module return when an animal has fewer than N weight records? What is the minimum data requirement? Does it return a breed-average lookup, a linear extrapolation, or an explicit "insufficient data" response with a data collection prompt?

**Model versioning and rollback**
When a new model is deployed, old predictions stay in the database with the old `model_version` tag. How are predictions compared across versions? Is there a shadow deployment mode (run old and new simultaneously, compare outputs)? What triggers a rollback?

**Label drift and data drift detection**
If the system is used on farms in different geographic regions or climates, the image distribution will drift from the training set. How is this detected? What are the triggers for retraining?

**Sentinel-2 preprocessing pipeline**
Completely unspecified. Needs: data source (Copernicus Data Space Ecosystem), product type (L2A preferred, or L1C + sen2cor), cloud masking approach (SCL band or external mask), band selection (B04, B08 for NDVI), resampling to common grid, clip-to-polygon (rasterio/GDAL), cloud cover threshold for rejection, NDVI computation, seasonal normalization baseline, storage as raster or scalar timeseries.

**Pasture phenological baseline**
How is "normal" NDVI defined for a given zone at a given time of year? Without a multi-year historical baseline, "declining" is meaningless. Is this baseline computed from historical Sentinel-2 imagery for the same zone in the same calendar period? How many years? What if no historical data exists for a new zone?

## 2.3 Missing Backend/Product Details

**API authentication flow**
What is the registration/login flow? SMS OTP, email/password, OAuth? For Telegram, how does the bot authenticate a farm worker — by Telegram user ID, by a registration code, by a linked account? Telegram user IDs are not secure identifiers on their own.

**API versioning strategy**
Is the API versioned at the URL level (`/v1/animals`)? What is the deprecation policy? This matters for long-running farm deployments where the app must remain functional even as the backend evolves.

**Image upload protocol**
Does the client upload directly to object storage (presigned URL pattern) or to the API server? The difference has major implications for bandwidth, backend load, and failure recovery.

**Telegram bot state machine**
The bot commands are listed but the conversation state machine is not. If a user sends `/upload_image` and then sends a photo, does the bot know which animal the photo belongs to? How? Is there a session state? What is the timeout on a pending upload session? What happens if the user abandons mid-flow?

**Alert delivery mechanism**
The system generates risk flags and pasture alerts. How are these delivered? Do they appear in the Telegram bot proactively? As push notifications? Only on-demand query? What is the alert deduplication strategy — does the same risk flag trigger a new alert every day, or only when state transitions?

**Report generation**
What is the format — JSON API response, PDF export, CSV? What triggers a report — on-demand, scheduled, event-driven? Who can request a report — only farm managers, or also auditors?

**Soft deletion and data retention**
If an animal is marked `deceased`, what happens to its events, predictions, and images? Are they retained, archived, or deleted? What is the legal or regulatory assumption around data retention?

## 2.4 Missing Operational/Agricultural Details

**Connectivity assumption clarification**
The document claims offline tolerance but the entire architecture is online. This must be resolved: either (a) accept that V1 requires internet connectivity and remove all "offline-tolerant" claims, or (b) design an actual offline-first mobile component (e.g., a React Native or Flutter app with local SQLite, sync-on-connect, and conflict resolution). Claiming offline tolerance without either strategy is dishonest.

**Species coverage and model generalization**
The `Animal` entity supports cattle, sheep, goat, horse. These species have completely different BCS scales, visual morphology, and health indicators. A single CV model trained on cattle will not generalize to sheep. Does the system use separate models per species, a species-conditioned model, or does V1 restrict to one species?

**Stocking density calculation**
`stocking_density` appears in `PastureZone` as a field. How is it computed? Animals per hectare? Animal units (AU, where one AU = one 450kg cow)? Is it computed from the current animal location assignments, or manually entered? The field is defined but never computed.

**RFID vs. QR operational difference**
The document treats RFID and QR tags identically as `tag_code`. In practice they are very different: RFID can be read at distance, QR requires line-of-sight camera scan. Does the Telegram bot support QR scanning directly (camera-based)? Does the system support RFID readers connected to a separate device? The intake workflow is different in each case.

**Veterinary role boundary**
The document lists "veterinary assistant/inspector" as a primary user. What permissions does this role have that a field worker does not? Can a vet override an AI health flag? Can a vet add a medication event? What medical record fields are vet-only? This is not defined anywhere.

**Data entry realism for small farms**
The document assumes farmers will record `feed_type`, `quantity_kg`, and `cost_local_currency` per feeding event, per animal. In reality, small-to-medium farms often feed groups of animals together, not individually. Does the system support group-level feed records that are then proportionally distributed? If not, the feed tracking model is unrealistic for the stated target user.

---

# 3. Recommended Architecture Direction

## 3.1 What To Keep

**The core entity model** — Animal, AnimalEvent, ImageRecord, WeightRecord, FeedRecord, PastureZone, NDVIRecord, ModelPrediction — is the strongest part of the document. Flesh it out with the missing entities and it becomes a real schema.

**The hash-linked append-only event chain** — genuinely interesting, technically credible, and differentiated. Keep it. Specify it more rigorously. This is what makes the traceability layer meaningful.

**The Telegram bot as primary UX** — this is a smart, honest decision. It is low-bandwidth, requires no app install, and is genuinely used in agricultural contexts in Central Asia, Eastern Europe, and parts of Southeast Asia. Defend this choice explicitly and it strengthens the document.

**The modular layer structure** — data collection, AI/analytics, external data, backend API, traceability, UI — is reasonable and should be preserved as the organizing principle.

**The AI-assistive framing** — "support decisions, not replace veterinary judgment" — this is the correct positioning. Keep it, make it more specific.

**Phase-gated roadmap** — the Phase 1 through Phase 4 structure is good project management thinking. Tighten the scope of each phase.

## 3.2 What To Cut or Defer

**ESG / emissions proxy / sustainability score** — cut entirely from V1 and V2. Mention as aspirational in the roadmap only if a rigorous methodology citation can be included. Do not ship a sustainability score with no methodology.

**Multimodal fusion as a V1 feature** — defer. True multimodal fusion (image + time series + spatial) is a PhD-level research integration problem. In V1, a simple rule-based risk aggregation (if BCS < threshold AND weight trend declining AND NDVI declining, flag as high risk) is both more honest and more buildable.

**LSTM / temporal transformer** — defer until you have more than 6 months of data from real animals. Phase 1 forecasting should be XGBoost or LightGBM on structured features, with explicit acknowledgment that this is a structured baseline.

**Real-time sensor fusion** — already in the "not in first prototype" list. Keep it there.

**Multi-farm reporting and ESG analytics** — defer to Phase 4. The V1 focus should be one farm working correctly.

**"Fully decentralized blockchain infrastructure"** — correctly excluded. But also cut the language in the traceability section that gestures toward blockchain credibility without the implementation. The hash chain is not a blockchain. Say that clearly and own the honest version.

## 3.3 What To Reframe

**"Offline-tolerant field workflow"** → Reframe as: "V1 requires internet connectivity. Offline capability is a V3 objective, contingent on a mobile-native client with local persistence and sync protocol. Current architecture is internet-dependent by design."

**"Tamper-evident record logging"** → Reframe as: "Server-side append-only hash chain providing chain-of-custody auditability. Tamper evidence is internal — any external actor with database write access could reconstruct the chain. External anchoring (e.g., periodic digest publication) is a future integrity enhancement."

**"AI-assisted health and body condition analysis"** → Reframe as: "Computer vision pipeline producing a BCS estimate and a health risk band from a side-view image, subject to image quality gates. Outputs are decision-support signals, not clinical diagnoses. Initial model is trained on [source dataset], fine-tuned on collected farm images. Accuracy benchmarked against expert annotator agreement."

**"Multimodal AI fusion"** → Reframe as: "Risk aggregation layer that combines CV output, weight trend, and pasture status using a weighted scoring function in V1. Transition to a learned fusion model in V3 when labeled risk outcomes are available."

**"Progressive intelligence"** → Reframe as: "The platform is designed with incremental model improvement as a first-class concern. All predictions are logged with model version and input snapshot. Annotation tools allow vets to label AI outputs. Retrain pipeline is triggered manually or on data volume threshold."

## 3.4 Stronger V1 Definition

A credible V1 for a solo developer or two-person team over 6–8 months is:

**V1 must-haves:**
- Farm and user registration with JWT auth and two roles: `manager` and `field_worker`
- Animal CRUD with QR code generation (not RFID — QR is implementable without hardware)
- AnimalEvent append-only schema with SHA256 hash chain
- ImageRecord upload (store to S3 or local, no inference yet in V1.0)
- WeightRecord and basic FeedRecord entry (group-level feed supported)
- Chain verification endpoint that validates hash integrity
- Telegram bot covering: register animal, upload image, record weight, query animal status
- Simple dashboard (web): animal list, event history, recent images

**V1 stretch goals (V1.1):**
- Basic CV inference pipeline on uploaded images (BCS estimation, single species)
- Image quality gate before inference
- ModelPrediction record storage with confidence and model version
- Alert rule: if BCS drops below configurable threshold, generate alert
- Alert delivery via Telegram bot message

**Explicitly not in V1:**
- Sentinel-2 pasture monitoring
- Forecasting
- Multimodal risk scoring
- ESG reporting
- Offline sync
- RFID integration

This scoping makes the project sound engineered rather than dreamed.

## 3.5 Admissions/Portfolio Positioning Advice

**What makes this project strong for admissions:**

1. **Domain specificity** — livestock intelligence in agricultural contexts is neither generic (not another social network) nor purely academic. It exists at the intersection of systems engineering, applied ML, remote sensing, and domain-aware product design. That intersection is rare among student portfolios.

2. **Constraint-aware design** — the fact that the system explicitly deals with connectivity constraints, low-quality image inputs, sparse labeled data, and non-technical users shows operating environment awareness. This is more impressive than a project that assumes ideal conditions.

3. **The hash-chain traceability layer** — this is a genuinely interesting design choice that can be explained in one sentence and has a clear technical justification. It demonstrates security/data integrity thinking without requiring blockchain implementation.

4. **The three-layer AI architecture** — CV (spatial), forecasting (temporal), pasture monitoring (geospatial) — shows breadth across ML subfields. The key is to be honest about what each layer actually delivers.

5. **Evidence of scope discipline** — showing a phased roadmap where V1 is genuinely buildable, V2 adds ML, and V3 adds geospatial, demonstrates engineering maturity. Trying to build everything in V1 would suggest the opposite.

**What NOT to claim:**
- Do not claim the model is "production-ready" unless you have a deployment with real farmers providing feedback.
- Do not claim the emissions/ESG module works unless you have a documented methodology.
- Do not claim the system works offline unless you have implemented the offline sync.
- Do not say "blockchain" unless you mean it. The hash chain is not a blockchain.

**What to demonstrate with evidence:**
- Actual inference outputs with confidence scores and example images
- The hash chain with a real verification example (modify event, show chain break)
- Actual Telegram bot flow screenshots
- Actual NDVI map output for a real polygon
- Model evaluation metrics with methodology described

---

# 4. Rewritten Architecture Brief

```
ALIP — AI-Driven Livestock Intelligence Platform
Engineering Architecture Brief v2.0

Author: Aidyn Askarbekuly
Document Type: Implementation-Grade Architecture Brief
Scope: Full-stack applied AI system for livestock farm operations
Status: V1 in active development
```

---

## 4.1 Project Definition

ALIP is a modular server-side platform that gives livestock farms structured animal tracking, AI-assisted health and body condition assessment, feed and growth analytics, satellite-based pasture monitoring, and a verifiable event audit trail — accessible through a Telegram bot as the primary field interface.

The system is designed around four operating realities of agricultural environments:

1. **Field workers are not developers.** The primary interface must require no app installation and minimal typing.
2. **Farm data is sparse and inconsistent.** AI outputs must be honest about data sufficiency and avoid fabricating precision from incomplete inputs.
3. **Internet connectivity is intermittent.** V1 requires connectivity but the architecture is designed to support an offline-first mobile client in a future phase.
4. **AI outputs are decision support, not decisions.** The platform assists trained farm managers and veterinary personnel; it does not replace them.

---

## 4.2 Problem Statement

Livestock farms at the small-to-medium scale (50–2,000 animals) operate with:

- Paper-based or spreadsheet animal records with no event history integrity
- Health assessments that happen reactively — after visible decline — rather than proactively
- Feed cost tracking that is imprecise or absent
- No systematic monitoring of pasture condition relative to stocking load
- No audit-ready record system for animal provenance, health history, or movement

The consequences are: delayed health interventions, poor feed efficiency, undetected pasture degradation, and no defensible record chain for sale, export, or veterinary reporting.

ALIP provides a digital backbone for these operations: a structured record system with AI-assisted monitoring that is accessible from a basic smartphone with a Telegram account.

---

## 4.3 Target Users

| Role | Function | Primary Interface |
|------|----------|-------------------|
| Farm manager | Registers animals, reviews AI summaries, sets alert thresholds, exports reports | Web dashboard + Telegram |
| Field worker | Enters weights, uploads images, records feeding events, scans tags | Telegram bot |
| Veterinary inspector | Reviews health flags, adds treatment records, annotates AI outputs | Web dashboard |
| Auditor | Verifies event chain integrity, exports provenance records | API / dashboard |

**User assumption:** farm managers and vets have limited but real smartphone and computer access. Field workers have a smartphone with Telegram. No user has reliable desktop internet in the field.

---

## 4.4 Design Principles

**P1 — Data before inference.** The system must store and manage structured farm records independently of AI. The analytics layer is additive, not foundational.

**P2 — Explicit data sufficiency.** Every AI output must communicate what data it was based on and flag when that data is insufficient. "Insufficient data to forecast" is a valid and valuable output.

**P3 — Assistive, not authoritative.** AI outputs are labeled as estimates and decision-support signals. The system does not override user input and does not block workflow based on AI flags alone.

**P4 — Append-only event history.** Farm events are never edited or deleted. Corrections are new events referencing prior events. This preserves a complete, auditable history.

**P5 — Modular AI pipeline.** Each AI module (CV, forecasting, pasture) is independently deployable and independently evaluated. Failure of one module does not break the others.

**P6 — Conservative scope over ambitious claims.** The system claims only what it can demonstrate. Experimental features are clearly labeled as such.

---

## 4.5 Scope Boundaries

### In scope for V1 (core platform):
- Animal registration, QR tag assignment, and CRUD
- Append-only event log with SHA256 hash chain integrity
- Image upload (stored, quality-checked, queued for inference)
- Weight and feed event recording (supporting group-level feed allocation)
- Telegram bot interface for all field-facing operations
- Basic web dashboard: animal list, event history, status flags
- JWT authentication with `manager` and `field_worker` roles
- Farm-level multi-tenancy (one deployment serves multiple farms)

### In scope for V1.1 (AI prototype):
- CV inference pipeline: BCS estimation and health risk classification for cattle (single species)
- Image quality gate before inference (blur, occlusion, angle, multi-animal detection)
- ModelPrediction storage with confidence, model version, and input snapshot
- Alert rules: configurable BCS threshold triggers, Telegram delivery

### In scope for V2 (forecasting + pasture):
- Sentinel-2 NDVI ingestion pipeline (L2A products, cloud masking, polygon clipping)
- Pasture zone scoring with phenological baseline
- Growth forecasting on animals with >= 3 weight records (XGBoost on structured features)
- Feed cost per kg gain estimate with explicit data-availability gate

### In scope for V3 (integration + scale):
- Risk aggregation layer combining CV, growth, and pasture signals
- Annotation interface for veterinary labeling of AI outputs
- Retraining pipeline triggered by data volume threshold
- Multi-species CV model (sheep support)
- Offline-first mobile client with local persistence and sync

### Explicitly out of scope:
- Real-time sensor fusion or IoT hardware
- ESG reporting or emissions estimation
- Full blockchain infrastructure
- Fully automated grazing optimization
- Disease diagnosis (as opposed to health risk flagging)
- Regulatory compliance engine

---

## 4.6 MVP Definition

MVP is defined as V1 + V1.1 above, demonstrable end-to-end:

1. Register a farm and one animal with QR code
2. Record three weight events and two feeding events via Telegram
3. Upload a side-view image via Telegram, receive BCS estimate and health risk band
4. Verify that the hash chain for that animal's events is intact
5. View animal summary on dashboard with event timeline

This is demonstrable in a single live session and constitutes a complete V1 proof of concept.

---

## 4.7 System Architecture Overview

```
+-------------------------------------------------------------+
|                        USER LAYER                           |
|  Telegram Bot (field workers)    Web Dashboard (managers)   |
+------------------+---------------------------+--------------+
                   | HTTPS                     | HTTPS
+------------------v---------------------------v--------------+
|                     BACKEND API (FastAPI)                   |
|  Auth  |  Animals  |  Events  |  Images  |  Reports/Audit  |
+--+--------+----------+----+-------+--------+---------------+
   |        |               |       |
   |   +----v---+   +-------v-+  +--v------------------------------+
   |   |  DB    |   | Object  |  |    Task Queue (Celery + Redis)  |
   |   |(Postgres)  | Storage |  |  inference / etl / alerts       |
   |   +--------+   +---------+  +------------------+--------------+
   |                                                |
   |                             +------------------v--------------+
   |                             |     ML Inference Layer          |
   |                             |  CV  |  Forecast  |  Pasture    |
   |                             +---------------------------------+
   |
+--v------------------------------------------+
|        External Data Sources                |
|  Copernicus Data Space (Sentinel-2 L2A)     |
|  Open-Meteo or similar weather API          |
+---------------------------------------------+
```

---

## 4.8 Data Model

### 4.8.1 Farm
```json
{
  "farm_id": "UUID",
  "name": "string",
  "country": "string",
  "region": "string",
  "created_at": "ISO8601",
  "owner_user_id": "UUID"
}
```

### 4.8.2 User
```json
{
  "user_id": "UUID",
  "farm_id": "UUID",
  "telegram_chat_id": "integer | null",
  "name": "string",
  "role": "manager | field_worker | vet | auditor",
  "password_hash": "string",
  "created_at": "ISO8601",
  "is_active": "boolean"
}
```

Note: `telegram_chat_id` is used to authenticate Telegram interactions. Users register via the web dashboard first, then link their Telegram account via a one-time registration code. Telegram chat ID alone is not a trusted identifier.

### 4.8.3 Animal
```json
{
  "animal_id": "UUID",
  "farm_id": "UUID",
  "tag_code": "string",
  "tag_type": "qr | rfid | ear_tag",
  "species": "cattle | sheep | goat | horse",
  "breed": "string",
  "sex": "male | female",
  "birth_date": "YYYY-MM-DD | null",
  "status": "active | sold | deceased | unknown",
  "current_location_zone_id": "UUID | null",
  "created_at": "ISO8601",
  "created_by_user_id": "UUID"
}
```

### 4.8.4 Tag
```json
{
  "tag_id": "UUID",
  "tag_code": "string",
  "tag_type": "qr | rfid | ear_tag",
  "assigned_to_animal_id": "UUID | null",
  "assigned_at": "ISO8601 | null",
  "retired_at": "ISO8601 | null",
  "farm_id": "UUID"
}
```

Tags have their own entity because tags are reused across animals (after retirement) and lost tags require audit records.

### 4.8.5 AnimalEvent
```json
{
  "event_id": "UUID",
  "animal_id": "UUID",
  "farm_id": "UUID",
  "event_type": "birth | vaccination | feeding | weight | health_inspection | movement | image_upload | tag_assignment | status_change | correction",
  "timestamp": "ISO8601",
  "actor_user_id": "UUID",
  "payload": {},
  "notes": "string | null",
  "prev_event_id": "UUID | null",
  "prev_hash": "string | null",
  "event_hash": "string",
  "sequence_number": "integer"
}
```

**Hash computation rule:**
```
hash_input = JSON.stringify({
  event_id,
  animal_id,
  event_type,
  timestamp,
  actor_user_id,
  payload,
  prev_hash
}, sorted_keys=true)

event_hash = SHA256(hash_input)
```

Canonical serialization (sorted keys, no whitespace) is required to ensure deterministic hash reproduction across systems.

The `correction` event type allows a user to reference a prior event and add a correction note without modifying the original event, preserving the append-only constraint.

### 4.8.6 ImageRecord
```json
{
  "image_id": "UUID",
  "animal_id": "UUID",
  "farm_id": "UUID",
  "captured_at": "ISO8601",
  "uploaded_at": "ISO8601",
  "uploaded_by_user_id": "UUID",
  "source": "telegram | web | mobile",
  "view_type": "side | rear | locomotion | posture | unclassified",
  "storage_path": "string",
  "file_size_bytes": "integer",
  "quality_score": "float | null",
  "quality_rejection_reason": "blurry | dark | occluded | wrong_angle | multi_animal | null",
  "inference_status": "pending | queued | running | done | failed | rejected",
  "inference_task_id": "string | null"
}
```

### 4.8.7 WeightRecord
```json
{
  "weight_id": "UUID",
  "animal_id": "UUID",
  "farm_id": "UUID",
  "measured_at": "ISO8601",
  "weight_kg": "float",
  "measurement_method": "scale | manual | estimated",
  "recorded_by_user_id": "UUID"
}
```

### 4.8.8 FeedRecord
```json
{
  "feed_id": "UUID",
  "farm_id": "UUID",
  "recorded_at": "ISO8601",
  "recorded_by_user_id": "UUID",
  "allocation_type": "individual | group",
  "animal_id": "UUID | null",
  "group_zone_id": "UUID | null",
  "head_count": "integer | null",
  "feed_type": "hay | grain | silage | mixed | supplement | other",
  "quantity_kg": "float",
  "cost_local_currency": "float | null",
  "currency_code": "string | null"
}
```

Group-level feed allocation (`allocation_type: group`) allows a single record to represent feed distributed to animals in a pasture zone. Per-animal attribution is computed as `quantity_kg / head_count` for analytics.

### 4.8.9 PastureZone
```json
{
  "zone_id": "UUID",
  "farm_id": "UUID",
  "name": "string",
  "polygon_geojson": "GeoJSON Polygon",
  "area_hectares": "float",
  "max_capacity_au": "float | null",
  "current_animal_count": "integer",
  "created_at": "ISO8601"
}
```

`max_capacity_au` is optional and set by the farm manager. `current_animal_count` is a computed field updated by movement events. Animal Units (AU) use the standard: 1 AU = one 450kg beef cow.

### 4.8.10 NDVIRecord
```json
{
  "ndvi_id": "UUID",
  "zone_id": "UUID",
  "image_date": "YYYY-MM-DD",
  "sentinel2_product_id": "string",
  "cloud_cover_pct": "float",
  "mean_ndvi": "float",
  "std_ndvi": "float",
  "valid_pixel_pct": "float",
  "vegetation_status": "healthy | declining | critical | data_insufficient",
  "computed_at": "ISO8601"
}
```

`sentinel2_product_id` preserves provenance. `valid_pixel_pct` measures how much of the polygon was cloud-free. Records with `valid_pixel_pct < 0.6` are flagged `data_insufficient`.

### 4.8.11 ModelPrediction
```json
{
  "prediction_id": "UUID",
  "animal_id": "UUID",
  "farm_id": "UUID",
  "model_type": "bcs | health_risk | growth_forecast | feed_cost | pasture_risk",
  "model_name": "string",
  "model_version": "string",
  "generated_at": "ISO8601",
  "input_snapshot": {},
  "output": {},
  "confidence": "float | null",
  "data_sufficiency": "sufficient | marginal | insufficient",
  "reviewed_by_user_id": "UUID | null",
  "review_label": "string | null",
  "review_at": "ISO8601 | null"
}
```

`input_snapshot` stores the exact inputs used to generate this prediction, enabling reproducibility and model debugging. `review_label` captures a veterinarian's assessment of the prediction quality, which becomes training data.

### 4.8.12 AlertRule and Alert
```json
{
  "rule_id": "UUID",
  "farm_id": "UUID",
  "rule_type": "bcs_below | weight_decline | pasture_critical",
  "threshold": "float",
  "enabled": "boolean",
  "notify_user_ids": ["UUID"]
}

{
  "alert_id": "UUID",
  "rule_id": "UUID",
  "animal_id": "UUID | null",
  "zone_id": "UUID | null",
  "triggered_at": "ISO8601",
  "trigger_value": "float",
  "delivered_at": "ISO8601 | null",
  "delivery_status": "pending | delivered | failed",
  "acknowledged_at": "ISO8601 | null"
}
```

---

## 4.9 End-to-End Workflows

### 4.9.1 Animal Registration
```
1. Manager submits animal details via web dashboard or Telegram /register
2. API validates farm_id, checks for duplicate tag_code within farm
3. Animal record created, Tag record created with assignment
4. AnimalEvent(birth or registration) created
   - First event per animal: prev_hash = "GENESIS", sequence_number = 1
   - event_hash = SHA256(canonical JSON of {event_id, animal_id, event_type,
                          timestamp, actor_user_id, payload, prev_hash})
5. QR code generated and returned (can be printed by manager)
6. Confirmation sent to requesting channel
```

### 4.9.2 Image Upload and Inference
```
1. Field worker sends /photo to Telegram bot
2. Bot checks Redis session for active animal context for this chat_id
   - If none: prompt "Send the animal tag code or scan QR"
   - Store animal_id in Redis session key: session:{chat_id}:animal_id
3. User uploads photo
4. Bot forwards image bytes to API: POST /images/upload
5. API stores image to object storage: /{farm_id}/{animal_id}/{image_id}.jpg
6. ImageRecord created with inference_status = "pending"
7. API runs synchronous quality check (< 200ms):
   - Blur: Laplacian variance < 80 -> reject: "blurry"
   - Darkness: mean pixel intensity < 40 -> reject: "dark"
   - Resolution: shorter dimension < 300px -> reject: "too_small"
8. If rejected:
   - ImageRecord.inference_status = "rejected"
   - Bot returns: "Image rejected: [reason]. Retake from 3-5m, side view."
   - Session stays active for retry
9. If accepted:
   - ImageRecord.inference_status = "queued"
   - Celery task dispatched: infer_cv.delay(image_id)
   - Bot returns: "Received. Processing image for [TAG]. Results in ~30s."
   - Session cleared
10. Celery worker (infer_cv task):
    a. Load image from object storage
    b. Run YOLOv8n: detect cattle bounding box
       - No detection -> inference_status = "failed", reason = "no_animal_detected"
       - Multiple detections -> inference_status = "failed", reason = "multi_animal"
    c. Crop bounding box + 10% padding, resize to 512x512
    d. Run EfficientNet-B3 regression head: bcs_score (1.0-9.0)
    e. Run EfficientNet-B3 classification head: health_risk (normal/watchlist/at_risk)
    f. Apply temperature scaling to classification logits
    g. Compute prediction interval for regression output
11. ModelPrediction stored with input_snapshot, output, model_version
12. ImageRecord.inference_status = "done"
13. AnimalEvent(image_upload) appended to hash chain
14. Check alert rules: if bcs_score < rule.threshold, create Alert record
15. Alert Celery task delivers Telegram message to registered manager users
16. Bot sends result to field worker:
    "Animal [TAG-001]
     BCS: 4.2 / 9  (95% CI: 3.8 - 4.6)
     Risk: watchlist  (confidence: 71%)
     Flags: coat_condition, hip_protrusion
     Recommendation: Schedule veterinary review."
```

### 4.9.3 Hash Chain Verification
```
1. Auditor requests: GET /audit/chain/{animal_id}
2. API fetches all AnimalEvents for animal, ordered by sequence_number ASC
3. Initialize: expected_prev_hash = "GENESIS"
4. For each event in sequence:
   a. Recompute hash from stored fields using canonical serialization
   b. Compare recomputed hash to stored event_hash
   c. Verify stored prev_hash == expected_prev_hash
   d. Set expected_prev_hash = event.event_hash
5. Return:
   {
     "chain_valid": true | false,
     "total_events": N,
     "first_broken_sequence": null | integer,
     "first_broken_event_id": null | UUID
   }
6. On chain break: log discrepancy, surface to auditor. No self-repair.
```

### 4.9.4 Sentinel-2 NDVI Update (Scheduled Job)
```
1. Celery Beat triggers: ndvi_sync.run() — daily at 03:00 UTC
2. Fetch all active PastureZones across all farms
3. For each zone:
   a. Query Copernicus Data Space STAC API:
      - geometry: zone polygon bbox
      - datetime: past 12 days
      - collections: ["SENTINEL-2-L2A"]
      - filter: cloud_cover < 40
   b. If no qualifying product found: log "no_clear_imagery", skip zone
   c. Select most recent qualifying product
   d. Download B04 (Red, 10m), B08 (NIR, 10m), SCL (Scene Classification) bands
   e. Reproject all bands to zone polygon CRS (EPSG:4326 or UTM zone)
   f. Clip rasters to zone polygon (rasterio.mask.mask)
   g. Apply SCL cloud mask: exclude pixels where SCL in {3,8,9,10,11}
   h. Compute valid_pixel_pct = (unmasked pixels / total pixels)
   i. If valid_pixel_pct < 0.6:
      - Store NDVIRecord with vegetation_status = "data_insufficient"
      - Skip scoring
   j. Compute NDVI = (B08 - B04) / (B08 + B04) on valid pixels
   k. Compute mean_ndvi, std_ndvi
   l. Determine vegetation_status:
      - Query NDVIRecords for same zone, same calendar week, prior years
      - If >= 2 prior years: baseline = mean of prior same-week mean_ndvi values
        ndvi_deviation = (mean_ndvi - baseline) / baseline
        if ndvi_deviation < -0.15: "declining"
        if ndvi_deviation < -0.30: "critical"
        else: "healthy"
      - If < 2 prior years (first-year deployment): use absolute thresholds
        mean_ndvi > 0.45: "healthy"; 0.25-0.45: "declining"; < 0.25: "critical"
   m. Store NDVIRecord with sentinel2_product_id for provenance
   n. If status == "critical": create Alert for zone managers
```

---

## 4.10 AI/ML Modules

### 4.10.1 Computer Vision Module

**Purpose:** Estimate body condition score and health risk band from a single side-view image of a cattle animal.

**Scope restriction:** V1 supports cattle only. Sheep and other species require separate labeled datasets and are deferred to V3. This restriction is displayed to users explicitly in the bot UX.

**Training data:**
- Primary source: published cattle BCS image datasets (Rodríguez Alvarez et al., CVPR 2018 workshop; supplementary partner-farm collections)
- Minimum deployment threshold: 500+ labeled images spanning BCS range 1–9
- Annotation protocol: two independent assessors per image; images with inter-assessor disagreement > 1.0 BCS unit are excluded; inter-rater Cohen's kappa target >= 0.75
- Augmentation: horizontal flip, brightness/contrast jitter (factor 0.8–1.2), rotation +/- 10 degrees, Gaussian noise

**Architecture:**
```
Input: smartphone image (max 1024px, resized to 512x512, ImageNet normalize)
  -> YOLOv8n detection
       no detection    -> inference failed: "no_animal_detected"
       multi-detection -> inference failed: "multi_animal"
       single det.     -> crop bbox + 10% padding, resize 512x512
  -> EfficientNet-B3 (ImageNet pretrained, fine-tuned on cattle BCS dataset)
       regression head (1 output, sigmoid * 8 + 1): bcs_score [1.0, 9.0]
       classification head (3 classes, temperature-scaled softmax):
         health_risk in {normal, watchlist, at_risk}
       auxiliary head (multi-label): reason_flags
         {coat_condition, hip_protrusion, rib_visibility,
          posture_irregularity, body_mass_loss}
```

**Output contract:**
```json
{
  "bcs_score": 4.2,
  "bcs_prediction_interval_95": [3.8, 4.6],
  "health_risk": "watchlist",
  "health_risk_confidence": 0.71,
  "reason_flags": ["coat_condition", "hip_protrusion"],
  "image_quality_score": 0.83,
  "model_version": "cv-cattle-v1.2.0",
  "low_confidence": false
}
```

`low_confidence = true` when `health_risk_confidence < 0.55`. Alerts are suppressed for low-confidence predictions.

**Evaluation targets:**
- BCS MAE <= 0.5 units vs. expert annotator on 20% stratified hold-out
- Health risk macro F1 >= 0.75 on same hold-out
- Confidence calibration ECE <= 0.10 (reliability diagram)
- Field image rejection rate < 30% on pilot sample

### 4.10.2 Time-Series Growth Forecasting Module

**Purpose:** Predict 30-day weight trajectory and feed cost per kg gain.

**Data sufficiency gate (enforced before inference):**
- Minimum: 3 weight measurements spanning >= 21 days within past 90 days
- Below minimum: return `data_sufficiency = "insufficient"` with message: "Collect at least 3 weight measurements over 3 weeks before forecasting is available."
- 3–5 measurements or measurements only from scale: `data_sufficiency = "marginal"`, wider prediction intervals
- 6+ measurements with consistent frequency: `data_sufficiency = "sufficient"`

**Feature schema:**
```
Animal features:      age_days, species_code, breed_code, sex_binary
Weight history:       last_6_weights_kg[], last_6_weight_timestamps[]
Derived weight:       avg_daily_gain_21d, avg_daily_gain_60d,
                      gain_trend_slope (linear regression on recent points),
                      days_since_last_weight
Feed features:        avg_daily_feed_kg_30d, feed_type_mode_30d (encoded),
                      avg_feed_cost_per_kg_30d, feed_event_count_30d
Environmental:        avg_temp_c_30d, total_rainfall_mm_30d
Pasture (if available): zone_mean_ndvi_current, ndvi_trend_direction (encoded)
                        (null-imputed if pasture module not active)
```

**Model:** XGBoost regressor. Dual targets: (1) predicted_weight_30d, (2) feed_cost_per_kg_gain. Trained on historical weight + feed records from system. Hyperparameter tuning via 5-fold cross-validation on time-series split.

LSTM deferred to V3 pending: 6+ months of operational data from >= 3 farms with >= 500 animal-weight series at adequate measurement frequency (>= weekly).

**Output contract:**
```json
{
  "predicted_weight_30d_kg": 418.5,
  "predicted_gain_30d_kg": 12.1,
  "prediction_interval_95": [10.2, 14.0],
  "estimated_feed_cost_per_kg_gain": 2.14,
  "currency_code": "KZT",
  "data_sufficiency": "sufficient",
  "anomaly_flag": false,
  "model_version": "forecast-v1.0.0"
}
```

**Evaluation:**
- 30-day weight MAE target: <= 0.80 × naive baseline MAE (naive = last-observed-velocity linear extrapolation)
- Feed cost relative error target: <= 15% on held-out animals with complete records

### 4.10.3 Pasture Monitoring Module

**Purpose:** Assess vegetation health and overload risk per pasture zone using NDVI time series and stocking density.

See Section 4.9.4 for the full ingestion pipeline specification.

**Output contract:**
```json
{
  "zone_id": "UUID",
  "assessment_date": "YYYY-MM-DD",
  "current_mean_ndvi": 0.38,
  "std_ndvi": 0.06,
  "valid_pixel_pct": 0.82,
  "ndvi_trend_30d": "declining",
  "ndvi_vs_baseline": -0.11,
  "baseline_available": true,
  "pasture_health_score": 54,
  "overload_risk": "medium",
  "stocking_load_ratio": 0.91,
  "recommendation": "Monitor closely. Consider 15-20% stocking reduction for 2 weeks if rainfall forecast is below average.",
  "data_note": null
}
```

Recommendation text is template-generated from rule conditions, not from a language model.

**Pasture health score computation:**
```
base = normalize(mean_ndvi, lo=0.1, hi=0.7) * 70
trend_adj = +10 if trend == "improving", -10 if "declining", -20 if "critical"
deviation_adj = clamp(ndvi_vs_baseline * 40, -20, 0)
score = clamp(base + trend_adj + deviation_adj, 0, 100)

overload_risk:
  if max_capacity_au is set:
    ratio = current_animal_count / max_capacity_au
    "high" if ratio > 1.1, "medium" if 0.85-1.1, "low" if < 0.85
  if max_capacity_au not set: "unknown"
```

---

## 4.11 Risk Aggregation Layer (V3)

In V3, a per-animal composite risk score is computed by rule-based scoring on available signals. This is an explicitly rule-based function, reviewable and adjustable by farm managers. A learned model is not introduced until labeled health outcome data (veterinary interventions, treatments, mortality events) is available as a training signal.

```
risk_points = 0
if latest bcs_score < 3.5 (low BCS):           += 30
if 30d weight gain_slope < 0 (weight loss):     += 20
if days_since_last_inspection > 30:             += 15
if zone pasture_health_score < 40:              += 20
if open_alert_count > 0:                        += 15

risk_level:
  0-30:   normal
  31-60:  watchlist
  61-100: at_risk
```

---

## 4.12 Traceability and Audit Layer

### What it is

A server-side append-only hash chain stored in the primary database. Every `AnimalEvent` record includes a deterministic hash of its own content and the hash of the preceding event in the animal's event sequence.

### What tamper-evidence means here

Any modification to a stored event (payload, timestamp, actor) will cause the stored `event_hash` to no longer match a hash recomputed from the current field values. Because subsequent events reference the prior hash, a single modification breaks the chain from that point forward.

**Limitation:** This integrity guarantee holds against passive record modification (e.g., a database edit). It does not hold against an adversary who also recomputes and overwrites all subsequent hashes. Preventing that requires an external anchor.

**External anchoring (V3 enhancement):** Compute a Merkle root over all event hashes for a given day. Publish this root to an external, independently verifiable log (e.g., a public timestamping service or a public Git commit). This creates a verifiable external reference that makes full chain reconstruction detectable without blockchain infrastructure.

### Verification API

`GET /audit/chain/{animal_id}` — available to `auditor` and `manager` roles. Recomputes all hashes from stored fields. Returns a chain validity report with position of first discrepancy if found. Read-only. No repair.

---

## 4.13 Backend Architecture

### Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| API framework | FastAPI (Python 3.11+) | Async I/O, Pydantic validation, OpenAPI generation |
| Database | PostgreSQL 15 + PostGIS | ACID, geospatial polygon storage and queries |
| Object storage | MinIO (local) or AWS S3 | Image and raster file storage |
| Task queue | Celery 5 + Redis broker | Async inference and scheduled ETL |
| ML serving | In-process (Celery worker) | Sufficient for V1 scale; migrate to Triton at production scale |
| Cache / sessions | Redis | Bot session state, alert deduplication, rate limiting |
| Auth | JWT (access 15min + refresh 7d), bcrypt | |
| Geospatial processing | rasterio, shapely, pyproj | Sentinel-2 clip, reproject, NDVI |
| Satellite API client | Copernicus Data Space STAC + CDSE S3 | L2A product query and download |

### Service communication
- **API → Celery:** Redis task queue (fire-and-forget with task ID returned to caller)
- **Celery → DB:** SQLAlchemy sessions in task workers (same PostgreSQL instance)
- **Celery → Telegram:** aiogram Bot API calls for async result delivery
- **Bot → API:** HTTPS REST (bot is a client of the API, never a direct DB accessor)
- **Scheduler:** Celery Beat for periodic jobs (NDVI sync 03:00 UTC, weather sync 06:00 UTC)

### Service layout
```
alip/
├── api/
│   ├── routers/           # Animals, events, images, zones, auth, reports, audit
│   ├── schemas/           # Pydantic request and response models
│   ├── models/            # SQLAlchemy ORM models
│   ├── services/          # Business logic: hash chain, alert evaluation, etc.
│   ├── auth/              # JWT, Telegram OTP linking, role enforcement
│   ├── db/                # Session factory, Alembic migrations
│   └── main.py
├── ml/
│   ├── cv/
│   │   ├── detector.py    # YOLOv8n localization wrapper
│   │   ├── estimator.py   # EfficientNet-B3 BCS + health risk
│   │   ├── quality.py     # Pre-inference quality checks
│   │   └── weights/       # Model weight files (.pt / .onnx)
│   ├── forecasting/
│   │   ├── features.py    # Feature engineering from DB records
│   │   ├── gate.py        # Data sufficiency evaluation
│   │   ├── predictor.py   # XGBoost inference wrapper
│   │   └── weights/
│   └── pasture/
│       ├── sentinel.py    # CDSE API + band download
│       ├── ndvi.py        # Rasterio processing pipeline
│       └── scoring.py     # Zone health score + overload risk
├── jobs/
│   ├── tasks.py           # Celery task registry
│   ├── ndvi_sync.py       # Scheduled NDVI update job
│   ├── weather_sync.py    # Scheduled weather update job
│   └── alerts.py          # Alert evaluation and Telegram dispatch
├── bot/
│   ├── handlers/          # Telegram command and message handlers
│   ├── sessions.py        # Redis-backed conversation state machine
│   └── bot.py             # aiogram application setup
├── infra/
│   ├── docker-compose.yml
│   └── Dockerfile.*
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

---

## 4.14 API Structure

### Authentication
```
POST /auth/register         Create farm + manager account
POST /auth/login            Returns {access_token, refresh_token}
POST /auth/refresh          Rotate tokens
POST /auth/telegram-link    Link Telegram chat_id via OTP (6-digit, 15min expiry)
```

### Farm and Users
```
GET   /farms/{farm_id}
PATCH /farms/{farm_id}
POST  /farms/{farm_id}/users        Invite user with role assignment
GET   /farms/{farm_id}/users
```

### Animals
```
POST   /animals
GET    /animals/{animal_id}
PATCH  /animals/{animal_id}/status       Status changes only; all edits create events
DELETE /animals/{animal_id}              Soft delete: status = "unknown"
GET    /animals?farm_id=&status=&species=&risk=
GET    /animals/{animal_id}/events
GET    /animals/{animal_id}/weights
GET    /animals/{animal_id}/predictions
```

### Events
```
POST /events
GET  /events/{event_id}
GET  /audit/chain/{animal_id}       Hash chain verification report
```

### Images
```
POST /images/upload                 Multipart; returns {image_id, inference_status}
GET  /images/{image_id}
POST /images/{image_id}/infer       Manual trigger (vet / manager only)
```

### Predictions
```
GET /animals/{animal_id}/latest-prediction?model_type=bcs
GET /animals/{animal_id}/growth-forecast
GET /zones/{zone_id}/pasture-status
GET /farms/{farm_id}/risk-ranking
```

### Zones
```
POST /zones
GET  /zones/{zone_id}
GET  /zones/{zone_id}/ndvi-history
GET  /zones/{zone_id}/pasture-status
```

### Alerts
```
GET  /alerts?farm_id=&status=
POST /alerts/{alert_id}/acknowledge
POST /farms/{farm_id}/alert-rules
PATCH /farms/{farm_id}/alert-rules/{rule_id}
```

### Reports
```
GET /reports/farm-summary?farm_id=&period=
GET /reports/animal-list?farm_id=&format=csv|json
GET /reports/at-risk-animals?farm_id=
```

---

## 4.15 Telegram Bot Design

### Authentication and account linking
```
1. Farm manager invites user via web dashboard (generates OTP)
2. User starts bot: /start
3. Bot: "Send your 6-digit registration code."
4. User sends code
5. API validates OTP, links telegram_chat_id to user record
6. Bot: "Linked to [Farm Name] as [role]. Type /help for commands."
```

### Commands
```
/start          Registration and help
/animal [tag]   Look up animal by tag code
/register       Begin animal registration flow (manager only)
/weight         Record weight for an animal
/feed           Record feeding event
/photo          Begin image upload flow for an animal
/status [tag]   Show latest status summary
/alerts         Show active farm alerts
/pasture        Show pasture zone summary
/report         Request farm summary report (manager only)
/help           Command reference
```

### Conversation state machine (Redis-backed)
```
State: IDLE
  /photo           -> "Send tag code or type animal name" -> AWAITING_ANIMAL_FOR_PHOTO
  /weight          -> "Send tag code"                     -> AWAITING_ANIMAL_FOR_WEIGHT
  /register        -> "Send new animal details"           -> REGISTERING_ANIMAL
  unrecognized msg -> "Unknown command. Try /help."

State: AWAITING_ANIMAL_FOR_PHOTO
  text or QR code  -> validate tag in farm
                      found: store animal_id, "Now send the photo" -> AWAITING_PHOTO
                      not found: "Tag not found. Try again or /cancel."
  /cancel          -> IDLE, session cleared
  timeout (5 min)  -> IDLE, session cleared, notify user

State: AWAITING_PHOTO
  photo received   -> upload, quality check, dispatch inference -> IDLE
    quality fail   -> "Image rejected: [reason]. Retry or /cancel." -> AWAITING_PHOTO
  /cancel          -> IDLE
  timeout (5 min)  -> IDLE, session cleared

State: AWAITING_ANIMAL_FOR_WEIGHT
  text             -> validate tag -> RECORDING_WEIGHT (animal_id stored)
  /cancel          -> IDLE

State: RECORDING_WEIGHT
  text (number)    -> validate float, store WeightRecord, AnimalEvent -> IDLE
                      "Weight [X] kg recorded for [TAG]."
  non-number       -> "Send a number, e.g. 312.5"
  /cancel          -> IDLE
```

### Response format examples
```
# Successful BCS result
"Animal TAG-001
 BCS: 4.2 / 9  (95% interval: 3.8 - 4.6)
 Health: watchlist  (71% confidence)
 Flags: coat_condition, hip_protrusion
 Recommendation: Schedule veterinary review."

# Low confidence result
"Animal TAG-001
 BCS: 3.9 / 9  [LOW CONFIDENCE]
 Model uncertainty is high on this image.
 Upload a second side-view photo or schedule manual inspection."

# Inference failure
"Image processing failed for TAG-001.
 Error logged. Retry with /photo or contact your manager."
```

---

## 4.16 Failure Modes and Safeguards

| Failure | Detection | Response |
|---------|-----------|----------|
| Poor image quality | Pre-inference quality classifier | Reject before inference, prompt retry with guidance |
| Low model confidence | Threshold check post-inference | Return result flagged `low_confidence=true`, suppress auto-alert |
| Inference task crash | Celery exception handler | Retry up to 2x with 30s backoff; mark `failed`, log error, notify admin |
| No animal detected | YOLOv8 detection output count = 0 | Mark `failed: no_animal_detected`, prompt retry |
| Multiple animals detected | YOLOv8 detection output count > 1 | Mark `failed: multi_animal`, prompt to photograph alone |
| Sentinel-2 data unavailable | STAC query returns no qualifying products | Skip zone update, retain prior status, log `no_clear_imagery` |
| Cold-start forecasting | Data gate returns `insufficient` | Return explicit message with data collection prompt, no prediction |
| Weather API outage | ETL exception handler | Skip weather update; impute weather features as null in forecasting |
| Hash chain break detected | Verification endpoint reports mismatch | Log discrepancy, surface to auditor. No self-repair. |
| Wrong animal-image association | Session state enforcement | Bot requires explicit animal selection before photo accepted |
| DB connection failure | Health check middleware | API returns HTTP 503 with Retry-After header |

---

## 4.17 Evaluation Plan

### Computer Vision Module

| Metric | Target | Methodology |
|--------|--------|-------------|
| BCS MAE | <= 0.5 units | 20% stratified hold-out split; expert annotator labels as ground truth |
| Health risk macro F1 | >= 0.75 | Same hold-out split; macro average across normal/watchlist/at_risk |
| Confidence calibration | ECE <= 0.10 | Reliability diagram (10 bins) on validation set |
| Image rejection rate | < 30% of field images | Measured on 100+ images from pilot farm |
| Inter-rater agreement (labels) | Cohen's kappa >= 0.75 | Two-annotator agreement on training labels before inclusion |

### Growth Forecasting Module

| Metric | Target | Methodology |
|--------|--------|-------------|
| 30-day weight MAE | <= 0.80 x naive baseline | Time-series hold-out: last 30 days per animal; naive = linear extrapolation from last two points |
| Feed cost relative error | <= 15% | Held-out animals with complete cost records |

### Pasture Module

| Metric | Target | Methodology |
|--------|--------|-------------|
| NDVI temporal consistency | < 0.05 NDVI difference between two consecutive clear-sky captures | Computed on any zone with 2+ qualifying captures in 10 days |
| Scoring agreement | >= 70% agreement with agronomist label | Manual expert review on 10+ zones across 2+ seasons |

### System-level

| Metric | Target |
|--------|--------|
| Hash chain integrity | 100% on all test events (CI-enforced) |
| CV inference latency | P95 < 5 seconds end-to-end from upload to Telegram delivery |
| API availability | >= 99% during farm operating hours (06:00-20:00 local) |

---

## 4.18 Development Roadmap

### Phase 1 — Core Platform (V1.0)
**Deliverable:** Working farm record system with full Telegram access and hash-chain audit trail.

- Farm, User, Animal, Tag entities and API
- AnimalEvent append-only schema with SHA256 hash chain
- Chain verification endpoint
- WeightRecord entry (group-level and individual)
- FeedRecord entry (group-level and individual)
- Telegram bot: register, weight, feed, status query
- Web dashboard: animal list, event timeline, QR display
- JWT auth with manager/field_worker roles
- Docker Compose deployment (API + DB + Redis + Bot)

**Demo gate:** Single farm, 10 animals, 30 days of events, chain verified intact.

### Phase 2 — AI Prototype (V1.1)
**Deliverable:** CV pipeline producing BCS estimates on uploaded cattle images.

- Image upload and storage workflow
- Pre-inference quality gate
- YOLOv8n localization + EfficientNet-B3 BCS + health risk pipeline
- ModelPrediction storage with input snapshot and model version
- Alert rules with BCS threshold triggers
- Telegram delivery of inference results and alerts

**Demo gate:** 50+ cattle images processed end-to-end; MAE and F1 documented on hold-out.

### Phase 3 — Spatial Intelligence (V2)
**Deliverable:** Sentinel-2 NDVI pipeline with pasture zone scoring.

- Copernicus Data Space integration (STAC query + CDSE S3 download)
- L2A processing: cloud masking (SCL), NDVI computation, polygon clip
- NDVIRecord storage with provenance
- Zone health scoring: rule-based with seasonal baseline
- Pasture alerts, dashboard zone map with NDVI overlay

**Demo gate:** 3 zones updated weekly for 4 weeks; outputs validated against agronomist review.

### Phase 4 — Forecasting (V2.1)
**Deliverable:** Growth and feed cost forecasting for animals with sufficient history.

- Feature engineering pipeline
- XGBoost training on collected farm data
- Data sufficiency gate
- Forecast API endpoint and dashboard

**Demo gate:** Forecasting on animals with >= 3 weight records; MAE benchmarked against naive baseline.

### Phase 5 — Integration Layer (V3)
**Deliverable:** Rule-based risk aggregation, annotation interface, retraining pipeline.

- Per-animal composite risk score
- Veterinary annotation interface for AI outputs
- Retraining trigger (manual + data-volume threshold)
- Multi-species CV model (sheep)
- External hash chain anchor implementation

---

## 4.19 Why This Architecture Is Credible

**Scope is calibrated to implementation reality.** V1 contains no ML. It builds the data foundation first. Every AI component is added in a phase where the prerequisite data has been accumulating from the prior phase. This is the correct sequencing.

**Data assumptions are made explicit.** The cold-start problem for forecasting is named and handled with an explicit gate. The Sentinel-2 preprocessing pipeline specifies product type, cloud masking method, and seasonal normalization. CV training data requirements are quantified with a minimum threshold and inter-annotator quality criterion.

**AI outputs are qualified, not oversold.** Every inference output includes confidence, data sufficiency, model version, and input snapshot. Low-confidence predictions are flagged. The system never presents AI output as ground truth. Alerts are suppressed below confidence thresholds.

**The traceability layer is honestly described.** The hash chain is server-side append-only integrity, not a blockchain. Its limitations are stated directly. An enhancement path to external anchoring is defined without overclaiming.

**Failure modes are first-class design concerns.** Every major failure path has a detection mechanism, system response, and user message. The system degrades gracefully.

**The evaluation plan has methodology.** Each AI module has a target metric, a comparison baseline, and a measurement method that can actually be executed.

---

# 5. Portfolio Positioning Notes

## 5.1 What Sounds Most Impressive to Admissions Officers

**The problem framing with domain specificity.** "Helped farmers track livestock" is weak. The correct framing is: "Designed a system to give small and medium livestock farms in low-connectivity agricultural regions a structured digital record system with AI-assisted health monitoring, satellite pasture analysis, and a tamper-detectable audit trail." That sentence signals: you understand the user, the environment, the technology, and the constraints. Admissions readers respond to that combination.

**The interdisciplinary reach.** This project visibly crosses: backend systems engineering, computer vision, time-series machine learning, remote sensing (Sentinel-2, NDVI, phenological baselines), database design, and agricultural domain knowledge. The range is unusual among student projects. Emphasize that you had to learn domain-specific things — what body condition scoring is, how NDVI works, why seasonal normalization matters for pasture assessment — that you could not find in a standard CS course.

**The phase-gated roadmap.** The explicit decision to build a functional data system before adding ML, and to add ML modules in sequence with prerequisite data accumulation, signals engineering maturity. Most student projects either build everything poorly or build a tiny slice. Knowing what order to build things in is a real skill.

**The hash-chain traceability layer.** One sentence: "I built an append-only hash-linked event log that makes farm records tamper-detectable without blockchain infrastructure." Accessible to a general admissions reader, impressive to a technical one, and — crucially — it is honest about what it is.

## 5.2 What Sounds Most Impressive to Engineers

**The data sufficiency gate on forecasting.** Naming the cold-start problem and designing an explicit gate — "minimum 3 weight measurements spanning 21 days before forecasting runs; below that, return `data_sufficiency = insufficient` with a collection prompt" — is the kind of detail that marks a person who has thought about production data pipelines, not just model training notebooks.

**The image quality pre-inference pipeline.** Blur detection via Laplacian variance, darkness check, multi-animal detection via YOLO count — all before the main model runs. This is production ML hygiene. Most portfolio CV projects skip it entirely.

**The Sentinel-2 preprocessing specificity.** Naming L2A products, SCL band cloud masking, valid_pixel_pct thresholds, seasonal phenological normalization, and the Copernicus Data Space STAC API — these are details that signal actual satellite data engineering knowledge. The engineer reviewer knows this is a real pipeline problem that most people underestimate.

**Temperature scaling for confidence calibration.** Noting that raw softmax probabilities are not calibrated probabilities and applying temperature scaling to the classification head — this is an advanced applied ML insight that most students do not know. It signals genuine model deployment thinking.

**The canonical hash serialization rule.** Specifying "sorted keys, no whitespace" for the hash input — this is the type of detail that breaks hash chain implementations across language boundaries (Python vs. JavaScript vs. Go) and demonstrates awareness of real implementation pitfalls.

**The group-level feed allocation.** Recognizing that small farms feed animals in groups, not individually, and designing a `FeedRecord` with `allocation_type: group` and per-head attribution — this is domain-aware data modeling that most student projects ignore because they have never talked to a farmer.

## 5.3 What Must Be Demonstrated with Evidence

Do not claim any of the following without a screenshot, working output, or executable demo:

- **CV inference end-to-end:** Show an actual cattle image → YOLOv8 crop → EfficientNet output with BCS score, confidence interval, health risk band, and reason flags
- **Hash chain verification:** Show chain verification on a clean chain, then show detection of a break after manually modifying a stored event payload in the database
- **Telegram bot conversation:** Screenshots of the complete /photo flow from send-photo to receive-result
- **NDVI output:** Show a real polygon processed through the pipeline with a computed mean NDVI, sentinel2_product_id, cloud masking statistics, and vegetation_status assigned
- **Evaluation metrics:** Show a real hold-out evaluation table with MAE, F1, sample size, and baseline comparison. Hypothetical targets are not evidence.

If any of these are not yet built, describe them as "designed and in development" rather than claiming completion.

## 5.4 What Should Not Be Exaggerated in Interviews

**Do not say "the AI diagnoses diseases."** The correct statement: "The model produces a health risk band — normal, watchlist, or at-risk — as a decision-support signal. It is not a diagnostic tool. It flags animals for veterinary review."

**Do not say "it works offline."** V1 requires internet. Correct statement: "V1 requires connectivity. I designed the event schema to support an offline-first mobile client in a later phase, but that is not yet implemented."

**Do not say "it is like a blockchain."** Correct statement: "It is an append-only hash-linked event log that makes tampering detectable within the database. It is not a distributed ledger. For external verifiability, you would need to anchor periodic digests to a public timestamping service, which is on the roadmap."

**Do not say the forecasting model is a neural network.** The V1 model is XGBoost on structured features. That is the correct choice given data volume. If asked why not LSTM: "An LSTM needs substantial sequential data. With a new farm deployment, I don't have enough measurement history to train a sequence model that beats a structured feature approach. I designed a data gate that defers deep sequence modeling until that data exists."

**Do not claim the system is production-deployed on real farms unless it is.** Correct framing: "It is a functional pilot-scale system. I have validated it on a demo farm setup. Production deployment on real farms would require additional field testing, regulatory consideration for specific markets, and expanded training data."

## 5.5 How to Describe the Project Orally

**One-sentence version:**
"I built an agricultural software platform that combines computer vision, satellite pasture analysis, and time-series forecasting to help livestock farms track animal health, monitor grazing conditions, and maintain an auditable record system — accessible from a Telegram bot for field workers with basic smartphones."

**Two-minute technical version:**
"The foundation of the system is an append-only event log — every farm event, from a weight measurement to an AI health assessment, is stored as a hash-linked record, so the history is tamper-detectable. The three AI modules are: first, a computer vision pipeline that takes a side-view cattle photo, runs YOLOv8 to localize the animal, then runs a fine-tuned EfficientNet to estimate body condition score on a 1-to-9 scale and classify health risk — with a pre-inference quality gate that rejects blurry or poorly framed images before the model runs; second, a growth forecasting module using XGBoost on structured features like weight history, feed records, and weather data — but I built an explicit data sufficiency gate, so the system refuses to forecast if there are fewer than three weight measurements, rather than producing nonsense from thin data; and third, a satellite pasture monitoring pipeline that ingests Sentinel-2 L2A imagery from the Copernicus Data Space API, applies cloud masking with the scene classification layer, clips rasters to farm polygon zones, and computes NDVI against a seasonal phenological baseline to score pasture health. The user interface is a Telegram bot, which is the right choice for this use case — no app install, works on basic Android phones, low bandwidth. The architecture is explicitly phased: V1 is the record system and bot only, V2 adds the computer vision pipeline, V3 adds satellite and forecasting — because the right sequencing is to collect real data before you try to model it."

**When asked what was hardest:**
"Three things I did not anticipate going in. First, getting labeled training data for body condition scoring — it is a specialized annotation task that requires trained livestock assessors, not crowdsourced labelers. I had to reach out to veterinary contacts and find published research datasets, then design an annotation protocol with inter-rater agreement criteria before I trusted the labels. Second, the Sentinel-2 pipeline — I assumed it would be like calling an API and getting back a number. In reality you have cloud masking, atmospheric correction, raster reprojection, polygon clipping, and the problem that NDVI values are meaningless without a seasonal baseline because a low NDVI in winter is normal and a low NDVI in summer is a problem. Third, the hardest architectural decision was scope discipline — deciding what to defer. There is a strong temptation to claim multimodal fusion and LSTM and emissions metrics in the same project. I had to be honest that those features require data I don't have yet, and that building a system that works correctly at V1 is more valuable than claiming V4 capabilities that don't run."

---

*End of document.*
