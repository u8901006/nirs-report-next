# Case handoff

## Findings

### F-001
- title: Target is an unencrypted Python 3.11 PyInstaller application
- severity: n/a_re
- category: reverse_algo
- status: validated
- evidence_ids: [E-001, E-003, E-004]
- location: start.exe CArchive / start.pyc
- impact: High-level Python modules can be reconstructed from bytecode and metadata.
- confidence: high
- repro_steps:
  1. Verify E-001 sample hash.
  2. Run the E-003 archive information command.
- remediation: n/a

### F-002
- title: Application responsibilities were coupled in a single controller
- severity: n/a_re
- category: design
- status: candidate
- evidence_ids: [E-004]
- location: controller.pyc:MainWindow_controller
- impact: UI, analysis, plots, and reports were difficult to test or extend independently.
- confidence: medium
- repro_steps:
  1. Run the E-004 code-object inspection.
  2. Review the MainWindow_controller method tree.
- remediation: Split loader, analysis, service, reporting, UI, and plugin boundaries.

## Paths

### P-001
- title: Packaged executable to modular source project
- path_type: solve
- start: start.exe
- goal: Testable and extensible Python repository
- steps:
  1. action: Fix sample identity and PE metadata — evidence: E-001 — finding: F-001
  2. action: Classify native bootloader imports — evidence: E-002 — finding: F-001
  3. action: Extract the PyInstaller CArchive and PYZ — evidence: E-003 — finding: F-001
  4. action: Recover owned Python code objects — evidence: E-004 — finding: F-002
- residual_risks: Clinical and layout equivalence require de-identified golden-master inputs.
