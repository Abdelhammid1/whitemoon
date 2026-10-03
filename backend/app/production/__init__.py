"""Production — EPIC 7 (basic manufacturing orders).

A deliberately minimal scope: a manufacturing order turns raw-material
products into a finished product through a predefined sequence of stages
(US-7.1). Completing the order deducts the materials and adds the finished
good to stock, and posts the linked inventory/accounting journal
automatically (US-7.2). No cost layer or resource scheduling in this version
— the relations are built so those can be added later without a rebuild.
"""
