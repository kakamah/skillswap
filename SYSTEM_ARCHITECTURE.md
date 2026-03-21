# System Architecture Document
## Data Science and Research Pipeline for Kazakhstan Public Procurement Risk Analysis

**Version:** 1.0  
**Date:** 2026-03-21  
**Purpose:** Academic and policy-paper-grade analysis of procurement behavior, with focus on cartel structures, hidden affiliations, and corruption risk signals.  
**Design Principle:** Maximum analytical rigor under strict budget/time constraints; no enterprise overengineering.

---

## 1. Executive Summary and Research Objectives

### 1.1 Problem Statement
Kazakhstan public procurement data is fragmented, noisy, partially dynamic, and frequently obfuscated by:
- inconsistent legal entity names,
- rapid ownership changes near tender events,
- address and contact reuse across nominally independent bidders,
- mixed Cyrillic/Latin symbol substitution,
- scanned (image-only) technical documents.

Traditional one-table or snapshot analysis fails to preserve temporal evidence and network structure. The required system must therefore be a **batch-first, historically aware, graph-enabled research pipeline**.

### 1.2 Core Objective
Design a production-grade research architecture that can:
1. Collect and preserve procurement evidence at scale.
2. Reconstruct entity identity and ownership history over time.
3. Build affiliation graphs for cartel-like behavior discovery.
4. Produce statistically defendable risk indicators for a policy paper.

### 1.3 Scope (In-Scope)
- Scheduled batch ingestion from API and scraping fallback.
- Evasion layer: residential proxy rotation, headless automation, anti-captcha integration.
- OCR extraction for scanned tender specifications.
- Raw/staging/core data layers in PostgreSQL and/or Parquet object storage.
- SCD Type 2 temporal modeling with `valid_from` and `valid_to`.
- Neo4j graph modeling for deep relationship traversal and network analytics.
- Deterministic plus probabilistic entity resolution.
- Statistical anomaly detection and graph metrics (Louvain, betweenness, density).
- Kazakhstan-specific contextual false-positive controls (anti-dumping, systemic enterprise filters).

### 1.4 Explicit Non-Goals (Out-of-Scope)
To prevent scope and budget explosion, the following are intentionally excluded:
- UI product design, complaint generators, DOCX/PDF legal submission workflows.
- Real-time streaming/event systems (Kafka, RabbitMQ, Celery).
- Kubernetes and distributed microservice orchestration.
- Arbitrary rule points such as "+50 if X matches".

### 1.5 Research Outputs
The architecture is designed to produce:
- reproducible datasets,
- transparent feature definitions,
- methodologically sound risk distributions (not black-box accusations),
- explainable graph and statistical evidence for policy analysis.

### 1.6 Design Principles
1. **Batch over real-time:** Daily/periodic recomputation is acceptable and preferred.
2. **Evidence preservation:** Never overwrite historical ownership/registration facts.
3. **Deterministic traceability:** Every analytic output references raw lineage.
4. **Statistical defensibility:** Use distributions, confidence intervals, and normalized deviations.
5. **Context-aware filtering:** Avoid legal/sector false positives by explicit domain controls.
6. **Operational simplicity:** Single-node or dual-node Docker Compose deployment only.

### 1.7 Success Criteria
- >= 99% batch completion without full-pipeline crash.
- Full temporal reproducibility for ownership/address changes.
- Graph analytics runs on refresh schedule without manual rewriting.
- Risk outputs are explainable by formula and source evidence.
- False positives reduced via contextual filters for anti-dumping and mega-entities.

---

## 2. High-Level Data Flow Diagram (Mermaid.js)

