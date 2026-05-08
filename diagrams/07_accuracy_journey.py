#!/usr/bin/env python3
"""
Genera el grafico de evolucion de accuracy del pipeline UnibaBot PDA.
Datos reales de results/accuracy_progression.md.

Uso:
    pip install matplotlib
    python diagrams/07_accuracy_journey.py
    # Genera: diagrams/rendered/accuracy_journey.png y .svg
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np

OUT_DIR = os.path.join(os.path.dirname(__file__), "rendered")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Fase 1: dataset original 48 entradas (sin split) ─────────────────────────
F1_LABELS = [
    "Baseline\nLlama 3.2 3B",
    "Reglas\nEstructurales\nEST-001..011",
    "Filtro\nRetrieval\npor Seccion",
    "Pydantic\n+ Retry",
    "Few-shot\nPrompting",
    "Llama 3.1 8B\n(8B params)",
    "Mapeo\nSecciones\n(m8b)",
]
F1_ACC = [0.351, 0.927, 0.944, 0.947, 0.951, 1.000, 1.000]
F1_COV = [37, 41, 36, 38, 41, 41, 45]   # matched / 48
F1_MAX = 48

F1_DECISIONS = [
    "RAG clasico\nsin checks Python",
    "Python puro\npara estructurales",
    "Filtro semántico\npor metadato",
    "Validacion\nestructurada JSON",
    "Ejemplos 2+1\nCUMPLE/NO CUMPLE",
    "Modelo LLM\nmas capaz",
    "Longest-match\nkeyword routing",
]

# ── Fase 2: dataset expandido, metrica en TEST hold-out (55 entradas) ─────────
F2_LABELS = [
    "m10 RAG\n(test, 55 ent.)\n69% cob.",
    "m11 Rule-driven\n(test, 55 ent.)\n100% cob.",
    "m12 Qwen\n2.5 14B\n(test)",
    "m13 Extractor\nDeterministico\n(test)",
    "m14 Docling\nParser\n(test)",
    "m15 Evidence\nValidator\nFINAL",
]
F2_ACC = [0.974, 0.873, 0.891, 0.982, 1.000, 1.000]
F2_COV = [38, 55, 55, 55, 55, 55]    # matched / 55
F2_MAX = 55

F2_ANNOTATIONS = {
    1: ("100% cobertura\n(+17 entradas\nnuevas)", "#b45309"),
    3: ("LLM extrae\nPython decide", "#1d4ed8"),
    5: ("1.000 train\n1.000 test\nProduccion", "#15803d"),
}

# ── Colores ───────────────────────────────────────────────────────────────────
def bar_color(acc):
    if acc < 0.90:
        return "#ef4444"
    if acc < 0.98:
        return "#f97316"
    return "#22c55e"

# ── Figura ────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(20, 10), facecolor="#f8fafc")
gs = gridspec.GridSpec(2, 2, figure=fig, height_ratios=[3, 1], hspace=0.35, wspace=0.12)

ax_f1 = fig.add_subplot(gs[0, 0])
ax_f2 = fig.add_subplot(gs[0, 1])
ax_cov_f1 = fig.add_subplot(gs[1, 0])
ax_cov_f2 = fig.add_subplot(gs[1, 1])

# ── Barra Fase 1 — accuracy ───────────────────────────────────────────────────
x1 = np.arange(len(F1_LABELS))
colors1 = [bar_color(a) for a in F1_ACC]
bars1 = ax_f1.bar(x1, F1_ACC, color=colors1, width=0.55, edgecolor="white",
                  linewidth=1.5, zorder=3)

ax_f1.set_facecolor("#f8fafc")
ax_f1.set_ylim(0, 1.16)
ax_f1.set_xticks(x1)
ax_f1.set_xticklabels(F1_LABELS, fontsize=8.5, ha="center", multialignment="center")
ax_f1.set_ylabel("Accuracy", fontsize=11, fontweight="bold", color="#374151")
ax_f1.set_title(
    "Fase 1 — Dataset Original (48 entradas, 4 PDAs)\n"
    "Iteraciones del enfoque RAG con mejoras incrementales",
    fontsize=11, fontweight="bold", pad=10, color="#1e293b"
)
ax_f1.axhline(y=1.0, color="#22c55e", linestyle="--", alpha=0.6, linewidth=1.2, zorder=2)
ax_f1.grid(axis="y", alpha=0.25, zorder=0, color="#cbd5e1")
ax_f1.spines["top"].set_visible(False)
ax_f1.spines["right"].set_visible(False)
ax_f1.spines["left"].set_color("#cbd5e1")
ax_f1.spines["bottom"].set_color("#cbd5e1")

for bar, acc in zip(bars1, F1_ACC):
    ax_f1.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.012,
               f"{acc:.3f}", ha="center", va="bottom",
               fontsize=9, fontweight="bold", color="#374151")

ax_f1.annotate("Arquitectura RAG clasica\nsin Python deterministico",
               xy=(0, 0.351), xytext=(0.8, 0.5),
               fontsize=7.5, color="#6b7280",
               arrowprops=dict(arrowstyle="->", color="#6b7280", lw=0.9))

# ── Barra Fase 2 — accuracy ───────────────────────────────────────────────────
x2 = np.arange(len(F2_LABELS))
colors2 = [bar_color(a) for a in F2_ACC]
bars2 = ax_f2.bar(x2, F2_ACC, color=colors2, width=0.55, edgecolor="white",
                  linewidth=1.5, zorder=3)

ax_f2.set_facecolor("#f8fafc")
ax_f2.set_ylim(0, 1.16)
ax_f2.set_xticks(x2)
ax_f2.set_xticklabels(F2_LABELS, fontsize=8.5, ha="center", multialignment="center")
ax_f2.set_ylabel("Accuracy (hold-out test)", fontsize=11, fontweight="bold", color="#374151")
ax_f2.set_title(
    "Fase 2 — Dataset Expandido (55 entradas test, 3 PDAs no vistos)\n"
    "Evaluacion en conjunto hold-out — arquitectura rule-driven",
    fontsize=11, fontweight="bold", pad=10, color="#1e293b"
)
ax_f2.axhline(y=1.0, color="#22c55e", linestyle="--", alpha=0.6, linewidth=1.2, zorder=2)
ax_f2.grid(axis="y", alpha=0.25, zorder=0, color="#cbd5e1")
ax_f2.spines["top"].set_visible(False)
ax_f2.spines["right"].set_visible(False)
ax_f2.spines["left"].set_color("#cbd5e1")
ax_f2.spines["bottom"].set_color("#cbd5e1")

for bar, acc in zip(bars2, F2_ACC):
    ax_f2.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.012,
               f"{acc:.3f}", ha="center", va="bottom",
               fontsize=9, fontweight="bold", color="#374151")

for idx, (text, color) in F2_ANNOTATIONS.items():
    ax_f2.annotate(text,
                   xy=(idx, F2_ACC[idx]),
                   xytext=(idx + (0.9 if idx < 4 else -1.1), F2_ACC[idx] - 0.06),
                   fontsize=7.5, color=color, ha="center",
                   arrowprops=dict(arrowstyle="->", color=color, lw=0.9))

# ── Barra cobertura Fase 1 ────────────────────────────────────────────────────
cov1_pct = [c / F1_MAX for c in F1_COV]
bars_c1 = ax_cov_f1.bar(x1, cov1_pct, color="#94a3b8", width=0.55,
                          edgecolor="white", linewidth=1.2, zorder=3)
ax_cov_f1.set_facecolor("#f8fafc")
ax_cov_f1.set_ylim(0, 1.12)
ax_cov_f1.set_xticks(x1)
ax_cov_f1.set_xticklabels(F1_LABELS, fontsize=7, ha="center", multialignment="center")
ax_cov_f1.set_ylabel("Cobertura", fontsize=9, fontweight="bold", color="#374151")
ax_cov_f1.set_title("Entradas evaluadas / total (48)", fontsize=9, color="#374151", pad=4)
ax_cov_f1.grid(axis="y", alpha=0.25, zorder=0, color="#cbd5e1")
ax_cov_f1.spines["top"].set_visible(False)
ax_cov_f1.spines["right"].set_visible(False)
for bar, cov in zip(bars_c1, F1_COV):
    ax_cov_f1.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.01,
                   f"{cov}/{F1_MAX}", ha="center", va="bottom", fontsize=7.5, color="#374151")

# ── Barra cobertura Fase 2 ────────────────────────────────────────────────────
cov2_pct = [c / F2_MAX for c in F2_COV]
bar_col_cov2 = ["#ef4444" if c < F2_MAX else "#22c55e" for c in F2_COV]
bars_c2 = ax_cov_f2.bar(x2, cov2_pct, color=bar_col_cov2, width=0.55,
                          edgecolor="white", linewidth=1.2, zorder=3, alpha=0.75)
ax_cov_f2.set_facecolor("#f8fafc")
ax_cov_f2.set_ylim(0, 1.12)
ax_cov_f2.set_xticks(x2)
ax_cov_f2.set_xticklabels(F2_LABELS, fontsize=7, ha="center", multialignment="center")
ax_cov_f2.set_ylabel("Cobertura", fontsize=9, fontweight="bold", color="#374151")
ax_cov_f2.set_title("Entradas evaluadas / total (55)", fontsize=9, color="#374151", pad=4)
ax_cov_f2.grid(axis="y", alpha=0.25, zorder=0, color="#cbd5e1")
ax_cov_f2.spines["top"].set_visible(False)
ax_cov_f2.spines["right"].set_visible(False)
for bar, cov in zip(bars_c2, F2_COV):
    ax_cov_f2.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.01,
                   f"{cov}/{F2_MAX}", ha="center", va="bottom", fontsize=7.5, color="#374151")

# ── Leyenda global ────────────────────────────────────────────────────────────
patches = [
    mpatches.Patch(color="#ef4444", label="Accuracy < 0.90"),
    mpatches.Patch(color="#f97316", label="Accuracy 0.90 – 0.97"),
    mpatches.Patch(color="#22c55e", label="Accuracy >= 0.98"),
]
fig.legend(handles=patches, loc="lower center", ncol=3, fontsize=9,
           framealpha=0.9, bbox_to_anchor=(0.5, -0.01), frameon=True,
           edgecolor="#cbd5e1")

fig.suptitle(
    "UnibaBot PDA — Evolucion de Accuracy por Iteracion de Diseno\n"
    "Universidad de Ibague · Agentes Inteligentes · 2025-2026",
    fontsize=14, fontweight="bold", y=1.01, color="#1e293b"
)

plt.tight_layout(rect=[0, 0.06, 1, 1])

png_path = os.path.join(OUT_DIR, "accuracy_journey.png")
svg_path = os.path.join(OUT_DIR, "accuracy_journey.svg")
plt.savefig(png_path, dpi=180, bbox_inches="tight", facecolor="#f8fafc")
plt.savefig(svg_path, format="svg", bbox_inches="tight", facecolor="#f8fafc")
print(f"Guardado: {png_path}")
print(f"Guardado: {svg_path}")
