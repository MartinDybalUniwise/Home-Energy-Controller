# Step43 — do not miss local morning price rises

Owner reported recurring heating onset during the morning price rise on2026-10-31.
Standing authority covers the fix and deployment. No UI development.

## Evidence and cause

- Today's published morning maximum7.9408 CZK/kWh was below the old daily-median-plus1
  threshold8.09885. The plan included only evening preheat/coast; no overnight preheat.
- Room drifted from21.6 C at00–03h to21.4 C in05h and21.3–21.4 C in06h. GoodWe
  house demand rose from roughly0.35–0.4 kW overnight to about3 kW in the morning.
  House demand is not a complete independent HP power meter; do not invent isolated HP
  energy, COP, heat inventory or compressor-start proof from it.
- The comfort guard was not the cause of the missing price plan. Leaving42 C/room21.5
  all night allowed device regulation to choose a later start, without advance preparation.

## Decisions

- Compare local rises with the previous six hours. Freeze the entry baseline within a
  peak; end it at a material price valley so morning and evening do not merge.
- Retain at least45 minutes of a meaningful peak, a gap>=0.60 CZK/kWh AND>=8% against
  the selected preheat. Near-flat curves do not create extra heating cycles.
- Retain two-hour preheat, at most42 C water and21.7 C room target. Among candidates
  within0.10 CZK/kWh of the cheapest qualifying window, prefer the latest. This prevents
  a tiny price advantage from moving preparation unnecessarily early.
- Coast across the whole shorter peak plus up to45 minutes of its rising edge, bounded
  by three hours. For longer peaks select the most expensive three hours. Preserve
  room>=21.5 C entry and the latched21.3 C comfort veto; never force a cold house to wait.
- Keep exclusive/bounded DHW, real FTE checks, all confirmation/900 s gates and master
  control semantics unchanged. No LAN probing, Boost, battery or inverter actuation.
- Keep dated-plan ownership version for migration; add a policy identifier to the input
  hash so already-generated plans are actually refreshed. A revised_at cutoff avoids
  rewriting missed overnight preheat into today's saved schedule. Tomorrow uses its
  own published prices when available, never today's curve copied forward.
- Handle24:00 boundaries in TNG scheduling/logging and resolve the supplied date rather
  than wall-clock date, preventing a midnight window from stopping the reader thread.

## Validation and delivery

- Prechange incremental backup57dee502f589430a9df9e6a057698d21; first PID verification
  attempt was refused by Windows. Retry with the current PID after full process exit passed.
- Compare old/new algorithm offline on the actual31 October published curve; store that
  comparison only in external monitoring evidence, explicitly as a counterfactual.
- Test modest morning peaks with a dearer evening, separate valleys, later cheap preheat,
  flat curves, manual dates, correction cutoff, data validity, midnight boundaries,
  solar/comfort interlocks, one controller and persistent device gates.
- Commit tested code, capture a clean incremental snapshot with the service stopped,
  set revised_at and refresh only owned current/future plans, restart the existing service.
- Do not reset confirmation state or force a compressor start. Validate saved windows,
  effective phase, reader health and preservation of DHW/inverter configuration after start.
