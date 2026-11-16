# EVV1 distribution-aware planning - owner approved 2026-10-31

Use a single price projection in OTE snapshots, thermal planning and validation,
battery planning, forecasts and the existing price API. Preserve raw OTE cache,
EUR/CZK and all market provenance. Reprice cached quarters immediately; never add
distribution twice. No new controller, device writer, timer or UI implementation.

Owner XLS export gives EVV1 every weekday: NT 00-06,07-09,10-13,14-16,17-24;
VT is the complement. Local clocks Europe/Prague. D57d confirmed by owner portal.
Distribution 2026 excluding VAT: NT 0.11650, VT 0.75477 CZK/kWh, replacing
single distribution_czk_kwh when enabled. Existing configured fees and VAT remain.
These are planning prices, not a complete bill: supplier charges remain unverified.
No invented SDG 0.50/1.10 fees. No fixed monthly charges in marginal optimisation.

Price source: https://www.cez.cz/webpublic/file/edee/ceniky/moo_ele_cez_bez_starosti_na_3_roky_01012026_12026.pdf
Distribution section page2, D57d, rows4/5, values in parentheses exclude VAT.
Source validity 2026; stop tariff-based optimisation outside configured date range.
Weekly switching is an exported schedule, not live HDO confirmation; reviews must
check schedule changes in distributor portal. Do not infer physical HDO actuation.

A discrete NT/VT edge needs no 45-minute price-ramp coast: allow preheat until
06:00 and coast from06:00. Preserve existing price margin, <=21.7 preheat cap,
21.5 entry/21.3 abort comfort gates, PV veto and TNG confirmation/900-second guard.
Preserve manual dated overrides. Replan only owned current/future dates; revised_at
prevents attributing missed overnight actions to today. Never reset battery basis.

Prechange incremental snapshot: 30bd2002c15c4795a4f503096e662de9.

Additional preheat candidates must stay entirely in NT when the tariff is enabled.
Normal comfort heating remains available during VT. No forced battery charging.

Validation before activation:189 targeted tests passed (tariff boundaries, cache
repricing, expiry, morning preheat, PV/comfort/TNG guards, battery, controller, API).
Ruff and production Python compilation passed. Real published2026-11-01 dry run
selects04-06 preheat and06-07 coast; additional preheat07-09, coast13-14.
These are conditional plans, not claims of executed heating or savings.
