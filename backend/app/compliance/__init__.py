"""Legal compliance — EPIC 11.

Structural readiness for Egyptian ETA e-invoicing without calling the tax
API yet (US-11.1): item codes and an ETA-ready flag per product, on top of
the tax numbers already held on supplier profiles and the `eta_code` on
chart-of-accounts accounts. Plus the hard EGP-only guarantee (US-11.2),
enforced by a `currency = 'EGP'` CHECK on every monetary table.
"""
