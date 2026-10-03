"""Point of Sale — EPIC 8.

A fast, standalone sell path for branches and agents (US-8.1). It draws from
the SAME inventory as the main platform — a POS sale deducts stock
immediately (single source of truth) — but its accounting is posted in a
periodic BATCH settlement (e.g. end of day), never per-sale (US-8.2).
"""
