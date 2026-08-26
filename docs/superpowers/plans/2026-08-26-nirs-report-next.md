# NIRS Report Next Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new Windows desktop application named `nirs-report-next` that preserves the existing NIRS Excel analysis flow and adds channel-quality handling, configurable ROIs, LI, pre/post and regional statistics, a report-style dashboard, DOCX/data exports, and a packaged executable.

**Architecture:** Start from the tested modular `nirs-report-modular` baseline and keep numerical analysis independent from PyQt5. Add immutable result models in focused analysis modules, orchestrate them through services, render all charts from a shared report view model, and make GUI/Word outputs consume the same values. Publish the verified result as a separate public GitHub repository without modifying the source repository.

**Tech Stack:** Python 3.11/3.12, NumPy, pandas, SciPy, statsmodels, Matplotlib, openpyxl, python-docx, PyQt5, pytest, Ruff, PyInstaller.

**Spec:** `../specs/nirs-report-modular-fNIRS-advanced-analysis-SPEC-v1.md` and `../specs/nirs-report-modular-output-report-interface-SPEC-v1.md`

## Global Constraints

- Preserve the existing single-workbook Integral/Centroid workflow and modern/legacy Excel loaders.
- Never replace missing or invalid ROI data with a zero waveform or numeric zero.
- Statistical inference uses subject-level observations, never raw time frames as independent samples.
- HbO and HbR remain separate analysis endpoints.
- The default montage is Right PFC ch1–ch4, Anterior Frontal ch5–ch11, Left PFC ch12–ch15, and derived Lateral Frontal.
- GUI and DOCX reports consume the same structured result values.
- Python support remains `>=3.11,<3.13`; Windows 10/11 is the executable target.
- All new numerical behavior follows strict red-green-refactor TDD.
- The new GitHub repository is public and named exactly `nirs-report-next`.

---

### Task 1: Establish the New Repository Baseline

**Files:**
- Create: repository root copied from the `nirs-report-modular` baseline
- Create: `docs/specs/nirs-report-modular-fNIRS-advanced-analysis-SPEC-v1.md`
- Create: `docs/specs/nirs-report-modular-output-report-interface-SPEC-v1.md`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Test: existing `tests/`

**Interfaces:**
- Consumes: baseline commit `48d695ddf8c249a9c800878e8f3e6e2f43e0989f`.
- Produces: an isolated local Git repository whose package remains importable as `nirs_report_app`, with distribution name `nirs-report-next` and version `2.0.0`.

- [x] **Step 1: Copy the clean baseline without its `.git` directory**

Use PowerShell `Copy-Item` from the verified temporary clone into `nirs-report-next`, preserving the already-created `docs/superpowers/plans` directory and excluding `.git`.

- [x] **Step 2: Initialize the new repository and copy both approved specs**

Run `git init -b main`, copy the two Markdown specs into `docs/specs/`, and verify the original repository remote is not configured as a push target.

- [x] **Step 3: Run the baseline tests before changing behavior**

Run:

```powershell
python -m pytest -q
```

Expected: all inherited baseline tests pass.

- [x] **Step 4: Update project identity and dependencies**

Set:

```toml
[project]
name = "nirs-report-next"
version = "2.0.0"
dependencies = [
  "matplotlib>=3.7,<4",
  "numpy>=1.24,<3",
  "openpyxl>=3.1,<4",
  "pandas>=1.5,<3",
  "Pillow>=9,<13",
  "PyQt5>=5.15,<6",
  "python-docx>=0.8.11,<2",
  "scipy>=1.10,<2",
  "statsmodels>=0.14,<1",
]
```

Keep the console entry point `nirs-report = "nirs_report_app.app:main"` for compatibility.

- [x] **Step 5: Update README product identity and safety statement**

Document the three new analysis modes, report dashboard, Windows build steps, public-repository purpose, and research-only/non-diagnostic limitation.

- [x] **Step 6: Re-run inherited tests and commit**

Run `python -m pytest -q`, then commit with `chore: establish nirs-report-next baseline`.

### Task 2: Channel Quality, ROI Definitions, and Metrics

