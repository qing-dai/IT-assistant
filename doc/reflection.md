# Design Reflection  <!-- omit in toc -->

## 1. External Sources

Two sources were selected: **Reddit (`r/sysadmin`)** and **Ars Technica (`/security/`)**.

For Reddit, I evaluated several subreddits and settled on `r/sysadmin` as the most relevant to IT managers — it covers real operational issues, incidents, and vendor problems that practitioners care about.

For Ars Technica, I initially tried their RSS feed but found it only covers general top-level categories, is served as a static HTML page, and is capped at 20 articles — unsuitable for a real-time stream. I switched to scraping the `/security/` section directly, which allows topic-specific filtering and pagination for deeper fetches. The trade-off is brittleness: if the page layout changes, the scraper must be updated.

Both sources are registered in `data/sources/`, which acts as a simple registry. Adding a new source only requires implementing the `NewsSource` base class and registering it there — no other files need to change.

---

## 2. Hybrid Filter + LLM Judge

Empirical IR research consistently shows hybrid filters outperform either lexical or semantic alone, so the pipeline combines three signals:

### a. BM25 (Lexical, 30%)
BM25 matches a predefined vocabulary of ~40 query terms against the incoming batch using TF-IDF weighting. Critically, BM25 is run in **batch mode** across all articles in the request — this is intentional, as BM25 scores are only meaningful relative to the document corpus, not in isolation.

### b. Hard-Keep Rules (Boost +0.15)
29 high-signal phrases (e.g. `"zero-day"`, `"actively exploited"`, `"ransomware"`) trigger a hard boost to the fused score. In practice, exact keyword rules like these are extremely reliable for critical incidents and act as a safety net independent of the probabilistic scoring.

### c. Semantic Embeddings (50%)
Since there is no user query to match against (unlike a chatbot), I defined four IT incident categories with detailed prototype descriptions:
- `security_incident`, `service_outage`, `major_bug_patch`, `vendor_advisory`

Each incoming article is embedded and compared against all four prototype embeddings. The highest cosine similarity score becomes the semantic score, and the winning category is recorded for traceability.

### Fused Score

```
fused_score = 0.30 × lexical + 0.50 × semantic + (0.15 if hard_keep)
```

> Note: freshness weight was initially 0.20 but was removed from the filter gate after evaluation (see §4). Freshness is still used in the final ranking score.

### Triage Decision

| fused_score | Decision          |
| ----------- | ----------------- |
| ≥ 0.75      | Auto-keep         |
| < 0.45      | Auto-discard      |
| 0.45 – 0.75 | LLM judge (GPT-5) |

All vocabulary — prototype descriptions, BM25 terms, and hard-keep phrases — is centralised in `tools/vocabulary.py`. Thresholds and weights live in `config.py`. Neither requires touching any business logic to update.

---

## 3. LLM Judge

For borderline articles (fused score 0.45–0.75), GPT-5 is called to make the final keep/discard decision. The prompt asks for:
- A binary `keep` decision
- A `relevance_score` from 0–100
- A short `reason`

The 0–100 scale is preferred over a Likert scale based on empirical findings (including my own thesis work) showing LLMs produce better-calibrated outputs in this format. An article is kept only if `keep=true` **and** `relevance_score ≥ 70`.

If the LLM keeps the article, the `relevance_score / 100` is used as the `final_score` (replacing the fused score). This gives the LLM's judgment direct influence on ranking.

To avoid serial API latency, LLM calls are dispatched **concurrently** using `ThreadPoolExecutor` with up to 10 workers, reducing wall-clock time from O(n) sequential calls to roughly O(n/10).

The output schema is enforced via OpenAI's structured JSON output feature, ensuring `(keep, relevance_score, reason)` are always present and correctly typed.

---

## 4. Ranking

```
rank_score = 0.80 × final_score + 0.20 × freshness_score
```

Ranking considers both relevance and recency. `freshness_score` decays linearly over 7 days (score = 0 beyond one week). It is computed at **ingest time** and stored in the DB — this makes the ranking deterministic and stable: the same batch always returns the same order.

The retrieve query sorts by `rank_score DESC, published_at DESC, article_id ASC`. The secondary and tertiary sort keys only activate on ties, ensuring fully deterministic results.

> **Trade-off:** Because `rank_score` is frozen at ingest time, an article's rank does not decay after ingestion. In a long-running system, this could be improved by recomputing freshness dynamically at query time. For this pipeline, stability was prioritised; the dashboard displays `published_at` so users can easily identify and discount older articles themselves.

---

## 5. Data Integrity

**`NewsEntry`** (Pydantic) enforces the ingest API contract — `id`, `source`, `title`, `published_at` are required; `body` is optional. Invalid payloads are rejected with HTTP 422 before reaching the pipeline.

**`ScoredNewsEntry`** enforces the internal schema throughout the pipeline, ensuring all fields (`keep`, `rank_score`, `decision_source`, etc.) are always present when persisting to SQLite.

**LLM output** is validated via OpenAI's JSON schema enforcement plus Pydantic (`LLMJudgeResult`), so malformed responses are caught and logged rather than silently corrupting the DB.

Both kept and discarded articles are persisted — this enables evaluation, debugging, and audit of every triage decision.

---

## 6. Evaluating Correctness and Efficiency

### Correctness

