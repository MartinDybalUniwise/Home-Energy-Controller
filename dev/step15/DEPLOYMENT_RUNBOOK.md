# Step 15 deployment runbook

This runbook is the operational output of S01-S06. It is a production
procedure, not permission to execute a deployment. Production execution
requires the human approvals recorded in `STEP.json` and a confirmed
maintenance window.

## S01 - Host inventory

| Item | Repository baseline | Required confirmation |
|---|---|---|
| Host | `192.168.2.115` | Confirm host identity before connecting |
| URL | `http://192.168.2.115:8080` | Confirm from the maintenance network |
| Service | `hec.service` | Confirm with `systemctl status hec.service` |
| Install root | `/opt/home-energy-controller` | Confirm on the host |
| Runtime data | `data/`, `logs/`, `history/` | Confirm paths and ownership |
| Runtime config | `.env`, `dev/hec/config/config.json` | Confirm paths and permissions; never copy values |
| Service user | Not verified in repository | Record the account name, not credentials |
| SSH access | Key-based access preferred | Record operator and key identifier, never the private key |

Do not continue when the host, service, install root, or service user differs
from the approved inventory. A mismatch is a deployment blocker.

## S02 - Controlled update

1. Confirm the approved commit SHA and maintenance window with the operator.
2. Connect through the approved SSH account and verify the host identity.
3. Record only non-secret pre-change facts:
   `git rev-parse HEAD`, `systemctl is-active hec.service`, and an HTTP status
   from `http://192.168.2.115:8080/`.
4. Create a host-local backup of `.env`, `dev/hec/config/config.json`, and the
   current release pointer. Protect the backup with the service operator's
   filesystem permissions. Do not print the files.
5. Preserve `data/`, `logs/`, and `history/`. Synchronize the approved code
   while excluding `.git/`, `.env`, `data/`, `logs/`, and `history/`.
6. Validate the approved revision before restart using the repository's Ruff,
   non-e2e pytest, ready validation, and safe preview checks.
7. Abort without restarting if any validation or safety check fails.
8. Restart `hec.service` only after all gates pass. Record the new commit SHA
   and restart timestamp without recording secrets or full logs.
9. Run S05. Keep the previous release recoverable until S05 passes.

The update must be repeatable: selecting the same approved SHA again must not
replace runtime data, regenerate secrets, or change host-local credentials.

## S03 - Rollback and recovery

Start rollback when the service does not become active, the HTTP check fails,
reader status is unhealthy, or a safety invariant is violated.

1. Record the failed SHA, timestamp, service state, and a redacted failure
   reason.
2. Stop `hec.service` and prevent repeated restart attempts while recovering.
3. Restore the previous application release or checkout the preserved previous
   SHA. Do not use an unreviewed working tree.
4. Restore the host-local configuration backup without displaying its contents.
5. Verify ownership and permissions, then start `hec.service`.
6. Run the S05 checks again and record only non-secret results.
7. If recovery fails, leave the service in the documented safe state, stop
   repeated retries, and escalate to the named operator.

Never commit or copy `.env`, credentials, tokens, production data, private
keys, or unredacted logs as rollback evidence.

## S04 - Security controls

- Use an approved SSH key and least-privilege account; use `sudo` only for the
  service operations that require it.
- Keep `.env` and any credential store on the host. Exclude them from Git,
  synchronization, logs, diagnostics, and evidence.
- Check ownership and permissions for the service directory, `.env`, and backup
  directory before restarting the service.
- Do not put host fingerprints, private key paths that reveal sensitive
  infrastructure, passwords, or secret values in repository documents.
- Keep `controller.enabled=false` and `tng.write_enabled=false` in local and
  preview validation. Never use a production deployment check to enable a
  physical-device write path.

## S05 - Post-deploy verification

Run these checks from the approved maintenance context and retain only
redacted results:

```text
systemctl is-active hec.service
curl --fail --silent --show-error http://192.168.2.115:8080/
systemctl --no-pager --lines=100 status hec.service
journalctl --unit hec.service --since "5 minutes ago" --no-pager
```

Confirm all of the following:

- the service is active;
- the HTTP interface responds successfully;
- the bounded journal contains no startup failure;
- reader status is healthy through a non-mutating status path;
- the deployed revision matches the approved SHA;
- no controller or TNG physical-device write path was enabled.

## S06 - Evidence and gates

Evidence IDs are defined in `TRACEABILITY.md`. Evidence must contain command
names, timestamps, status, revision identifiers, and redacted outcomes only.
Runtime output and browser artifacts belong under ignored runtime directories,
not in the repository.

Before production execution:

- Gate A must be `APPROVED`.
- S01 host inventory must be confirmed by the named operator.
- The approved revision and maintenance window must be recorded.
- Local Ruff, non-e2e tests, ready validation, and safe preview checks must
  pass.
- Local preview must remain separate from production access.

After execution, complete the evidence and human gates before changing the
manifest to `DONE`. Until then, `STEP.json` remains `PLANNED` or
`IN_PROGRESS`, with `readiness` and evidence kept truthful.