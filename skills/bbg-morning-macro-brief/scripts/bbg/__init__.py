"""Bloomberg ASKB ingestion package for bbg-morning-macro-brief.

Exposes:
  - parse.parse_bbg(text)        -> structured dict from delimited markdown
  - ingest.load_bbg(path)        -> parse a pasted ASKB file (or default location)
  - crosscheck.run_crosscheck(...) -> reconcile Bloomberg (primary) vs free sources
"""
