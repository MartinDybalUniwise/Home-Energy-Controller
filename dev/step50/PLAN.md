# Prolonged discomfort repair — owner approved 2026-11-16

Evidence: private weekly-2026-11-16-result.md and comfort-root-cause evidence,
specific Nov10/Nov15 cloud samples, command acknowledgements and controller plans.
Prechange incremental backup: c69a5bbc4bc84d168599c0006876771d.

Single controller and existing transports only. No LAN access, extra scheduler,
forced pump setting, GoodWe policy change, heat inventory or compressor inference.
Keep42C water /21.7C ordinary preheat, approved bounded floor service,55C DHW,
explicit off/disabled/master switches and original900s/dual confirmation gates.

1. Persist day-wide coast inhibition after discomfort/recovery activation. Guard
   releases only after30min continuous fresh samples >=21.5C. Missing evidence
   cannot establish recovery. Current thermostat target prevents overheating.
2. Admit new coast only with stable warm room, >=60min acknowledged21.7/42
   preheat and a successful response assessment <=7days old. Keep owned schedules
   and revised_at cutoffs. Failed/short/missing evidence means ordinary heating;
   no new4h model confidence is fabricated. Runtime comfort veto remains active.
3. Diagnose >=60min acknowledged heating with persistent cold/insufficient room
   response; inhibit coast, expose explicit warning on overview and control page,
   retain acknowledgement/activity distinction. Existing two-hour review reports
   alerts here; application has no new direct chat transport or instant delivery.
4. Publish/audit cloud external-pump configuration and source; preserve true/false
   without assuming relay activity or correcting an unverified hardware meaning.
5. Persist missed-DHW/evening-low-probe debt; after stable comfort, outside dated
   owner plans, allow exclusive50C catch-up <=45min, max2/day,>=1h cooldown.
   Restore current heating plan on deadline/comfort/data/permission interruption.
   Wall deadlines survive restart; actual restore delivery still needs live
   service/cloud and existing gates. No usable-water-volume guarantee.

Acceptance: synthetic restart/gap/explicit-off/ack/deadline regressions; isolated
Nov15 and Nov10 replay with no device IO and temp-only state. Replay compares
decisions on the same measured inputs, never claims counterfactual temperatures
or savings. Run relevant regression suite, lint, API and mobile UI checks before
service deployment. Rollback code from the prechange revision/snapshot while
preserving live runtime/confirmation history; never replay elapsed timers.
