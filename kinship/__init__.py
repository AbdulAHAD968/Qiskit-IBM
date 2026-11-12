"""Kinship screening with QAOA.

A planning tool for beta-thalassaemia cascade screening: given one home visit
and k test kits, choose which relatives to test so that the expected number of
at-risk couples identified is as large as possible.

All families used by this package are synthetic and seeded.
"""

__version__ = "1.0.0"

CARRIER_RATE = 0.05          # population carrier frequency used for founders
DEFAULT_LAMBDA = 0.05        # weight of the single-carrier term in the objective
