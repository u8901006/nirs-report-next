---
title: NIRS Report Next 使用指南
description: 單次量測、研究資料集、側化指標、前後測、腦區比較與報告匯出操作說明
date: 2026-08-26
tags: [fNIRS, NIRS, LI, pre-post, research-report]
---

# NIRS Report Next 使用指南

## 1. 使用限制

本程式只供研究與教育用途。fNIRS 是間接血行動力指標，可能受到動作、頭皮血流、
呼吸、心跳與其他全身性訊號影響。輸出的 LI、p 值、效果量、圖表與 Word 報告不得
單獨用於疾病診斷、療效判定、手術規劃或其他臨床決策。

處理個案資料前，請依所在機構的研究倫理、去識別化、資料保存及存取權限規定操作。

## 2. 單次量測

1. 在「分析模式」選擇「單次量測」。
2. 選擇 NIRSIT Lite 預處理後的 Excel，或相容的 HbO/HbR 工作簿。
3. 設定 baseline、作業開始、作業結束與測量結束時間。
4. 在固定通道配置圖選擇納入通道；缺失或無效通道會留在原位置並顯示原因。
5. 執行分析後，依序查看「總覽」、「側化 LI」及「報告預覽」。

通道不足時，ROI 可能標示為「降級」，程式會用剩餘有效通道計算並保存有效 X/Y
通道數。ROI 完全無法計算時顯示空白或「無法計算」，不會用 0 代替缺失值。

## 3. 研究資料集 manifest

研究模式接受 CSV 或 Excel manifest。必要欄位如下：

| 欄位 | 說明 |
|---|---|
| `subject_id` | 去識別化受試者編號 |
| `file_path` | 原始工作簿路徑；相對路徑以 manifest 所在資料夾為基準 |
| `session` | 建議使用 `pre`、`post` |

選用欄位包括 `group`、`condition`、`measurement_date`、`baseline_start`、
`baseline_end`、`task_start`、`task_end`、`measure_end`。每筆
`subject_id + session + condition` 必須唯一；缺檔、重複鍵與不完整配對都會保留警告
或排除紀錄。

## 4. 結果判讀

### 側化指標 LI

`LI = (L − R) / (L + R)`。正值偏左、負值偏右，介於設定切點內視為雙側。當分母過小、
左右數值異號或資料非有限值時，程式會拒絕分類並顯示警告。LI 是指定 ROI、時間窗、
chromophore 與指標下的摘要，不等同穩定的人格或診斷特徵。

### 前後測

推論以受試者為單位，只有完整 pre/post 配對才進入配對分析。報告同時列出納入 N、
排除 N、差值、信賴區間、效果量與方法。兩組研究應優先解讀 `group × time`，不要只比較
一組顯著、另一組不顯著。

### 腦區差異

腦區比較保存全部 contrasts 與多重比較校正後 p 值。`Lateral Frontal` 是左右 PFC 的
衍生平均，不能和其左右組成區當作互相獨立的 ROI 放入同一比較模型。

## 5. 報告與資料匯出

「產生 Word 報告」會建立原生文字與表格，圖表則以同一渲染器輸出 300 dpi PNG 後插入。
「匯出資料包」建立新資料夾，包含：

- `subject_level_results.xlsx`
- `statistical_results.csv`
- `exclusions_and_warnings.csv`
- `analysis_config.json`
- `figures/*.png`

圖片固定為 A4 橫式 `3508 × 2480 px`。JSON 保存分析設定、警告、隨機種子與來源檔
SHA-256，方便重現分析。CSV/Excel 的數值缺失維持空白/NA，不會混入 `missing` 字串。

## 6. 報告預覽

預覽縮放範圍為 60%–200%。LI、前後測、腦區差異只在有結果時加入；「品質控管」與
「方法與聲明」為必要頁面，不能取消。匯出前請確認有效通道數、時間窗、警告、排除清單
及主要分析方法。

## 7. Windows 執行與建置

一般使用者執行 `NIRS-Report-Next.exe`。開發者可在 PowerShell 執行：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev,build]"
.\scripts\build.ps1
```

建置腳本會先執行測試、程式檢查與 Python 套件建置，再產生
`dist/NIRS-Report-Next.exe`，最後使用 `--smoke-test` 驗證執行檔能初始化核心元件。
