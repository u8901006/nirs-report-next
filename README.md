# NIRS Report Next

NIRS Report Next 是 Windows 桌面版 fNIRS/NIRS 分析與研究報告工具。它延續
`nirs-report-modular` 的 Excel 載入、ROI、Integral、Centroid 與 Word 報告流程，
並加入通道品質控管、可設定 ROI、側化指標 LI、前後測差異、腦區比較及報告式儀表板。

> 本程式只供研究與報告輔助。fNIRS 是間接的血行動力量測；本程式輸出的 LI、
> 統計結果與圖表不構成疾病診斷、療效判定或手術決策。

## 主要功能

- 載入 NIRSIT Lite 預處理 Excel 與既有 HbO/HbR 工作簿。
- 顯示 Right PFC、Anterior Frontal、Left PFC 與 Lateral Frontal 波形。
- 通道缺失時明確警告，並以剩餘有效通道進行降級分析。
- 計算 Integral、Centroid、Slope 與 Laterality Index（LI）。
- 建立單組/兩組前後測與多 ROI 比較的受試者層級統計結果。
- 產生多通道報告儀表板、Word 報告及 Excel/CSV/JSON 結果。

## 快速開始

需要 Python 3.11 或 3.12。

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\nirs-report.exe
```

也可以使用：

```powershell
.\.venv\Scripts\python -m nirs_report_app
```

## 專案結構

```text
src/nirs_report_app/
├── analysis/          # MBLL、品質、ROI、特徵、LI 與差異分析
├── ui/                # PyQt5 視窗，只處理互動與顯示
├── app.py             # composition root
├── paths.py           # 執行目錄與輸出路徑
├── plugins.py         # 外掛介面與 entry-point 探索
├── reporting.py       # DOCX 報告服務
├── visualization.py   # 報告式圖表
├── dataset.py         # 研究資料集 manifest
├── statistics.py      # 受試者層級統計
├── services.py        # 分析流程編排
└── settings.py        # settings.ini / Report_settings.ini
tests/                 # 不啟動 GUI 的核心回歸測試
docs/                  # 架構與逆向證據報告
```

## 分析原則

數值分析保持為不依賴 Qt 的純函式，再由 `NirsAnalysisService` 編排。推論統計使用
受試者層級資料，不把同一受試者的 frame 當成獨立樣本；缺失 ROI 不會以 0 取代。

```python
from nirs_report_app.analysis.features import positive_integral

value = positive_integral(signal, dt=0.1)
```

## 設定與輸出

程式延續原版檔名：

| 路徑 | 用途 |
|---|---|
| `settings.ini` | 分析時間、Y 軸、濾波與上次目錄（內容為 JSON） |
| `Report_settings.ini` | 報告標題與欄位顯示設定（內容為 JSON） |
| `img/` | 圖像資產與執行期圖表 |
| `report/` | DOCX 報告輸出 |

## 建置 Windows 執行檔

```powershell
.\.venv\Scripts\python -m pip install -e ".[build]"
.\scripts\build.ps1
```

建置後的檔案為 `dist/NIRS-Report-Next.exe`。

## 文件

- [使用指南](docs/user-guide.md)
- [架構與擴充方式](docs/architecture.md)
- [逆向工程報告](docs/2026-08-25_逆向工程-start-exe-report.md)
- [進階分析 SPEC](docs/specs/nirs-report-modular-fNIRS-advanced-analysis-SPEC-v1.md)
- [報告介面 SPEC](docs/specs/nirs-report-modular-output-report-interface-SPEC-v1.md)
- [實作計畫](docs/superpowers/plans/2026-08-26-nirs-report-next.md)

## 授權提醒

本儲存庫公開可見不等同於已授予開源使用權。專案擁有者仍需確認原程式、商標、
圖片、演算法及第三方素材的發布權，並另外選擇 LICENSE。原始執行檔、研究資料、
個案資料與分析輸出不得提交到儲存庫。