**Files:**
- Create: `src/nirs_report_app/analysis/models.py`
- Create: `src/nirs_report_app/analysis/quality.py`
- Create: `src/nirs_report_app/analysis/metrics.py`
- Modify: `src/nirs_report_app/analysis/regions.py`
- Modify: `src/nirs_report_app/analysis/features.py`
- Test: `tests/test_quality.py`
- Test: `tests/test_metrics.py`
- Modify: `tests/test_features.py`

**Interfaces:**
- Produces: `ChannelState`, `QualityStatus`, `ChannelAssessment`, `RoiDefinition`, `RoiSignal`, `MetricSummary`, `assess_channel()`, `aggregate_roi()`, `baseline_corrected_mean()`, and `recovery_slope()`.
- Consumes: pandas channel frames and NumPy time series from the existing loader.

- [x] **Step 1: Write failing channel-quality tests**

Add literal fixtures proving:

```python
def test_missing_channel_is_reported_without_zero_waveform():
    result = aggregate_roi(frame, RoiDefinition("right_pfc", "Right PFC", (1, 2)))
    assert result.valid_channels == (1,)
    assert result.missing_channels == (2,)
    assert result.status is QualityStatus.DEGRADED
    np.testing.assert_allclose(result.values, [1.0, 2.0, 3.0])

def test_roi_without_valid_channels_is_invalid_and_nan():
    result = aggregate_roi(empty_frame, RoiDefinition("right_pfc", "Right PFC", (1, 2)))
    assert result.status is QualityStatus.INVALID
    assert np.isnan(result.values).all()
```

- [x] **Step 2: Run quality tests and verify RED**

Run `python -m pytest tests/test_quality.py -q`.
Expected: import failure for the missing quality API.

- [x] **Step 3: Implement immutable quality and ROI models**

Create enums/dataclasses and row-wise ROI aggregation. A time point with less than 50% valid selected channels becomes `NaN`; an empty ROI returns an all-NaN array and `E_ROI_EMPTY`, never zeros.

- [x] **Step 4: Run quality tests and verify GREEN**

Run `python -m pytest tests/test_quality.py -q` and then the full suite.

- [x] **Step 5: Write failing metric tests**

Use hand-derived expectations:

```python
def test_baseline_corrected_mean_subtracts_windows():
    values = np.array([1.0, 1.0, 3.0, 5.0])
    assert baseline_corrected_mean(values, slice(0, 2), slice(2, 4)) == 3.0

def test_recovery_slope_uses_seconds():
    assert recovery_slope(np.array([3.0, 2.0, 1.0]), np.array([0.0, 0.5, 1.0])) == -2.0
```

- [x] **Step 6: Run metric tests and verify RED**

Run `python -m pytest tests/test_metrics.py -q`.

- [x] **Step 7: Implement metrics and split built-in ROIs**

Implement metric functions and change `compute_region_signals` to expose Right PFC, Anterior Frontal, Left PFC, and derived Lateral Frontal while preserving `front_hbo`, `front_hbr`, `side_hbo`, and `side_hbr` compatibility properties.

- [x] **Step 8: Run metric, feature, and full tests; commit**

Commit with `feat: add channel quality and configurable ROI metrics`.

### Task 3: Laterality Index Analysis

**Files:**
- Create: `src/nirs_report_app/analysis/laterality.py`
- Create: `tests/test_laterality.py`
- Modify: `src/nirs_report_app/analysis/__init__.py`

**Interfaces:**
- Produces: `LateralityResult`, `LateralityDirection`, `calculate_li(left, right, threshold=0.10)`, and `bootstrap_li(left_blocks, right_blocks, repetitions=5000, seed=20260826)`.
- Consumes: finite left/right ROI metrics produced by Task 2.

- [ ] **Step 1: Write failing LI point-estimate tests**

```python
@pytest.mark.parametrize(("left", "right", "expected"), [(3, 1, 0.5), (1, 3, -0.5), (2, 2, 0.0)])
def test_li_uses_left_minus_right_ratio(left, right, expected):
    assert calculate_li(left, right).value == expected

def test_li_rejects_near_zero_denominator():
    result = calculate_li(1.0, -1.0)
    assert result.value is None
    assert "W_LI_DENOMINATOR_SMALL" in result.warnings

def test_li_with_opposite_signs_has_no_direction_classification():
    result = calculate_li(2.0, -0.5)
    assert result.direction is None
    assert "W_LI_OPPOSITE_SIGNS" in result.warnings
```

