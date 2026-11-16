# AKU display range2026-11-04

Owner requested removal of the photo-reference range cutoff from AKU display.
Fresh finite buffer readings now remain visible outside that interval, in both
the overview and heat-pump detail. Missing values say “Current reading unavailable”.
Existing cloud boiler/outlet display policy and controller conditions are preserved.
Regression coverage includes43.2 C, below-reference29.7 C and stale AKU data.
