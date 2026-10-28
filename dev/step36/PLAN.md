# Step36 — current thermal status

Owner requested room, tank and heating-water temperatures above weather on 2026-10-28.

A three-value panel displays TNG sensor readings and sample time, with available setpoints and heating permission. Heat-pump outlet temperature is explicitly labelled, not presented as direct floor temperature or proof of compressor operation. Missing, implausible and older-than-15-minute measurements are unavailable, never zero.

Actual Edge checks passed at 360, 390 and 1280 pixels: placement, overflow, current values, stale/missing/invalid values and absence of JavaScript errors. No physical controls changed.

Owner approved deployment: exclusive TNG mode windows, bounded DHW, versioned bilingual operational rule registry exposed in service menu, graphical day-plan timeline in energy chart card. Preserve write confirmation and 900-second gate. Validation: 80 relevant offline tests; mobile/desktop browser checks for plan, rules and DOM stability.