- [ ] **Step 2: Verify RED, implement the minimal LI function, verify GREEN**

Run the single test module before and after implementation.

- [ ] **Step 3: Write failing deterministic bootstrap tests**

Assert that the same seed returns identical CI bounds and that resampling paired blocks preserves equal sample length.

- [ ] **Step 4: Implement paired block/subject bootstrap**

Resample indices, compute the mean left/right metrics for each replicate, discard only invalid denominators, and return percentile 2.5/97.5 bounds plus valid replicate count.

- [ ] **Step 5: Run full tests and commit**

Commit with `feat: add robust laterality index analysis`.

### Task 4: Research Dataset and Statistical Inference

**Files:**
- Create: `src/nirs_report_app/dataset.py`
- Create: `src/nirs_report_app/statistics.py`
- Create: `src/nirs_report_app/analysis/prepost.py`
- Create: `src/nirs_report_app/analysis/regional.py`
- Create: `tests/test_dataset.py`
- Create: `tests/test_statistics.py`
- Create: `tests/test_prepost.py`
- Create: `tests/test_regional.py`

**Interfaces:**
- Produces: `StudyRecord`, `load_manifest()`, `validate_manifest()`, `pair_pre_post()`, `paired_test()`, `welch_test()`, `one_sample_test()`, `adjust_pvalues()`, `fit_mixed_model()`, `PrePostResult`, and `RegionalComparisonResult`.
- Consumes: subject-level ROI metric rows; never raw frames.

- [ ] **Step 1: Write failing manifest-validation tests**

Test required columns, duplicate `(subject_id, session, condition)` keys, relative paths, and readable-file validation with literal temporary manifests.

- [ ] **Step 2: Verify RED, implement manifest models/validation, verify GREEN**

Keep row numbers and actionable error messages in validation results.

- [ ] **Step 3: Write failing pairing tests**

Prove that complete subjects produce `post - pre`, incomplete subjects appear in exclusions, and no missing value is filled with zero.

- [ ] **Step 4: Verify RED, implement pairing, verify GREEN**

The returned object contains paired rows, total subjects, paired N, and exclusions.

- [ ] **Step 5: Write failing statistical tests**

Use small hand-calculated fixtures for paired difference, one-sample LI, Holm correction, and Benjamini–Hochberg correction. Assert estimates, sample sizes, and adjusted p-value ordering rather than implementation details.

- [ ] **Step 6: Verify RED, implement SciPy tests/effect sizes/corrections, verify GREEN**

Return a common `StatisticalResult` with estimate, standard error, CI, statistic, p-value, adjusted p-value, effect size, included/excluded N, method, warnings, and provenance.

- [ ] **Step 7: Write failing mixed-model behavior tests**

Create a deterministic repeated-measures fixture where the intervention group increases only at post; assert a positive `group:time` coefficient, subject count, and converged status.

- [ ] **Step 8: Verify RED, implement statsmodels MixedLM wrapper, verify GREEN**

Do not silently switch models. Return `W_MODEL_CONVERGENCE` with no interpretation when fitting fails.

- [ ] **Step 9: Implement and test regional contrasts**

Build all requested ROI pairs, apply one correction family, retain every contrast, and reject comparisons that treat `lateral_frontal` as independent of its left/right components.

- [ ] **Step 10: Run the full suite and commit**

Commit with `feat: add study dataset and inferential statistics`.

### Task 5: Service Orchestration and Structured Report Model

**Files:**
- Modify: `src/nirs_report_app/services.py`
- Create: `src/nirs_report_app/report_models.py`
- Create: `tests/test_services.py`
- Create: `tests/test_report_models.py`

**Interfaces:**
- Produces: `SingleAnalysisRequest`, `StudyAnalysisRequest`, `StudyAnalysisResult`, `ReportViewModel`, `NirsAnalysisService.analyze_single()`, and `NirsAnalysisService.analyze_study()`.
- Consumes: loader, quality, metrics, laterality, pre/post, regional, and statistics modules.

- [ ] **Step 1: Write a failing single-analysis service test**

Use a real temporary workbook with one missing PFC channel. Assert Right/Anterior/Left/Lateral ROI summaries, degraded status, LI values, and compatibility feature output.

