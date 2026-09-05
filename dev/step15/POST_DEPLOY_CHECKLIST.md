# Step 15 post-deploy checklist

Retain only redacted command results and timestamps.

- [ ] `systemctl is-active hec.service` reports active.
- [ ] `curl --fail --silent --show-error http://192.168.2.115:8080/` succeeds.
- [ ] The bounded recent journal contains no startup failure.
- [ ] Reader status is healthy through a non-mutating status path.
- [ ] The deployed revision matches the approved SHA.
- [ ] No controller or TNG physical-device write path is enabled.
- [ ] The previous release remains recoverable until verification is complete.