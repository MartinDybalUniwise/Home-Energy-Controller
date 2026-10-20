# Step16 S07 GoodWe Hardware Verification Runbook

> This is a manual runbook only. It does not authorize autonomous writes.
> Do not set the authorization artifact or enable write gates until the human
> operator has reviewed the read-only evidence.

## Preconditions

- Human operator is physically present or has direct operational responsibility
  for GoodWe inverter `192.168.2.116`.
- The inverter is in a safe, stable operating state and no other controller or
  SDG process is changing settings.
- A rollback/reference copy of `dev/hec/config/config.json`, `.env`, and the
  relevant `data/` and `history/` directories exists.
- `controller.enabled=false`, `goodwe.enabled=false`, and
  `goodwe.writer_enabled=false` are the starting state.
- `tng.write_enabled=false` remains unchanged. It is not a GoodWe write gate.
- Do not use a pytest process, preview config, or test fake for hardware work.

All commands below run from the repository root in PowerShell. Replace paths
only with operator-approved local paths. Do not commit the temporary config,
authorization artifact, audit data, or exported device data.

## 1. Read-only communication

Create a temporary configuration copy outside Git and enable only the GoodWe
reader in that copy. Keep both write-related flags disabled:

```powershell
$repo = (Get-Location).Path
$cfg = Join-Path $env:TEMP "hec-step16-s07-readonly.json"
Copy-Item "dev\hec\config\config.json" $cfg -Force
$config = Get-Content $cfg -Raw | ConvertFrom-Json
$config.controller.enabled = $false
$config.tng.write_enabled = $false
$config.goodwe.enabled = $true
$config.goodwe.writer_enabled = $false
$config.goodwe.sdg.enabled = $false
$config | ConvertTo-Json -Depth 20 | Set-Content $cfg -Encoding utf8
```

Start exactly one read-only cycle. The environment variable permits the real
GoodWe read connection; it does not enable a write:

```powershell
$env:HEC_GOODWE_PHYSICAL_IO = "1"
py -3 dev\run.py --config $cfg --once
```

Record the output and confirm:

- source is `goodwe`;
- `online=true`;
- timestamp is current and includes timezone;
- PV, battery, grid and inverter values are plausible;
- model and firmware are reported;
- no write command appears in terminal output;
- no `goodwe_audit` write record was created.

If communication fails, stop. Do not enable any write gate. Record the error,
then restore the environment variable:

```powershell
Remove-Item Env:HEC_GOODWE_PHYSICAL_IO -ErrorAction SilentlyContinue
```

## 2. Gate and diagnostics check

With the same read-only config, inspect status:

```powershell
$env:HEC_GOODWE_PHYSICAL_IO = "1"
py -3 dev\run.py --config $cfg --status
Remove-Item Env:HEC_GOODWE_PHYSICAL_IO -ErrorAction SilentlyContinue
```

Confirm the JSON and `/status` UI show:

- `controller.enabled=false`;
- `goodwe.enabled=true` only for read-only collection;
- `goodwe_writer_diagnostics.enabled=false`;
- `hardware_authorization.status=NOT_AUTHORIZED`;
- no current `last_write`;
- connection, model, firmware and `last_read` diagnostics;
- `tng.write_enabled=false`.

## 3. Prove write refusal before authorization

Do not create an authorization artifact. Keep `writer_enabled=false` and
`controller.enabled=false`. An attempted writer call must fail at the manager
safety boundary before any device write is sent.

This check is preferably performed with a fake/injected client in a local test
process, or by an operator review of the gate state. Do not call a write method
against the real inverter at this stage.

Expected result: `PermissionError` identifying one or more blocked gates,
including `controller.enabled`, `goodwe.writer_enabled`, or
`hardware_authorization`.

## 4. Explicit human S07 authorization

Stop and obtain deliberate human confirmation before creating the local
service evidence. The operator must record at minimum:

- device host: `192.168.2.116`;
- human name/initials;
- date/time and local timezone;
- reason for the verification;
- the read-only output/evidence location;
- the exact candidate parameter for the one reversible write;
- rollback value and expected effect.

Only after that human decision, run the explicit local service authorization
operation. The authorization service writes the local artifact atomically; it
is not a normal Settings/API operation. Use the project-approved service
wrapper or an equivalent directly supervised local service command. Do not
invent an authorization record by editing JSON manually.

Expected artifact: `data/goodwe_hardware_authorization.json` with status
`APPROVED`, host, evidence ID, operator and timestamp.

## 5. HARD STOP before physical write

Do not continue automatically. Show the human operator this exact proposed
write summary and wait for an explicit confirmation:

```text
S07 PHYSICAL WRITE PROPOSAL
Device: 192.168.2.116
Parameter: <exact GoodWe command/setting>
Current value: <read-only value captured in phase 1>
Value to write: <must equal current value for the first write>
Expected impact: no operational change; communication/read-back path only
Command/procedure: <exact supervised command, including config path and flags>
Rollback value: <same captured value>
Audit location: <data/history path for goodwe_audit JSONL>

Confirm physical write? Type: CONFIRM S07 WRITE
```

The first permitted write must use a supported idempotent command and write the
same value currently read from the device. Suitable candidates are an existing
export-limit value or an existing on-grid SOC limit. Do not use charge,
discharge, mode changes, or a new value for the first write.

No write command may be executed until the human has confirmed the exact
parameter, current value, proposed value, expected impact, and command.

## 6. One supervised write and read-back

After explicit confirmation only, run the exact command shown in the proposal
through the HEC `FTEWriter`/`GoodWeManager` path. Do not call the `goodwe`
library setter directly and do not use raw Modbus.

Immediately capture:

- terminal write request and success/failure output;
- returned `command_id`;
- before value;
- write result;
- actual read-back value;
- final status and attempt count.

The operation passes only when read-back exactly equals the proposed value and
the audit record confirms success. On timeout, mismatch, or ambiguous state,
stop and do not issue a second write manually.

## 7. Persistent audit verification

Inspect the JSONL history without changing it:

```powershell
Get-ChildItem -Recurse -Filter "*.jsonl" data,history |
  Select-String -Pattern 'goodwe_audit|command_id|readback|write_result'
```

Confirm the matching audit record contains:

- unique `command_id`;
- timestamp with timezone;
- command and requested parameters;
- `requested_by` and `source`;
- all safety gate states;
- `before` value;
- `write_result`;
- `readback` value;
- attempt/retry count;
- final status and error field.

## 8. Close-down and gates OFF

Immediately after the single supervised write/read-back check:

- set `goodwe.writer_enabled=false`;
- set `goodwe.enabled=false` unless read-only monitoring is intentionally kept;
- set `controller.enabled=false`;
- leave `tng.write_enabled=false`;
- remove `HEC_GOODWE_PHYSICAL_IO` from the environment;
- stop the manual process;
- verify status shows writer disabled and no new write is possible;
- preserve the authorization and audit evidence for review, but do not enable
  another write.

Do not delete or edit the audit record. Do not mark Step16 DONE.

## 9. Evidence to record in Step16

After the human test, update `RESULT.md` and `TRACEABILITY.md` with actual
operator evidence only:

- read-only communication result and timestamp;
- gate refusal result before authorization;
- authorization evidence ID and operator;
- the exact approved parameter/current value/proposed value;
- write/read-back result and `command_id`;
- audit record path and validation result;
- confirmation that all write gates were returned to OFF;
- any limitation or failure.

S07 remains incomplete if any of these records is missing, if the read-back does
not match, if a gate could not be returned to OFF, or if a physical write was
performed without the explicit confirmation text above.