- [ ] **Step 2: Verify RED, implement single orchestration, verify GREEN**

The existing `analyze()` method delegates to `analyze_single()` and preserves its public result contract.

- [ ] **Step 3: Write a failing multi-file study service test**

Use four small workbooks (two subjects × pre/post), a manifest, and literal expected paired deltas. Assert subject-level rows and exclusion/warning propagation.

- [ ] **Step 4: Verify RED, implement study orchestration, verify GREEN**

Do not import PyQt5 in services or analysis modules.

- [ ] **Step 5: Write and implement ReportViewModel validation tests**

Reject mismatched metric/plot coordinates and accept absent optional analysis pages. Commit with `feat: orchestrate advanced analyses through report models`.

### Task 6: Dashboard Visualizations and Data Exports

**Files:**
- Create: `src/nirs_report_app/visualization.py`
- Create: `src/nirs_report_app/exporting.py`
- Create: `tests/test_visualization.py`
- Create: `tests/test_exporting.py`

**Interfaces:**
- Produces: `ReportDashboardRenderer`, `render_overview()`, `render_laterality()`, `render_prepost()`, `render_regional()`, and `export_result_bundle()`.
- Consumes: `ReportViewModel`; produces Matplotlib figures/PNG and XLSX/CSV/JSON files.

- [ ] **Step 1: Write failing overview-renderer tests**

Render a fixed 15-channel view model and assert observable figure contracts: three region headers, 15 channel axes, two ROI cards, one plot-map axis, and marker coordinates matching the model.

- [ ] **Step 2: Verify RED, implement the A4 landscape overview, verify GREEN**

Use HbO `#D6455D`, HbR `#148FBD`, fixed montage positions, shared axes by default, and explicit missing-channel panels.

- [ ] **Step 3: Write failing advanced-page renderer tests**

Assert that LI, pre/post, and regional renderers label their primary estimate and include required warning text when results are invalid.

- [ ] **Step 4: Verify RED, implement advanced renderers, verify GREEN**

All renderers accept explicit dimensions/DPI and do not recompute statistics.

- [ ] **Step 5: Write failing export-bundle tests**

Assert exact output names, numeric columns remaining numeric/NA, config seed preservation, SHA-256 provenance, and 300-DPI PNG dimensions.

- [ ] **Step 6: Verify RED, implement XLSX/CSV/JSON/PNG bundle export, verify GREEN**

Write to a temporary sibling directory and rename only after all outputs succeed.

- [ ] **Step 7: Run full tests and commit**

Commit with `feat: render report dashboard and export analysis data`.

### Task 7: DOCX Reporting

**Files:**
- Modify: `src/nirs_report_app/reporting.py`
- Create: `tests/test_advanced_reporting.py`

**Interfaces:**
- Produces: `build_advanced_report(destination, settings, patient, view_model, rendered_pages)`.
- Consumes: validated report model and 300-DPI dashboard images.

- [ ] **Step 1: Write a failing DOCX structure test**

Open the generated DOCX with `python-docx` and assert native report title, patient table, quality/warning text, required research-only statement, overview image, and method/provenance table.

- [ ] **Step 2: Verify RED, implement hybrid DOCX report, verify GREEN**

Use native Word text/tables for selectable content and inserted PNGs for chart layout. Optional LI/pre/post/regional sections appear only when corresponding results exist.

- [ ] **Step 3: Write a failing consistency test**

Assert that displayed Integral/Centroid/Slope/LI values match the same `ReportViewModel` used by CSV export.

- [ ] **Step 4: Implement consistency formatting and verify GREEN**

Use blank/NA for numeric missing values and Traditional Chinese `無法計算` only in narrative cells.

- [ ] **Step 5: Run reporting and full suites; commit**

Commit with `feat: add advanced Word research reports`.

### Task 8: PyQt5 Workflow and Report Preview

**Files:**
- Modify: `src/nirs_report_app/ui/main_window.py`
- Create: `src/nirs_report_app/ui/channel_grid.py`
- Create: `src/nirs_report_app/ui/result_tabs.py`
- Create: `src/nirs_report_app/ui/report_preview.py`
- Create: `src/nirs_report_app/ui/workers.py`
- Create: `tests/test_ui_smoke.py`

