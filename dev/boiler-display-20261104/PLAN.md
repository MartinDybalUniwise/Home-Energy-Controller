# Boiler/outlet display correction2026-11-04

Plausible low passive candidates were displayed ahead of independently verified
cloud temperatures. The decoder's provisional quality/range flag cannot detect
a high branch alias. Shared source selection now makes boiler, outlet and their
targets cloud-only; stale/missing/error cloud data show unknown instead of wire
candidates. Other fields retain their existing policy, including independent AKU.
Overview and detail share the same selector, with actual per-field sample times.

Validation: browser fixtures reproduce54.4 C boiler /53.1 C outlet against
28.8/27.4 candidates. Check fresh/stale/missing/error cloud, missing fields,
legitimate cold boiler, AKU quality, sample-time provenance, detail/overview
agreement and mobile layout. No sensor offset, decoder or controller changes.
Evidence: C:/TepelneCerpadlo/boiler-ui-20261104/evidence.

Deployment: supported offline incremental backup, retain private config/runtime,
install listed frontend/locale/release/doc files, restart existing service,
verify live cloud/display agreement and independent AKU, rollback on failure.