```mermaid
flowchart TD
    A[Official Sources: Goszakup/eGov/KGD] --> B[Batch Collector Scheduler]
    B --> C{Acquisition Mode}
    C -->|API First| D[API Pull Workers]
    C -->|Fallback| E[Headless Browser Workers<br/>Playwright + Proxy Rotation + Anti-Captcha]
    D --> F[Raw Landing<br/>PostgreSQL raw.* and/or Parquet object storage]
    E --> F

    F --> G[Document Extractor]
    G --> H{Document Type}
    H -->|Text PDF| I[Direct Text Extraction]
    H -->|Image/Scan| J[OCR Pipeline<br/>Tesseract/Neural OCR]
    I --> K[Staging Normalization]
    J --> K

    K --> L[Entity Resolution Pipeline<br/>Deterministic + Probabilistic]
    L --> M[SCD Type 2 Core Model<br/>valid_from / valid_to]
    M --> N[Graph Projection Jobs]
    N --> O[Neo4j Affiliation Graph]

    M --> P[Feature Mart Builder]
    O --> P
    P --> Q[Analytics Engine<br/>Statistical + Graph Algorithms]
    Q --> R[Research Outputs<br/>Risk distributions, network motifs, policy evidence tables]

    S[Data Quality & Lineage Audits] --> F
    S --> K
    S --> M
    S --> Q
```

### 2.1 Pipeline Cadence
- **Ingestion batch:** every 2-6 hours (source dependent).
- **Normalization + SCD merge:** daily.
- **Graph rebuild/incremental merge:** daily or every 12 hours.
- **Scoring/analytics refresh:** daily; weekly deep recomputation.

### 2.2 Batch Orchestration Model
- Cron-based or lightweight scheduler (e.g., Prefect/APS-like orchestrator in batch mode).
- No streaming queues required.
- Every stage writes checkpoints (`run_id`, `batch_id`, `source_cursor`, `checksum`).

---

## 3. Ingestion and Anti-Ban Subsystem Details

### 3.1 Acquisition Strategy: API-First with Scraping Fallback
1. Attempt official API endpoints and published datasets first.
2. If fields are unavailable or delayed, use browser-driven scraping fallback.
3. Persist raw payload exactly as received before transformation.

### 3.2 Batch Worker Topology (Single Codebase, Multi-Process)
- `collector_api_worker.py`
- `collector_browser_worker.py`
- `document_fetch_worker.py`
- `ocr_worker.py`
- `normalization_worker.py`

All workers are executed in scheduled batches; no message broker is required.

### 3.3 Anti-Ban Controls
#### 3.3.1 Residential Proxy Rotation
- Proxy pool with health score and cooldown.
- Rotation key: `(target_host, session_window, response_code trend)`.
- Automatic quarantine for proxy nodes with repeated 403/429/5xx spikes.

#### 3.3.2 Headless Browser Hardening
- Playwright Chromium contexts with:
  - rotating user agents,
  - cookie/session isolation per run,
  - randomized viewport and timezone profiles,
  - bounded navigation retries with exponential backoff.

#### 3.3.3 Anti-Captcha Integration
- Challenge detector in browser DOM/network layer.
- Provider abstraction (`solve_captcha(challenge_type, image_or_token)`).
- Captcha audit table stores:
  - challenge type,
  - solve latency,
  - success/failure,
  - source URL,
  - run_id.

### 3.4 Raw Evidence Model
Raw zone stores immutable payload and fetch metadata:
- `source_system`
- `source_endpoint`
- `source_cursor`
- `source_batch_id`
- `payload_checksum`
- `payload_json/xml`
- `http_status`
- `scraped_at`
- `request_fingerprint`

This allows reprocessing without re-scraping and enables strict lineage.

### 3.5 OCR Pipeline Design
#### 3.5.1 Document Classification
- Check extractable text ratio.
- If ratio < threshold, classify as scanned.

#### 3.5.2 OCR Flow
1. Convert pages to images.
2. Run OCR model with `kaz + rus + eng`.
3. Store page-level confidence and coordinates where available.
4. Reconstruct document text in canonical UTF-8.
5. Tag low-confidence pages for manual audit list (optional offline review).

