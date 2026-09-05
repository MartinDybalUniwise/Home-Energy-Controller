# Step 15 rollback checklist

Use this checklist only after a failed post-deploy check and within an
approved recovery window.

- [ ] Record failed SHA, timestamp, service state, and a redacted reason.
- [ ] Stop `hec.service` and prevent repeated restart attempts.
- [ ] Restore the preserved previous release or approved previous SHA.
- [ ] Restore host-local configuration without displaying `.env` values.
- [ ] Verify ownership and permissions, then start `hec.service`.
- [ ] Repeat the post-deploy checks in `DEPLOYMENT_RUNBOOK.md`.
- [ ] Escalate and leave the service in the documented safe state if checks
  still fail.

Rollback evidence must not contain secrets, production data, private keys, or
unredacted logs.