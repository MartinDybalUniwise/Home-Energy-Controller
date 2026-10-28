# Step37 — show absolute diagnostic heat-pump power

Owner requested correction and immediate deployment on 2026-10-28.
The reader already converts -1253.94 W to +1253.94 W and preserves raw fields.
The overview hid this value because L2 reports zero voltage and non-zero current.

Show the normalised absolute reading in the overview, explicitly marked partial
while the phase fault persists. Keep analytic power invalid, retain warning
styling, exclude stale/offline/missing/uncorrected data, and leave energy/COP/
control semantics, physical devices and historical records unchanged.

Verify helper semantics and real DOM display in a safe browser preview, then use
the supported incremental backup, deploy, verify production, push and merge after
required CI passes. Existing owner authorisation covers these actions.
