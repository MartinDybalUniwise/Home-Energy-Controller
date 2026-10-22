# Requirements

## Objective

Correct the reported mobile alignment, missing graphical energy flows and accidental route changes while dragging content. Preserve factual telemetry and every physical control setting.

- REQ-031-001: Responsive Today/Flow cards align without clipped text, accidental full-page horizontal overflow or overlapping content, including long Czech unavailable-state text and enlarged text.
- REQ-031-002: Mobile Flow displays an actual diagram connecting FVE, battery, house and grid, with readable values and direction arrows based on valid measured signed flows. Missing/invalid/near-zero measurements must not invent active flows. Appliance status remains readable and truthful.
- REQ-031-003: Disable document-wide swipe route navigation. Horizontal movement within cards, charts and scrolling strips never changes the page; explicit menu navigation and vertical page scrolling remain usable.
- REQ-031-004: Verify on real Chromium at 360/390/430 and desktop 1280 CSS px, with 200% text zoom, long Czech/English labels, missing measurements and real touch drags. Review and owner Human Gate precede a separate production deployment.