#### 3.5.3 OCR Storage
- `doc_id`, `page_no`, `ocr_text`, `confidence`, `engine_version`, `run_id`.
- Keep both original binary metadata and OCR outputs.

### 3.6 Data Quality Safeguards
- Empty batch detection (possible source layout/API mutation).
- Schema drift detector for source payload keys.
- Duplicate suppression using `(source_cursor, checksum)`.
- Retry policy limited to transient failures; hard failures logged and skipped.

### 3.7 Failure Isolation
Failure in one source batch must not terminate all sources:
- Batch-level status (`success`, `partial_success`, `failed`).
- Failed records moved to error quarantine table with reason codes.
- Pipeline continues with next batch window.

---

## 4. Data Modeling: SCD Type 2 Schema and Entity Resolution Pipeline

### 4.1 Storage Layers
#### 4.1.1 Raw Layer
- PostgreSQL `raw.*` tables for immediate ingest and metadata.
- Optional Parquet object storage partitioned by `source/date`.

#### 4.1.2 Staging Layer
- Parsed, normalized, denoised fields.
- Holds quality flags and match candidates.

#### 4.1.3 Core Layer (Temporal)
- Canonical entities with SCD Type 2 versioning.
- Fact tables for tender participation, outcomes, and pricing evolution.

### 4.2 SCD Type 2 Requirements (Strict)
For every historical attribute subject to change (ownership, director, address):
- `valid_from TIMESTAMPTZ NOT NULL`
- `valid_to TIMESTAMPTZ NULL`
- one active row where `valid_to IS NULL`
- immutable historical rows (no destructive overwrite)

### 4.3 Example Relational Schema (Core)

```sql
CREATE TABLE core.company_scd (
    company_scd_id      BIGSERIAL PRIMARY KEY,
    company_bin         TEXT NOT NULL,
    company_name_norm   TEXT,
    company_type        TEXT,
    registration_rka    TEXT,
    address_norm        TEXT,
    source_hash         TEXT NOT NULL,
    valid_from          TIMESTAMPTZ NOT NULL,
    valid_to            TIMESTAMPTZ,
    is_current          BOOLEAN NOT NULL DEFAULT TRUE,
    source_raw_id       BIGINT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ux_company_current
ON core.company_scd(company_bin)
WHERE is_current = TRUE;

CREATE TABLE core.company_person_role_scd (
    company_person_role_scd_id BIGSERIAL PRIMARY KEY,
    company_bin         TEXT NOT NULL,
    person_iin          TEXT NOT NULL,
    role_type           TEXT NOT NULL,   -- founder, director, beneficiary
    role_share_percent  NUMERIC(5,2),
    valid_from          TIMESTAMPTZ NOT NULL,
    valid_to            TIMESTAMPTZ,
    is_current          BOOLEAN NOT NULL DEFAULT TRUE,
    source_raw_id       BIGINT
);

CREATE TABLE core.tender_participation_fact (
    participation_id    BIGSERIAL PRIMARY KEY,
    tender_id           TEXT NOT NULL,
    lot_id              TEXT NOT NULL,
    protocol_date       DATE NOT NULL,
    buyer_bin           TEXT,
    supplier_bin        TEXT,
    submitted_amount    NUMERIC(18,2),
    awarded_amount      NUMERIC(18,2),
    protocol_status     TEXT,
    rejection_reason    TEXT,
    is_antidumping      BOOLEAN,
    source_raw_id       BIGINT,
    UNIQUE(protocol_date, tender_id, lot_id, supplier_bin)
);
```

### 4.4 SCD2 Merge Logic
For each incoming entity version:
1. Compute normalized hash of tracked attributes.
2. Compare against active row.
3. If changed:
   - close active row (`valid_to = now()`, `is_current=false`),
   - insert new active row (`valid_from = now()`, `valid_to=NULL`).
4. If unchanged: keep current row, only update ingestion metadata if needed.

### 4.5 Entity Resolution Pipeline
Entity linkage is implemented in two phases.

