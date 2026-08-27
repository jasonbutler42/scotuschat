"""
Corpus import helper package (Phase 29: Historical Corpus Import).

Pure-Python helpers with no DB dependency, consumed by the ConvoKit bulk
importer:
    - loader: streaming/full-load readers for the ConvoKit source files.
    - stage_directions: curated-vocabulary stage-direction detection.
    - apolitical: the sole sanctioned allowlist translation layer from raw
      corpus dicts into ORM-bound fields (D-12/D-23 hard constraint).
"""
