# Benchmark: rule-driven vs semantic RAG

Empirical head-to-head between the two dispatchers that coexist in `src/rag/`. Isolates the variable "how is the rule set to evaluate selected" while keeping the rest of the pipeline (parser, LLM extractor, deterministic matcher, enrichment) identical.

## Methodology

**Pipeline shared by both arms:**

```
PDF -> pdf_parser (Docling) -> rules/estructural_checker (11 EST)
                            -> rules/declaracion_extractor (1 LLM call per PDA)
                            -> rules/declaracion_checker (regex + set intersection)
                            -> JSON report
```

**The only thing that changes:**

| Step | Rule-driven (`dispatcher="rule"`) | Semantic RAG (`dispatcher="rag"`) |
|------|-----------------------------------|------------------------------------|
| How the rule set to evaluate is obtained | `reglas_aplicables(codigo_curso)`: iterates `reglas.json` and returns every rule with `aplica_a in (course, "todos")`. 100% coverage by construction. | `recuperar_reglas_aplicables(secciones, codigo_curso, top_k=5)`: for each PDA section, queries ChromaDB with multilingual SBERT + a cross-encoder reranker. Unions the top-k of every section. Rules outside top-k are never evaluated. |

**LLM:** Qwen 2.5 14B (same in both arms).
**Hardware:** MacBook Pro M3 18 GB.
**RAG top-k:** 5 (historical default m4–m10).
**Reranker:** active (`use_reranker=True`).

**Datasets:**
- Train: `data/gold_labels.json` — 51 entries, 3 PDAs (22A14, 22A12, 22A31).
- Test (hold-out): `data/gold_labels_test.json` — 55 entries, 3 unseen PDAs (22A32, 22A35, 22A52).

**Known bias:** the gold dataset was built by iterating over the rule-driven dispatcher, which biases it structurally: entries that the rule-driven path would never generate (e.g., an applicable rule that does not translate into a finding) never enter the gold. This is why RAG starts at a coverage disadvantage. We report this explicitly as "matched / total" and separate accuracy (over matched) from coverage (matched / total) so the metrics are not contaminated.

## Results

### Train (51 entries, 3 PDAs: 22A12, 22A14, 22A31)

| Metric | Rule-driven | Semantic RAG (top-k=5) | Delta |
|--------|-------------|------------------------|-------|
| Accuracy (over matched) | **1.000** | **1.000** | =  |
| Precision NO CUMPLE | **1.000** | **0.000***  | -1.000 |
| Recall NO CUMPLE | **1.000** | **0.000***  | -1.000 |
| Coverage (matched / 51) | **51 / 51 (100.0%)** | **45 / 51 (88.2%)** | -6 rules |
| not_found | 0 | 6 | +6 |
| Total latency (3 PDAs) | 153.6 s | 147.9 s | -3.7% (RAG slightly faster) |

\*The single NO CUMPLE entry of the train gold (`COMP-119`, course 22A31) falls inside the 6 entries RAG fails to recover. By construction it produces neither TP nor FP, so precision and recall collapse to 0/0. The rule-driven path captures, matches, and reports it correctly.

### Test hold-out (55 entries, 3 unseen PDAs: 22A32, 22A35, 22A52)

| Metric | Rule-driven | Semantic RAG (top-k=5) | Delta |
|--------|-------------|------------------------|-------|
| Accuracy (over matched) | **1.000** | **1.000** | =  |
| Precision NO CUMPLE | **1.000** | **1.000** | =  |
| Recall NO CUMPLE | **1.000** | **1.000** | =  |
| Coverage (matched / 55) | **55 / 55 (100.0%)** | **48 / 55 (87.3%)** | -7 rules |
| not_found | 0 | 7 | +7 |
| Total latency (3 PDAs) | 161.4 s | 158.9 s | -1.5% |

In the test split, RAG keeps precision/recall NC = 1.000 because the 7 real NC entries WERE retrieved. But it loses 7 CUMPLE entries (all in courses 22A32 and 22A52) that the rule-driven path evaluates and reports correctly.

### Detail of the 13 entries RAG never evaluates

| Split | rule_id | Course | PDA | PDA section | Expected state | Probable cause |
|-------|---------|--------|-----|-------------|----------------|----------------|
| train | COMP-105 | 22A14 | Intelligent Agents | "Classroom typology" | CUMPLE | English-language section, embedding far from the abstract vocabulary of the rule |
| train | COMP-119 | 22A31 | UIUX Development | "Generic competencies:" | **NO CUMPLE** | top-k=5 saturated by other rules in the same section |
| train | COMP-120..123 | 22A31 | UIUX Development | "Generic competencies:" | CUMPLE (x4) | Same: section with many applicable rules, top-k saturates |
| test | COMP-107..115 | 22A32 | IT Management | "Competencies / Learning Outcomes" | CUMPLE (x6) | Large section with many applicable rules; top-k=5 leaves at least 6 out |
| test | COMP-006 | 22A52 | Computational Thinking | "Competencies" | CUMPLE | Idem |

**Single pattern:** every loss comes from **sections where the number of rules applicable to the course exceeds top_k**. The reranker does not solve it: it only re-orders within the bi-encoder's top-k. Raising top-k mitigates but does not scale (course 22A32 has 10 rules in one section; guaranteeing coverage would require top-k >= 10 per section, which neutralizes the semantic ranking — and cost grows linearly).

