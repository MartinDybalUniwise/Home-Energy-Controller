# Step 15 security checklist

- [ ] Use the approved SSH key and least-privilege operator account.
- [ ] Use `sudo` only for required service operations.
- [ ] Keep `.env` and credential stores on the host only.
- [ ] Exclude `.env`, credentials, tokens, runtime data, and logs from Git,
  synchronization, diagnostics, and evidence.
- [ ] Verify ownership and permissions for the service directory, `.env`, and
  backups before restart.
- [ ] Keep `controller.enabled=false` and `tng.write_enabled=false` in local
  and preview validation.
- [ ] Confirm no physical-device write path is enabled by deployment checks.