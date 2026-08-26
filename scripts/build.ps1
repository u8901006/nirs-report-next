param(
    [string] $Python = ".\.venv\Scripts\python.exe",
    [switch] $SkipVerification
)

$ErrorActionPreference = "Stop"
& $Python -m pip install -e ".[dev,build]"
if (-not $SkipVerification) {
    & $Python -m pytest -q
    & $Python -m ruff check .
    & $Python -m build
}
& $Python -m PyInstaller --clean --noconfirm "nirs-report-next.spec"
$Smoke = Start-Process `
    -FilePath "dist/NIRS-Report-Next.exe" `
    -ArgumentList "--smoke-test" `
    -Wait `
    -PassThru `
    -WindowStyle Hidden
if ($Smoke.ExitCode -ne 0) {
    throw "Executable smoke test failed with exit code $($Smoke.ExitCode)"
}