## Case study: bilingual PDA (22A14, "Intelligent Agents")

This PDA has section headers in English ("Pedagogical Strategy(ies)", "Classroom typology"). Historically it was the case where the semantic retriever lost the most coverage. Smoke test executed before the formal benchmark:

| Dispatcher | EST findings | COMP declarations | Total |
|------------|--------------|-------------------|-------|
| Rule-driven | 11 | 6 | 17 |
| Semantic RAG (top-k=5) | 11 | 5 | 16 |

The lost rule is **COMP-105** (Dimension D4 International, declared in the "Classroom typology" section). The retriever does not rank it in the top-5 of any section because the embedding of the rule ("Dimensión D4: Internacional") is far from the embedding of the English content. Rule-driven evaluates the rule without consulting embeddings: it finds it via the keyword fallback in `rule_dispatcher.encontrar_seccion_destino`.

## Setup costs

| Concept | Rule-driven | Semantic RAG |
|---------|-------------|--------------|
| Persisted on disk | `data/lineamientos/reglas.json` (60 KB) | `data/chroma_db/` (1.1 MB) plus the JSON above |
| Extra dependencies | (none) | `chromadb>=0.5.0`, `sentence-transformers>=3.0.0`, `torch>=2.0.0` |
| Initial setup | (none; reads JSON on the fly) | `python src/rag/ingest.py` (~30 s, downloads the SBERT model the first time) |
| Re-indexing when rules change | None; the JSON is re-read every run | Re-run `ingest.py` (seconds per chunk) |
| Embedding models loaded | (none) | SBERT `all-MiniLM-L6-v2` (~80 MB RAM) + multilingual cross-encoder (~280 MB) |

## Theoretical scalability

Let N be the number of rules and S the number of PDA sections.

| Operation | Rule-driven | Semantic RAG |
|-----------|-------------|--------------|
| Load rules in memory | O(N) once per process | O(N) initial ingestion; O(1) recall on queries |
| Filter rules for a course | O(N) direct list lookup | O(N) metadata filter + O(top_k) semantic ranking |
| Dispatch rules to sections | O(N x S) name match + keyword fallback | O(S x retrieve_k x emb_dim) per embedding query plus reranker |
| Add a new rule | O(1): edit JSON, done | Re-run `ingest.py` (full re-embedding if model changes, partial otherwise) |
| Expected growth at 1000 rules | Same latency | Latency grows linearly with N in the filter; O(log N) in the ANN search |

**Implication:** the rule-driven path scales better in maintenance (adding rules does not require reprocessing the corpus) and latency (no embedding query cost per section). Semantic RAG would only be preferable if the rule catalog grew to a point where iterating over every applicable rule for a course became prohibitive (>10K rules/course, out of scope for this project).

## Conclusions

1. **Coverage is the differentiator, not verdict quality.** Over the gold entries that both dispatchers evaluate, accuracy is 1.000 in both arms. But semantic RAG loses 13 entries (6 train + 7 test) that the rule-driven path evaluates. The critical loss: the only NO CUMPLE entry of the train split (`COMP-119`, course 22A31) falls within the 6 entries RAG does not recover.

2. **The RAG bottleneck is structural, not solvable by tuning.** The 13 losses follow one pattern: PDA sections where the number of applicable rules exceeds `top_k=5`. The reranker does not help (it re-orders within the bi-encoder top-k, it does not expand the set). Raising top-k mitigates but does not scale: course 22A32 has 10 rules in a single section; guaranteeing coverage would require top-k >= 10 per section, which neutralizes the semantic ranking.

3. **Rule-driven operational savings:** ~360 MB of models in RAM (SBERT bi-encoder + cross-encoder reranker), 1.1 MB on-disk vector store, and the `torch`, `sentence-transformers`, `chromadb` dependencies. At project volumes (179 rules, 23 courses) the rule-driven path is strictly dominant.

4. **Comparable latency at this scale.** At 179 rules and ~10 sections per PDA, the embedding query cost per section is comparable to the list lookup. The difference would only become significant at much larger scales, where rule-driven keeps constant latency while RAG pays `S x retrieve_k x emb_dim` per PDA.

5. **When to reconsider:** rule-driven dominates while N (rules) is small and the catalog changes infrequently. Semantic RAG would only be preferable if the catalog grew to thousands of rules AND natural-language querying over the rules became part of the use case (rather than evaluating against structured PDAs). For UnibaBot's institutional scope (finite, version-controlled JSON catalog) rule-driven is the correct architectural choice.

## Reproducibility

```bash
# Re-ingest rules into ChromaDB (required for the RAG path)
python src/rag/ingest.py

# Train benchmark
python src/evaluate.py --tag bench_rule_train --dispatcher rule --gold-path data/gold_labels.json
python src/evaluate.py --tag bench_rag_train --dispatcher rag --gold-path data/gold_labels.json

# Test benchmark
python src/evaluate.py --tag bench_rule_test --dispatcher rule --gold-path data/gold_labels_test.json
python src/evaluate.py --tag bench_rag_test --dispatcher rag --gold-path data/gold_labels_test.json

# Compare two saved runs
python src/evaluate.py --compare bench_rule_train bench_rag_train
```

Metrics are persisted in `results/metrics_<tag>.json`. Raw reports in `results/reports_<tag>.json`.
