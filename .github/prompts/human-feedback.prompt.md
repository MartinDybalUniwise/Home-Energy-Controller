# HEC human feedback prompt

Classify the feedback as **SMALL** or **LARGE** before editing.

For SMALL feedback (text, layout, validation, contained bug): implement the
minimum, run relevant tests and Playwright for UI, and update result evidence.

For LARGE feedback (new module/data flow, API/storage contract, controller or
write behavior, security, architecture, or major UI): stop; update the
requirement, plan, acceptance criteria, and add new `Sxx` steps. Wait for
human approval before implementation.

Never infer a human PASS from automated checks.