#### 4.5.1 Deterministic Pass (High Precision)
- Legal entities by BIN.
- Individuals by IIN.
- Exact registration codes where available.
- Exact tax identifiers and official registry IDs.

#### 4.5.2 Probabilistic Pass (Recall Recovery)
Applied only when deterministic keys are missing/incomplete:
- Name similarity (Jaro-Winkler, token set overlap).
- Address similarity with RKA-aware normalization.
- Contact overlap (email/phone partial normalization).
- Temporal consistency checks (implausible overlap suppression).

Output:
- `entity_cluster_id`
- `match_method` (`deterministic`, `probabilistic`)
- `confidence_score` (0..1)
- `evidence_fields` JSON

### 4.6 Address Normalization with RKA Codes
Address pipeline:
1. Unicode NFKC normalization.
2. Common abbreviation expansion.
3. Street/building token canonicalization.
4. RKA lookup and geocode enrichment.
5. Mass-registration address flagging for down-weighting in analytics.

### 4.7 Mixed Cyrillic/Latin Text Normalization
To prevent obfuscation:
- confusable character map (Latin->Cyrillic for known homographs),
- whitespace/punctuation normalization,
- token language consistency checks.

Applied to:
- company names,
- technical specification text,
- tender titles/descriptions.

### 4.8 Lineage and Reproducibility
Every transformed record retains:
- `source_raw_id`
- `source_cursor`
- `source_batch_id`
- `checksum`
- `transform_run_id`

This supports full forensic traceability from policy-paper figure back to raw source.

---

## 5. Graph Database Architecture (Neo4j Node/Edge Definitions)

### 5.1 Why Neo4j is Mandatory
Deep affiliation detection requires variable-length path traversal, motif search, and community analysis. These workloads are graph-native and are not efficient in relational deep-join patterns for exploratory research scale.

### 5.2 Graph Scope
Graph captures both structural and temporal relations across entities involved in procurement.

### 5.3 Node Definitions
- `:Company {bin, name_norm, company_type, size_class, valid_from, valid_to}`
- `:Person {iin, fio_norm, valid_from, valid_to}`
- `:Address {rka_code, address_norm, lat, lon}`
- `:Tender {tender_id, buyer_bin, publish_date}`
- `:Lot {lot_id, tender_id, category_code, is_antidumping}`
- `:Phone {phone_norm}`
- `:Email {email_norm}`
- `:BankAccount {iban_hash}`

### 5.4 Edge Definitions
- `(:Person)-[:IS_FOUNDER_OF {valid_from, valid_to, share_pct, source_ref}]->(:Company)`
- `(:Person)-[:IS_DIRECTOR_OF {valid_from, valid_to, source_ref}]->(:Company)`
- `(:Company)-[:REGISTERED_AT {valid_from, valid_to, source_ref}]->(:Address)`
- `(:Company)-[:PARTICIPATED_IN {bid_amount, result, protocol_date, source_ref}]->(:Lot)`
- `(:Company)-[:CONTRACTED_BY {award_amount, contract_date}]->(:Buyer)` (optional buyer node)
- `(:Company)-[:USES_PHONE {valid_from, valid_to}]->(:Phone)`
- `(:Company)-[:USES_EMAIL {valid_from, valid_to}]->(:Email)`
- `(:Company)-[:SHARES_IDENTIFIER_WITH {identifier_type, confidence, evidence}]->(:Company)`

### 5.5 Temporal Semantics
All sensitive relations include `valid_from` and `valid_to`.
Queries for event date `t` must filter:
`valid_from <= t AND (valid_to IS NULL OR valid_to > t)`.

### 5.6 Constraints and Indexes
```cypher
CREATE CONSTRAINT company_bin IF NOT EXISTS
FOR (c:Company) REQUIRE c.bin IS UNIQUE;

CREATE CONSTRAINT person_iin IF NOT EXISTS
FOR (p:Person) REQUIRE p.iin IS UNIQUE;

CREATE INDEX company_name_norm IF NOT EXISTS
FOR (c:Company) ON (c.name_norm);

CREATE INDEX address_rka IF NOT EXISTS
FOR (a:Address) ON (a.rka_code);
```