**Interfaces:**
- Produces: data/settings/results/report-preview workflow, channel selection, five result tabs, background study worker, and export actions.
- Consumes: service and renderer APIs only; UI does not perform numerical calculations.

- [ ] **Step 1: Write a failing offscreen UI smoke test**

With `QT_QPA_PLATFORM=offscreen`, instantiate `MainWindow` and assert the five named result tabs, analysis-mode selector, channel-grid status, and disabled export before analysis.

- [ ] **Step 2: Verify RED, implement the navigation shell, verify GREEN**

Keep controls usable at 1280×800 and do not remove inherited file/time settings.

- [ ] **Step 3: Write failing channel-grid interaction tests**

Assert that missing channels retain montage positions, selected channels update ROI counts, and an invalid LI pair disables LI execution.

- [ ] **Step 4: Verify RED, implement channel-grid/status interactions, verify GREEN**

Use text/icons plus colors for every state.

- [ ] **Step 5: Write failing report-preview tests**

Assert optional pages, mandatory quality/method pages, zoom range 60%–200%, and selected-page export state.

- [ ] **Step 6: Verify RED, implement result tabs and report preview, verify GREEN**

Use renderer outputs; do not recalculate result values in widgets.

- [ ] **Step 7: Write and implement worker cancellation tests**

Verify batch analysis signals progress, can be cancelled between files, and does not leave a partial destination report.

- [ ] **Step 8: Run offscreen UI and full suites; commit**

Commit with `feat: add advanced analysis and report preview UI`.

### Task 9: Packaging, Documentation, and Release Verification

**Files:**
- Modify: `scripts/build.ps1`
- Create: `nirs-report-next.spec`
- Modify: `README.md`
- Create: `docs/user-guide.md`
- Modify: `.github/workflows/ci.yml`
- Test: full test suite, Ruff, wheel/build smoke, PyInstaller artifact smoke.

**Interfaces:**
- Produces: reproducible Windows executable build and documented user workflow.
- Consumes: all completed application modules.

- [ ] **Step 1: Add PyInstaller specification**

Bundle PyQt5, Matplotlib data, Word dependencies, version metadata, and application assets. Output name is `NIRS-Report-Next.exe`.

- [ ] **Step 2: Update CI and documentation**

CI runs Python 3.11 and 3.12 tests plus Ruff. The user guide covers single/study modes, manifest columns, channel warnings, LI/pre-post/regional interpretation, report export, and non-diagnostic limitation.

- [ ] **Step 3: Run complete verification**

Run:

```powershell
python -m pytest -q
python -m ruff check .
python -m build
python -m PyInstaller --clean nirs-report-next.spec
```

Expected: zero test failures, zero Ruff errors, wheel/sdist created, and `dist/NIRS-Report-Next.exe` exists.

- [ ] **Step 4: Run executable smoke test**

Launch the EXE with a dedicated `--smoke-test` option that initializes paths and core imports without opening an interactive window, then exits 0.

- [ ] **Step 5: Commit the release candidate**

Commit with `release: prepare nirs-report-next 2.0.0`.

### Task 10: Create and Publish the Public GitHub Repository

**Files:**
- No production file changes unless final verification finds an issue, in which case return to the relevant TDD task.

**Interfaces:**
- Produces: `https://github.com/u8901006/nirs-report-next` with `main` branch.
- Consumes: verified local Git repository.

- [ ] **Step 1: Verify repository cleanliness and identity**

Run full tests again, `git status --short`, `git remote -v`, and scan tracked files for secrets, source patient data, `.venv`, build outputs, and temporary HEIC/PNG conversions.

- [ ] **Step 2: Confirm target repository availability**

Use authenticated GitHub CLI/API to confirm `u8901006/nirs-report-next` does not already exist. If it exists, stop before overwriting or changing its visibility.

- [ ] **Step 3: Create the public repository**

Run:

```powershell
gh repo create u8901006/nirs-report-next --public --source . --remote origin --push
```

- [ ] **Step 4: Verify the remote repository**

Confirm repository visibility is `PUBLIC`, default branch is `main`, remote HEAD matches the local release commit, README renders, and both SPEC files are present.

- [ ] **Step 5: Record final release information**

Report the public URL, commit SHA, test count, build artifact path, and any explicitly deferred items.
