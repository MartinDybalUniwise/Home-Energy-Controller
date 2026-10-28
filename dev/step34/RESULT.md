# Step34 result

Deployed HEC 0.1.7 on 2026-10-27; first final production verification 20:12 Europe/Prague. Owner explicitly authorized implementation and deployment.

GoodWe interval means take precedence per field, including zero. SDG ppvcelkem and total__w fill missing PV and household-power buckets. Origins appear in the table and inspection tooltip. A single-source API failure preserves the other source and is reported; failed partial responses are retryable. Raw history and device configuration are unchanged.

Validation: 25 relevant Edge browser regressions PASS, including CZ/EN, mobile/desktop, DST, gaps, zero/negative values, SDG morning fallback and unavailable-source handling. Additional actual-data preview and actual production Edge checks PASS. Production table has 339 rows with midnight SDG data and evening GoodWe data, with no JavaScript errors. All six readers are fresh and healthy under the Windows service. Private configuration hashes match preflight.

Pre-deployment incremental snapshot and operator evidence are outside the repository in C:/TepelneCerpadlo/step34-evidence. Deployment first rolled back safely after missing Git identity; a subsequent interrupted maintenance window was completed from its verified backup. Local commit identity was scoped to Codex for this commit; no global Git settings or remote branches were modified.