The correct approach is to build a benchmark dataset of representative articles annotated by domain experts (IT professionals), then run the pipeline against it and compare decisions using:

- **Precision** — of articles kept, how many should have been kept
- **Recall** — of articles that should be kept, how many were caught
- **F1** — harmonic mean of precision and recall
- **NDCG / MAP** — for evaluating ranking quality, not just binary keep/discard

For this pipeline, I constructed a synthetic benchmark of 113 articles (`data/benchmark.csv`) annotated by GPT-4o as a proxy for domain expert annotation. The evaluation notebook (`analysis/evaluate.ipynb`) runs the full pipeline in-memory (`persist=False`) against this dataset and computes all metrics, saving results to `analysis/eval_runs/` for cross-run comparison.

### Efficiency

Efficiency covers both **latency** and **cost**:

- **Latency** — use [Langfuse](https://langfuse.com) to trace LLM and embedding call durations; use OpenTelemetry for service-level tracing; use Prometheus to monitor `/retrieve` call frequency, DB query time, and CPU/memory usage
- **Cost** — the primary lever is reducing LLM calls. A stronger hybrid filter means fewer articles fall in the 0.45–0.75 borderline zone, directly reducing API spend. Parallelising LLM calls reduces latency without reducing cost.

---

## 7. Pipeline Optimisation: Findings and Changes

### Observations from the first evaluation run (92 articles)

Running the pipeline on an initial subset revealed a structural bias against Ars Technica articles:

- **Freshness penalty**: Reddit posts are typically hours old; Ars Technica security articles are often days or weeks old. With freshness weight at 0.20, older Ars articles received near-zero freshness scores, pulling their fused scores below the 0.45 discard threshold — even when content was highly relevant. 23 Ars articles were auto-discarded; zero Reddit articles were.
- **BM25 vocabulary mismatch**: Ars Technica uses different terminology than the BM25 query terms were tuned for. Words like `"hacked"`, `"compromised"`, `"attack"`, `"backdoor"` were missing, causing `lexical_score=0` for most Ars articles.
- **Hyphen normalisation gap**: `"supply-chain"` in article text never matched `"supply chain attack"` in `KEEP_TERMS` because `normalize_text` did not strip hyphens.

Among the borderline articles sent to the LLM judge: ~85% of Ars articles were kept; ~80% of Reddit articles were discarded. This confirmed the fused score was under-valuing Ars content at the filter stage, not at the relevance stage.

### Changes made

1. **Removed freshness from the filter gate** — set `freshness_weight=0.00` in the fused score. Freshness is still used in `rank_score` for ordering. This allows older but relevant articles to reach the LLM judge.
2. **Extended BM25 vocabulary** — added `"hacked"`, `"compromised"`, `"attack"`, `"backdoor"`, `"infected"`, `"exfiltration"`, `"phishing"` and others to `BM25_QUERY_TERMS`.
3. **Fixed hyphen normalisation** — `normalize_text` now replaces hyphens with spaces before matching.
4. **Updated LLM prompt** — added explicit guidance for field reports of confirmed attack patterns and supply-chain attacks on open-source packages, which were previously under-scored.

### Results (113-article benchmark)

| Metric          | Baseline | Optimised | Δ         |
| --------------- | -------- | --------- | --------- |
| Precision       | 0.679    | 0.806     | +0.127    |
| Recall          | 0.594    | 0.781     | +0.187    |
| F1              | 0.633    | 0.794     | +0.161    |
| False negatives | 13       | 7         | −6        |
| False positives | 9        | 6         | −3        |
| Auto-discard    | 29       | 58        | +29       |
| Sent to LLM     | 78       | 54        | −24       |
| LLM kept        | 22/78    | 30/54     | 28% → 56% |

The optimised pipeline is more decisive: more articles are resolved without LLM calls, and the articles that do reach the LLM are higher quality — the LLM keep rate more than doubled.

> **Caveat:** These optimisations were derived from observations on the benchmark dataset itself. This risks overfitting to the benchmark. In a production setting, vocabulary tuning and threshold selection should be done on a separate validation set, with the test set held out until final evaluation.

---

## 8. Proposed Improvements

1. **Source-specific vocabularies** — Reddit and Ars Technica use different registers (informal vs. formal; anecdotal vs. reported). Separate BM25 term lists and hard-keep phrases per source would improve lexical scoring accuracy.

2. **Source-specific fused-score thresholds** — following from the above, the 0.45–0.75 borderline zone could be tuned per source to better target the LLM judge where it adds most value.

3. **Expert-defined category prototypes and vocabulary** — the four semantic category prototypes and the BM25/hard-keep terms were designed by prompting GPT. In practice, IT professionals should define and validate these to better reflect what actually matters operationally.

4. **Domain-specific models** — both the embedding model (`text-embedding-3-small`) and LLM judge (`GPT-5`) are general-purpose OpenAI models. Domain-specific or fine-tuned alternatives could improve accuracy and reduce cost.

5. **LLM-refined category assignment** — the predicted category is always taken from the semantic step, which may not be accurate for borderline articles. For LLM-judged articles, the LLM could also assign the final category before DB persistence.

6. **Dynamic recency in ranking** — `rank_score` is currently frozen at ingest time. Recomputing `freshness_score` dynamically at query time would ensure rankings always reflect true article age, at the cost of slightly more complex retrieval logic.
