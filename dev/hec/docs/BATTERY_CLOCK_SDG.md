# Battery clock and single-writer repair

Owner request: configure SDG to leave battery actuation to HEC and resolve the
clock discrepancy. SMALL change covered by standing owner authorization.

The battery resolver compared the decision time with an inverter clock captured
in an earlier sample. A valid 110-second clock difference plus a fresh 60-second
sample age crossed the 120-second clock limit and stopped owned charging.
Compare the inverter clock with that sample's timestamp instead. Preserve the
independent -30..90-second telemetry freshness gate, the absolute 120-second
clock limit, and the writer's fresh native clock verification before activation.
Expose the observed skew and clock validity in the existing battery-plan status.

Validation covers both clock directions, inclusive 120-second boundaries,
121-second rejection, a running owned schedule with aged fresh feedback,
stale telemetry, economic/comfort coordination and existing GoodWe writer tests.
No charge/safety limits, thermal logic or physical writers are added.

Operational work stays outside Git: back up affected SDG configuration, select
the app's existing battery Manual mode and retain acquisition, persist its
existing variable default, verify other project streams are unchanged. During
the stopped HEC maintenance window, synchronize only the inverter clock using
the existing SDK time setting and verify native readback. Do not send a test
charge or change inverter work mode. Preserve configuration and runtime state.

Deployment: passing targeted tests and CI, review the diff, merge the PR, stop
the existing service, capture the supported incremental release backup, deploy
only changed tracked runtime files and start the same service. Verify version,
root, fresh readings, native mode/program and clock diagnostics. Physical charge
continuity remains to be observed in the next legitimate economic window.

Rollback: restore the changed runtime files from the release snapshot and
restart the existing service. Restore the exact private SDG project backup only
if its configuration change needs reversal; do not restore telemetry/history.
