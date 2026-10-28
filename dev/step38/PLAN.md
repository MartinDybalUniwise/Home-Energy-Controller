# Step38 — passive TNG evidence and live panel

Owner approved implementation, deployment, Git PR/merge and twice-daily analysis
on 2026-10-28. Preserve cloud control, confirmation cycle and 900 s guard.

- Independent, receive-only TZSP reader; no connections to the LAN controller.
- Persist both original bodies, versioned provisional decoding and paired replies.
- Track cloud commands and confirmation phases separately from physical effects.
- Main panel mirrors device layout with adjacent planned/sent/reported command state.
- Stale passive data cannot replace cloud data; AKU never falls back to outlet.
- Raw traces rotate daily, retain 30 days and cap at 50 MB/day by default.
- No captured payloads, device identities or private config in Git.
- Validate synthetic packet fragmentation/retransmission, pairs, sensor branches,
  cloud gates, reader isolation and responsive UI before release.
- Analysis at 08:00/20:00 Europe/Prague reads bounded evidence and reports findings;
  uncertain decoder/control fields never silently become control inputs.
