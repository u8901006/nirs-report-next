param(
    [string] $Python = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
& $Python -m pip install -e ".[build]"
& $Python -m PyInstaller `
    --clean `
    --noconfirm `
    --name "nirs-report" `
    --windowed `
    --onefile `
    "launcher.py"