### 5.7 Graph Build Strategy
- Daily projection from core SCD and fact tables.
- Incremental upsert keyed by `bin`, `iin`, `lot_id`.
- Tombstone/close relationship validity windows instead of hard delete.

### 5.8 Example Temporal Relationship Merge
```cypher
MERGE (p:Person {iin:$iin})
MERGE (c:Company {bin:$bin})
MERGE (p)-[r:IS_FOUNDER_OF {source_ref:$source_ref}]->(c)
SET r.valid_from = datetime($valid_from),
    r.valid_to   = CASE WHEN $valid_to IS NULL THEN NULL ELSE datetime($valid_to) END,
    r.share_pct  = $share_pct;
```

### 5.9 Graph Access Patterns for Research
- K-hop neighborhood extraction around entity clusters.
- Co-participation motifs in same lots over rolling windows.
- Shared identifier path discovery (`email`, `phone`, `address`, `person`).
- Time-sliced snapshots for before/after ownership transitions.

---

## 6. Statistical and Graph Analytics Methodology (Specific Algorithms)

### 6.1 Methodological Framework
The analytics engine combines:
1. **Graph structure metrics** for network-level suspicion.
2. **Statistical anomaly detection** for behavioral deviation.
3. **Context filters** to suppress known legal/structural false positives.

No arbitrary point assignment is allowed.

### 6.2 Unit of Analysis
Primary entities:
- supplier company,
- buyer organization,
- lot/tender event,
- affiliation component (graph community).

Time windows:
- rolling monthly and quarterly windows,
- event-aligned windows around tender publication and award dates.

### 6.3 Graph Algorithms
#### 6.3.1 Louvain Community Detection
Purpose: detect dense bidder-affiliation communities potentially representing coordinated rings.

Outputs:
- `community_id`
- modularity score
- community size and concentration metrics

Interpretation:
Communities with high internal co-participation and repeated near-neighbor ties are priority candidates for deeper checks.

#### 6.3.2 Betweenness Centrality
Purpose: identify brokers/bridge entities linking otherwise separate groups.

Statistic:
`CB(v) = sum_{s!=v!=t} sigma_st(v) / sigma_st`

Interpretation:
High-centrality intermediaries may indicate service coordinators, nominee operators, or network orchestrators.

#### 6.3.3 Network Density and Cohesion
For community `C`:
`density(C) = 2E / (N*(N-1))` (undirected approximation)

High density plus repeated co-bidding across short windows raises coordination hypothesis strength.

### 6.4 Statistical Anomaly Detection

#### 6.4.1 Z-Score Based Deviations
For metric `x` in peer group:
`z = (x - mu_peer) / sigma_peer`

Use cases:
- abnormal rejection rates by buyer,
- abnormal bid delta distributions,
- abnormal winner concentration.

#### 6.4.2 Robust Standardization for Heavy Tails
Where normality is weak, use robust z-score:
`z_robust = (x - median) / (1.4826 * MAD)`

#### 6.4.3 Empirical Distribution and Tail Probability
Compute empirical quantile rank and p-value approximation:
- `p = 1 - F_empirical(x)` for right-tail events.
- Events in extreme tail (e.g., >99th percentile) are flagged for review.

### 6.5 Composite Risk Index (Statistical, Not Arbitrary)
Risk index for entity `e` at time `t`:

`RI(e,t) = 100 * sum_i w_i * S_i(e,t)`

Where:
- `S_i` are normalized statistical signals in [0,1] derived from z-scores/quantiles,
- `w_i` are calibrated by validation experiments and stability analysis, not manual arbitrary points.

