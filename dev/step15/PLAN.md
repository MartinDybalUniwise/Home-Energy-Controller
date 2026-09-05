# Step 15 plan

## Goal

Establish a safe, repo-backed production deployment workflow for Home Energy
Controller on `192.168.2.115`, with explicit validation and rollback gates.

## Work packages

| ID | Work package | Output | Depends on |
|---|---|---|---|
| S01 | Host inventory | verified target, service, paths, ports, user, and access model | None |
| S02 | Safe deployment flow | staged update procedure with validation gates | S01 |
| S03 | Rollback plan | release preservation, restore commands, and recovery path | S02 |
| S04 | Security controls | SSH access, secret handling, permissions, and no Git secrets | S01 |
| S05 | Post-deploy verification | service, HTTP, reader, and log health checks | S02 |
| S06 | Documentation and gatekeeping | repository workflow, evidence rules, and human approvals | S02-S05 |

## Detailed plan

### S01 – Host inventory

- record the target as `192.168.2.115` and confirm it from the operator's
	maintenance context before any connection
- use the repository deployment contract as the initial inventory:
	`hec.service`, `/opt/home-energy-controller`, port `8080`, `data/`,
	`logs/`, `history/`, `.env`, and `dev/hec/config/config.json`
- confirm the production URL is `http://192.168.2.115:8080`
- record the service user, SSH key or approved alternative, maintenance window,
	and named operator; do not record private keys or secret values
- mark every unverified host fact as a pre-deployment blocker rather than
	guessing it

### S02 – Safe deployment flow

- deploy only an approved commit or release from a reviewable branch; do not
	use an unreviewed working tree or an unpinned `git pull` as the release
	decision
- record the current commit, `systemctl is-active hec.service`, and the
	current HTTP health result before changing anything
- create a non-secret release record and back up `.env`, configuration, and
	the release pointer to host-local protected storage; never copy their values
	into logs or repository evidence
- stage or synchronize only application files, excluding `.git/`, `.env`,
	`data/`, `logs/`, and `history/`
- run local/release validation before restart: Ruff, non-e2e tests, ready-step
	validation, and safe preview validation; production host checks are separate
- restart `hec.service` only after the pre-restart gates pass, then run the
	post-deploy checks from S05
- make repeated execution converge on the selected revision without deleting
	runtime data or secrets

### S03 – Rollback plan

- preserve the previous commit or release directory until post-deploy
	verification has passed
- on a failed post-deploy check, stop the service, restore the previous
	application revision and the pre-change configuration backup, then start the
	service and rerun S05
- record the failed revision, rollback revision, timestamps, service state, and
	non-secret failure reason
- if rollback health checks fail, keep the service in the documented safe
	state, stop repeated retries, and escalate to the named operator
- never use rollback as a reason to print or commit `.env`, credentials,
	tokens, production data, or full sensitive logs

### S04 – Security controls

- keep secret values in `.env` or host-local secure storage only
- never commit `.env`, credentials, or tokens to git
- prefer SSH key-based access and limit remote commands to the deployment path
- document a no-root and least-privilege approach where possible
- verify file ownership and permissions for the service user, `.env`, and
	backups before production execution
- do not put private keys, host fingerprints, passwords, or production log
	contents in `TRACEABILITY.md`, `RESULT.md`, or other repository evidence

### S05 – Post-deploy verification

- verify `systemctl is-active hec.service` and inspect a bounded recent journal
	window for startup errors without copying sensitive values
- verify `curl --fail http://192.168.2.115:8080/` or the documented health
	endpoint from an approved maintenance context
- confirm the web interface responds and reader status is healthy through the
	supported non-mutating status path
- confirm no physical-device write path was enabled by the deployment
- store only redacted, non-secret command results and timestamps as evidence

### S06 – Documentation and gatekeeping

- place the final deployment workflow in the repository under `dev/step15/`
- require human approval of the plan before any production execution
- keep local preview and dev validation separate from production deployment actions
- keep `STEP.json` at `PLANNED` and `readiness: NO` until all plan artifacts,
	validation evidence, and required human approvals exist
- do not create `RESULT.md` as a completed result before the workflow is
	actually validated; final evidence belongs in `TRACEABILITY.md` and
	`RESULT.md` only after execution

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| secrets leak into git | use `.env` and host-local secure config only |
| service restart causes downtime | validate before and after restart, roll back quickly |
| wrong host is targeted | document inventory and explicit host identity |
| stale code is deployed | require reviewable source and recorded version evidence |
| local preview is mistaken for production | keep preview safety and no-write invariants explicit |

## Validation commands

Local validation should include the repository workflow and non-destructive checks such as:

```text
python -m ruff check .
python -m pytest -m "not e2e"
python dev/sdd/tools/validate_step.py --phase ready --step dev/step15
python dev/sdd/tools/preview.py start
HEC_RUN_E2E=1 HEC_BASE_URL=http://127.0.0.1:8181 python -m pytest dev/hec/tests/e2e -m e2e
python dev/sdd/tools/preview.py stop
```

The exact shell syntax for environment variables may differ on Windows; use
the repository's configured Playwright task when needed. Any production
deployment action must be executed only after human approval and host-specific
validation. No validation command in this plan writes to TNG or another
physical device.

## Delivery order

1. Complete S01 and resolve all host-inventory blockers.
2. Review S02-S05 with the maintainer and confirm the maintenance access model.
3. Validate the repository workflow and the ready phase for Step15.
4. Execute production deployment only in an approved maintenance window.
5. Record non-secret evidence, complete traceability, and obtain the required
	final human gate before changing the step to `DONE`.
