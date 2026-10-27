# Step34: SDG history in the overview

Owner request: implement SDG fallback and deploy immediately (2026-10-27).

The overview requests matching time buckets from GoodWe and SDG. Valid GoodWe wins per field, including zero. SDG ppvcelkem and total__w fill missing PV and house-load values. Raw histories, physical controls and private configuration remain unchanged. Table and tooltip identify the source; partial API failure preserves the other source.

Acceptance: the actual October 27 morning appears; duplicate buckets are not summed; invalid/negative/missing values are not fabricated; mobile/desktop and source failure are covered.