Calibration approach:
- holdout historical windows,
- optimize for precision/recall against known cases or expert-labeled sample,
- perform sensitivity analysis for weight perturbation.

### 6.6 Contextual Filters (Kazakhstan-Specific False Positive Control)

#### 6.6.1 Anti-Dumping Legal Context Filter
For categories where anti-dumping constraints legally compress price deltas:
- disable or down-weight bid-delta anomaly signal,
- retain only non-price indicators (network ties, rejection anomalies, rotation patterns).

#### 6.6.2 Systemic Enterprise Filter
Large systemic actors (e.g., BI Group, House of Ministries related entities) can create high-degree graph artifacts.
- Tag such entities by curated registry.
- Apply separate baseline cohort and degree normalization.
- Prevent automatic high-risk escalation solely due to centrality or participation volume.

#### 6.6.3 Mass Address Filter
Known business-center mass addresses can inflate affiliation edges.
- Use address rarity weights.
- Require multi-signal confirmation (address + phone/email/time pattern) before escalation.

### 6.7 Example Feature Families
- Co-bidding overlap index over rolling windows.
- Bid spread compression anomalies.
- Buyer-level rejection skew against peer baseline.
- Temporal founder/director change proximity to tender milestones.
- Shared contact identifiers among competitors in same lot.

### 6.8 Validation and Scientific Integrity
- Report confidence intervals for major indicators.
- Keep model cards for each signal (definition, assumptions, bias risks).
- Perform backtesting by period to detect drift.
- Maintain reproducible notebooks/scripts linked to `run_id`.

---

## 7. Infrastructure Setup (Single/Dual Robust Server Setup with Docker Compose)

### 7.1 Deployment Philosophy
Use a **modular monolith pipeline** deployed via Docker Compose.  
No Kubernetes, no service mesh, no distributed orchestration complexity.

### 7.2 Option A: Single Robust Server (Recommended MVP)
Best when team and budget are limited.

#### 7.2.1 Services
- `postgres` (raw/staging/core/mart schemas)
- `neo4j`
- `pipeline-runner` (scheduled batch jobs, ingestion, normalization, analytics)
- `scheduler` (cron/Prefect server in batch mode)
- `minio` (optional local object storage for Parquet and documents)

#### 7.2.2 Compose Example (Condensed)
```yaml
version: "3.9"
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: research
      POSTGRES_PASSWORD: research
      POSTGRES_DB: procurement
    ports: ["5432:5432"]
    volumes: ["pg_data:/var/lib/postgresql/data"]

  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/research123
    ports: ["7474:7474", "7687:7687"]
    volumes: ["neo4j_data:/data"]

  pipeline-runner:
    build: ./pipeline
    depends_on: [postgres, neo4j]
    environment:
      DB_DSN: postgresql://research:research@postgres:5432/procurement
      NEO4J_URI: bolt://neo4j:7687
    volumes: ["./pipeline:/app"]

  scheduler:
    build: ./pipeline
    command: ["bash", "-lc", "python jobs/scheduler.py"]
    depends_on: [pipeline-runner]

volumes:
  pg_data:
  neo4j_data:
```

### 7.3 Option B: Dual Server Setup (Scale-Ready, Still Simple)

#### Server 1 (Ingestion + Raw/Core Persistence)
- PostgreSQL primary (`raw`, `staging`, `core`).
- Batch collectors + OCR workers.
- Writes canonical tables and checkpoint metadata.

#### Server 2 (Analytics + Graph)
- Read-replicated PostgreSQL analytical copy (`mart`).
- Neo4j graph engine.
- Statistical and graph batch analytics jobs.

Data movement:
- Scheduled logical replication or periodic dump/restore for analytical tables.
- Nightly graph projection from replicated data.
- No event streaming fabric required.

### 7.4 Hardware Baseline
#### Single Server
- 16 vCPU, 64 GB RAM, NVMe SSD >= 2 TB.

