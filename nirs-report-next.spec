# -*- mode: python ; coding: utf-8 -*-
# ruff: noqa: F821
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)


version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(2, 0, 0, 0),
        prodvers=(2, 0, 0, 0),
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", "nirs-report-next contributors"),
                        StringStruct("FileDescription", "NIRS Report Next"),
                        StringStruct("FileVersion", "2.0.0"),
                        StringStruct("InternalName", "NIRS-Report-Next"),
                        StringStruct("OriginalFilename", "NIRS-Report-Next.exe"),
                        StringStruct("ProductName", "NIRS Report Next"),
                        StringStruct("ProductVersion", "2.0.0"),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)

hiddenimports = collect_submodules("nirs_report_app") + [
    "statsmodels.formula.api",
    "statsmodels.regression.mixed_linear_model",
    "statsmodels.stats.multitest",
]

analysis = Analysis(
    ["launcher.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="NIRS-Report-Next",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=version_info,
)
