# UnibaBot PDA

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Test accuracy](https://img.shields.io/badge/test%20accuracy-1.000-success.svg)](Docs/UnibaBot_PDA.pdf)
[![LLM](https://img.shields.io/badge/LLM-Qwen%202.5%2014B-7c3aed.svg)](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-Next.js%2014-black.svg)](https://nextjs.org/)

Intelligent agent that automates compliance verification of Academic Development Plans (PDAs) at Universidad de Ibagué. Given a PDA in PDF format, the system evaluates it against 179 institutional guidelines and produces a structured report with cited evidence and prescriptive corrections.

> **Course:** Intelligent Agents — Software Engineering, Universidad de Ibagué (2025-2026).
> **Authors:** Kevin Beltrán Martínez (2220221003), Jeryleefth Lasso Motta (2220231074).
> **Technical report:** [Docs/UnibaBot_PDA.pdf](Docs/UnibaBot_PDA.pdf) (IEEE format).

## Results on the gold dataset

| Split | Accuracy | Precision NC | Recall NC | Matched | Latency |
|-------|----------|--------------|-----------|---------|---------|
| Train (51 entries, 3 PDAs) | **1.000** | **1.000** | **1.000** | 51/51 | ~290 s |
| Test hold-out (55 entries, 3 unseen PDAs) | **1.000** | **1.000** | **1.000** | 55/55 | ~330 s |

NC = NO CUMPLE class (real non-compliance findings). The hold-out test set is the metric of record because it measures generalization to PDAs the system has never seen.

The full narrative (methodology, per-iteration metric progression, related work, ablations, failure analysis) is in [Docs/UnibaBot_PDA.pdf](Docs/UnibaBot_PDA.pdf). For the head-to-head comparison between the rule-driven and semantic-RAG dispatchers, see [results/rag_vs_rules_benchmark.md](results/rag_vs_rules_benchmark.md).

## Architecture

The system has **two independent layers**: the compliance engine and the production stack.

**Layer 1 — Compliance engine (AI pipeline):** Docling parses the PDF into sections, eleven deterministic structural checks run in pure Python, an early classifier rejects documents that are not PDAs, a rule dispatcher maps every applicable rule to its target section, a single Qwen 2.5 14B call extracts declared canonical codes (C1, 1b, SP5, D4, ABET X.Y) with verbatim evidence, an evidence validator rejects hallucinations, and a deterministic matcher decides compliance via regex and set intersection. Optional LLM enrichment generates prescriptive corrections per finding and dual-audience summaries, both backed by a SHA-256 cache for bit-exact idempotency.

**Layer 2 — Production stack (web + queue + worker):** A FastAPI backend exposes the engine over HTTP with JWT auth and synchronous PDA validation. Uploads are queued in Redis via RQ; an RQ worker consumes the queue and runs the engine asynchronously, publishing progress events on a Redis pub/sub channel. The Next.js 14 frontend subscribes to those events via SSE and renders progress, results, and rejection messages as a chat-style conversation.

For the full architecture diagram, design decisions, and the comparison with the discarded fine-tuning route, see the [IEEE technical report](Docs/UnibaBot_PDA.pdf).

## Quickstart

The recommended path on any operating system (including Windows) is Docker Compose:

```bash
# Make sure ollama is running on the host (ollama serve) with qwen2.5:14b pulled
docker compose up --build
```

This starts redis, the FastAPI API, the RQ worker, and the Next.js frontend. Open `http://localhost:3000` and register a user.

For local development on macOS or Linux:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-api.txt
ollama pull qwen2.5:14b

# Terminal 1: Redis
docker run --rm -d --name unibabot-redis -p 6379:6379 redis:7-alpine
# Terminal 2: FastAPI
make dev-api
# Terminal 3: RQ worker
make dev-worker
# Terminal 4: Next.js
cd web && npm install && npm run dev
```

The CLI is the simplest entry point for evaluation:

```bash
# Analyze a single PDA
python src/agent.py "PDAs/<pda_file>.pdf" 22A14

# Evaluate against the gold dataset
python src/evaluate.py --tag my_run
python src/evaluate.py --tag my_run_test --gold-path data/gold_labels_test.json
```

A Streamlit demo is also available (`streamlit run streamlit_app.py`) for quick interactive exploration.

## Project layout

```
src/                  # Compliance engine (Layer 1)
  agent.py            # End-to-end pipeline (CLI / API / Streamlit entrypoint)
  pdf_parser.py       # Docling-based extraction and section segmentation
  pda_classifier.py   # Rule-based "is this a PDA?" classifier
  evaluate.py         # Evaluation harness for the gold dataset
  common/             # Logging, typed exceptions, ollama wrapper, text utils
  rules/              # Structural checks, declaration extractor, deterministic matcher
  enrichment/         # Optional LLM enrichment with SHA-256 cache
  rag/                # Rule dispatcher (production) + RAG path (alternative reference)
  api/                # FastAPI backend, RQ jobs, SSE progress (Layer 2)
web/                  # Next.js 14 frontend (Layer 2)
tests/                # Pytest suite (classifier, API, auth)
data/                 # Rules, gold labels, SQLite (PDAs and ChromaDB are gitignored)
results/              # Tagged metrics + progression notes
Docs/                 # IEEE technical report (drafts and slides are gitignored)
docker-compose.yml    # Orchestrates redis + api + worker + web
```

## Key technical decisions

1. **The LLM extracts; Python decides.** The probabilistic step is fact extraction (codes and verbatim evidence). Compliance is decided by deterministic regex + set intersection, so every verdict is reproducible and auditable.
2. **Rule-driven dispatch instead of semantic retrieval.** Iterating over the rules applicable to a course guarantees 100% coverage. The semantic-RAG path was kept as an alternative reference and is benchmarked head-to-head in [results/rag_vs_rules_benchmark.md](results/rag_vs_rules_benchmark.md): identical accuracy on matched entries, but RAG silently drops 13 entries (6 train + 7 test) because their target section has more applicable rules than top-k.
3. **Evidence-aware extraction closes the last false positive.** The extractor returns `{code, snippet, section, type}` per declared code; the validator rejects anything whose snippet is not present in the PDA text. This is what brings the hold-out from 0.982 to 1.000.
4. **Synchronous PDA validation before enqueuing.** The classifier runs Docling and a structural-rule sanity check at upload time and rejects non-PDAs (papers, syllabi, scanned-without-OCR, corrupt PDFs) with HTTP 422 and a natural-language message. The frontend renders the rejection as an assistant message in the chat, not as a transient toast.
5. **Fine-tuning was explored and discarded.** A QLoRA attempt on Llama 3.2 3B with 42 self-instruct examples produced a feedback loop that degraded the model. The engineering route (Docling, rule-driven dispatch, larger off-the-shelf model, deterministic matcher) reached the project's targets without specialization. The full account is in the IEEE report.

## Limitations

- **Latency.** ~290–330 s per PDA, dominated by the single Qwen 2.5 14B extraction call. Acceptable for batch review of ~20 PDAs per semester; would need a GPU host for real-time use.
- **PDF format dependence.** Scanned PDAs without OCR and PDFs with very atypical layouts can defeat Docling. The early classifier rejects those upfront.
- **Single-program dataset.** Six PDAs from Systems Engineering. Robustness on PDAs from other programs (humanities, business) is not measured.

The implementation milestones (m0–m18) that led to the production configuration are documented in the IEEE technical report.

## Authors

- Kevin Beltrán Martínez (2220221003)
- Jeryleefth Lasso Motta (2220231074)

Systems Engineering, Universidad de Ibagué, 2026A — Intelligent Agents course.

## License and institutional data

The code in this repository is distributed under the [MIT license](LICENSE). This covers the entire pipeline (`src/`), the frontend (`web/`), tests, and the institutional rule definitions in `data/lineamientos/`.

The actual PDA PDFs under `PDAs/` and the ChromaDB index under `data/chroma_db/` are academic data of Universidad de Ibagué and are NOT part of the public repository (see `.gitignore`). Reproducing the metrics requires authorized access to the original PDAs of the evaluated academic program.