#### Dual Setup
- Server 1: 8-12 vCPU, 32-64 GB RAM (ingestion-heavy).
- Server 2: 16-32 vCPU, 64-128 GB RAM (analytics-heavy).

### 7.5 Operations and Reliability
- Daily backups for PostgreSQL and Neo4j.
- Retention policy for raw payload and OCR artifacts.
- Run-level observability tables:
  - `ops.pipeline_run`
  - `ops.batch_checkpoint`
  - `ops.data_quality_issue`
- Alerting on:
  - zero-record batches,
  - schema drift,
  - OCR confidence collapse,
  - analytics runtime outliers.

### 7.6 Security and Governance
- Secrets via environment injection or local secret manager.
- Encrypt-at-rest volumes where feasible.
- Strict PII minimization in exports.
- Access control by role (ingestion operator, analyst, reviewer).

---

## 8. Technology Stack Justification

### 8.1 Python (Core Language)
Why:
- strongest ecosystem for scraping, OCR, NLP preprocessing, and statistical computing,
- mature tooling for ETL and data quality,
- low friction for rapid research iteration.

Key libraries:
- scraping/browser: `playwright`, `httpx`, `beautifulsoup4`
- parsing/OCR: `pymupdf`, `pytesseract`, optional deep OCR model
- data: `pandas`, `polars`, `pyarrow`
- stats: `scipy`, `statsmodels`
- ER/linkage: `rapidfuzz`, `recordlinkage` (or custom probabilistic matcher)

### 8.2 PostgreSQL 15 (Raw/Staging/Core + Analytical SQL)
Why:
- ACID integrity for source lineage and SCD2 merges,
- robust JSONB support for raw evidence,
- strong indexing and SQL analytics capabilities,
- operational simplicity versus multi-database sprawl.

### 8.3 Parquet/Object Storage (Optional but Valuable)
Why:
- low-cost archival for heavy raw exports and reproducible snapshots,
- efficient columnar reads for offline experiments.

### 8.4 Neo4j 5 (Affiliation Graph Layer)
Why:
- graph-native traversal and path analytics,
- mature procedures for community and centrality algorithms,
- better fit than relational recursive joins for deep network discovery.

### 8.5 Scheduler/Orchestration (Batch Only)
Recommended:
- OS cron + Python job runner for lean deployments, or
- lightweight orchestrator in scheduled mode.

Why:
- deterministic runs and checkpoints,
- minimal moving parts,
- aligns with non-real-time requirement.

### 8.6 Statistical Stack
- `scipy/statsmodels` for z-score, robust estimators, distribution diagnostics.
- optional notebook environment for research reproducibility.

Why:
- transparent, explainable, court/audit-friendly methodology over black-box outputs.

### 8.7 What Was Deliberately Rejected
Rejected by design:
- Kafka/RabbitMQ/Celery real-time queue architecture.
- Kubernetes/microservice control plane complexity.
- SaaS UX/report generation product layers.
- hardcoded rule points disconnected from statistical calibration.

### 8.8 Final Justification
This architecture is the minimum-complexity design that still satisfies:
- anti-ban collection reality in Kazakhstan,
- temporal evidence preservation,
- graph-native affiliation analytics,
- statistically rigorous and context-aware risk scoring,
- deployability by a small research engineering team.

It is intentionally practical, academically defensible, and scalable without entering enterprise overengineering territory.

---

## Implementation Sequence (Pragmatic)
1. Bootstrap PostgreSQL schemas and SCD2 tables.
2. Implement API-first ingestion with immutable raw writes.
3. Add browser fallback with proxy/captcha handling.
4. Integrate OCR and text normalization.
5. Build deterministic then probabilistic entity resolution.
6. Implement daily SCD2 merges.
7. Project graph to Neo4j and run Louvain/betweenness/density jobs.
8. Implement statistical anomaly features and calibrated composite risk index.
9. Add contextual filters (anti-dumping and systemic entities).
10. Produce policy-paper datasets, method notes, and reproducible run artifacts.
