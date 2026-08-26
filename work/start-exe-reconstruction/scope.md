# Case Scope

## meta
- case_id: start-exe-reconstruction
- created: 2026-08-25T21:29:36.7320034+08:00
- operator: local
- project_root: D:\Software\NIRS報告程式_v1.0.17 特殊版(20260401)\nirs_UI_260401\nirs-report-modular
- primary_skill: reverse-engineering/SKILL.md
- primary_id: R0
- lead_role: lead
- specialist_roles: []
- hint: Reverse engineer local Windows start.exe into a modular maintainable GitHub source project without modifying original files
- preset: offline-sample

## auth
- status: granted
- basis: own_system
- evidence_of_auth: preset:offline-sample (owner-operated local file)
- MUST NOT proceed if status != granted

## in_scope
- assets:
  - D:\Software\NIRS報告程式_v1.0.17 特殊版(20260401)\nirs_UI_260401\start.exe
- surfaces: [binary, packaged_python, desktop_ui]
- activities: [reverse, reconstruct, test, report]

## out_of_scope
- assets: []
- activities: [dos, phishing_real_users, unrestricted_exfil]

## network_profile
- mode: offline
- notes: |
    offline | lab_only | authorized_target_only | unrestricted_lab
    Change mode only after auth.status = granted.

## deliverables
- report: true
- field_journal: true
- diagrams: true
- timeline: true

## constraints
- timebox: {}
- stealth: low
- data_handling: anonymize

## signoff
- ready_for_act: true
- checklist:
  - [x] auth.status = granted
  - [x] in_scope.assets non-empty OR offline sample path set
  - [x] network_profile.mode chosen
  - [x] out_of_scope reviewed
  - [x] roles assigned (lead only; no sub-agent delegation requested)

## ops_refs
- skills/ops/scope-contract.md
- skills/ops/evidence-finding-path.md
- skills/ops/role-map.md
- skills/ops/timeline-workitem.md
- skills/ops/IDENTITY.md
