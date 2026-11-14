"""Continuous national policy collection for the Yance policy evidence base.

The package is split so that the security-sensitive network and extraction
layer (:mod:`urlguard`, :mod:`robots`, :mod:`fetch`, :mod:`extract`,
:mod:`classify`, :mod:`fingerprint`, :mod:`catalog`) is pure Python and can be
tested without a database, while the persistence layer (:mod:`pipeline`,
:mod:`scheduler`, :mod:`report`) reuses the existing Policy / PolicyVersion /
PolicyChunk evidence model.
"""

COLLECTOR_VERSION = "policy-collector-v3"
