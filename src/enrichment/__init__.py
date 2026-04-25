"""Enrichment LLM: comentarios prescriptivos y resumenes ejecutivos.

Modulos:
- cache: caches en disco indexado por SHA-256 de inputs.
- summary_writer: una llamada LLM produce {oficina, docente}.
- correction_writer: una llamada LLM por hallazgo NO CUMPLE.

Todos los modulos son ADITIVOS: si fallan, el reporte original
queda intacto. Las decisiones CUMPLE/NO CUMPLE se mantienen
deterministicas (decididas por rules/declaracion_checker.py).
"""
