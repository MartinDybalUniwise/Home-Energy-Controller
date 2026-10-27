// Both inputs are interval means from the same API bucket grid, in watts.
// SDG total__w is the archived house load; load_pt is not substituted for it.
const watts = value => typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;

export function mergeEnergyHistory(goodwe, sdg, bucketSeconds) {
  const bins = new Map();
  const bucketMs = bucketSeconds * 1000;
  if (!Number.isFinite(bucketMs) || bucketMs <= 0) throw new Error('Invalid history bucket');
  for (const [payload, source, fields] of [
    [sdg, 'sdg_history', {pv_w:'ppvcelkem', house_w:'total__w'}],
    [goodwe, 'goodwe', {pv_w:'pv_w', house_w:'house_w'}],
  ]) {
    for (const record of payload?.rows || []) {
      const time = Date.parse(record.timestamp);
      if (!Number.isFinite(time)) continue;
      const stamp = Math.floor(time / bucketMs) * bucketMs;
      const row = bins.get(stamp) || {timestamp:new Date(stamp).toISOString(), pv_w:null, house_w:null, sources:{}};
      for (const [field, original] of Object.entries(fields)) {
        const value = watts(record[original]);
        if (value !== null) {row[field] = value; row.sources[field] = source;}
      }
      bins.set(stamp, row);
    }
  }
  return {bucket_seconds:bucketSeconds, rows:[...bins.entries()].sort((a,b)=>a[0]-b[0]).map(([,row])=>row)};
}
