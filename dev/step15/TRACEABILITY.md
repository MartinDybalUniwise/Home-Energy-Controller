# Step 15 traceability

Step15 remains in planning. The status below records the intended evidence and
must not be changed to `PASS` until the corresponding artifact exists and has
been reviewed.

## Requirement mapping

| Requirement ID | Acceptance IDs | Plan step | Evidence type | Status |
|---|---|---|---|---|
| REQ-015-001 | AC-015-001, AC-015-007 | S01 | E-015-001: host inventory and ready validation | OPEN |
| REQ-015-002 | AC-015-002, AC-015-005 | S02, S05 | E-015-002: staged update record and validation output | OPEN |
| REQ-015-003 | AC-015-003, AC-015-005 | S03, S05 | E-015-003: rollback rehearsal or approved recovery evidence | OPEN |
| REQ-015-004 | AC-015-004, AC-015-006 | S04, S06 | E-015-004: safety and secret-handling review | OPEN |

## Acceptance mapping

| Acceptance ID | Requirement link | Test or evidence | Status |
|---|---|---|---|
| AC-015-001 | REQ-015-001 | S01 inventory review | OPEN |
| AC-015-002 | REQ-015-002 | S02 pre-restart gate review | OPEN |
| AC-015-003 | REQ-015-003 | S03 rollback procedure and recovery check | OPEN |
| AC-015-004 | REQ-015-004 | S04 secret-handling review | OPEN |
| AC-015-005 | REQ-015-002, REQ-015-003 | S05 post-deploy and post-rollback checks | OPEN |
| AC-015-006 | REQ-015-004 | S06 preview safety validation | OPEN |
| AC-015-007 | REQ-015-001 | ready-phase structural and README validation | OPEN |

## Plan mapping

| Step ID | Purpose | Dependencies | Status |
|---|---|---|---|
| S01 | Verify production host inventory and access model | none | OPEN |
| S02 | Define and review the controlled update flow | S01 | OPEN |
| S03 | Define and review release rollback and recovery | S02 | OPEN |
| S04 | Define security, permissions, and secret controls | S01 | OPEN |
| S05 | Define service, HTTP, reader, and log verification | S02 | OPEN |
| S06 | Complete repository documentation and gatekeeping | S02-S05 | OPEN |

## Evidence rules

- Evidence must be non-secret and must not contain credentials, private keys,
  production data, or unredacted sensitive logs.
- Local preview artifacts remain under ignored runtime storage.
- Production execution evidence requires explicit human approval and must not
  be represented by local preview output.
- The step cannot move to `DONE` while any mandatory row remains `OPEN`.