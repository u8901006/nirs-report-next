---
title: "nirs-report-modular：fNIRS 側化、前後測與腦區差異分析功能規格"
description: "定義側化指標 LI、NIRS/fNIRS 前後測差異、腦區活化差異、資料品質警告、統計推論、圖表與 Word 報告的產品及技術需求。"
date: 2026-08-26
status: draft-for-review
version: "1.0"
target_repository: "https://github.com/u8901006/nirs-report-modular"
target_commit: "48d695ddf8c249a9c800878e8f3e6e2f43e0989f"
keywords: [fNIRS, NIRS, laterality index, pre-post, ROI, statistics, PyQt5]
tags: [SPEC, fNIRS, desktop-app, statistics, reporting]
---

# nirs-report-modular：fNIRS 側化、前後測與腦區差異分析功能規格

## 1. 文件目的

本文件定義 `nirs-report-modular` 下一階段的三項分析能力：

1. 以 fNIRS 評估大腦側化，計算側化指標（Laterality Index, LI）及其統計推論。
2. 評估 NIRS/fNIRS 前後測差異，支援單組、控制組及多時間點設計。
3. 比較不同腦區的活化差異，支援預先定義 ROI、使用者自訂 ROI 與多重比較校正。

本規格只描述需求、介面、計算規則與驗收條件。本階段不修改既有程式、不建立實作分支，也不變更 GitHub 儲存庫。

## 2. 現況與設計前提

### 2.1 既有系統基線

本規格以 GitHub `main` 分支提交 `48d695d`、套件版本 `1.0.17` 為基線。現有程式為 Python 3.11/3.12、PyQt5 桌面應用，採模組化資料流：

```text
PyQt5 UI → NirsAnalysisService → Excel loader → MBLL → ROI → filter
         → integral/centroid → UI / DOCX report
```

目前已具備：

- 載入 `Filtered ΔHb`、`Padded ΔHb` 或舊版 `HbO`/`HbR` 工作表。
- 15 通道預設映射：右前額 `ch1–ch4`、前額中區 `ch5–ch11`、左前額 `ch12–ch15`。
- ROI 平均、mean filter、正值積分、累積面積重心與 DOCX 報告。
- UI 與分析純函式分離，適合擴充新的統計分析模組。

### 2.2 核心設計決策

- 保留「單一量測」模式，提供單一 Excel 的波形、Integral、Centroid、左右 ROI 與描述性 LI。
- 新增「研究資料集」模式；統計推論的獨立樣本單位是受試者，而不是 frame 或時間點。
- 三項新功能共用同一份資料集、ROI、品質控管、分析指標與報告模型，避免各自重複載入與計算。
- HbO 為預設主要指標；HbR 可切換為主要指標或作敏感度分析。HbO 與 HbR 的結果不得混合成同一個 LI。
- 預設採 baseline-corrected block average；既有正值積分可作 LI 或差異分析的替代來源，但報告必須標示所選指標。
- 軟體只提供研究與報告輔助，不輸出疾病診斷、療效判定或手術決策文字。

## 3. 範圍

### 3.1 本版納入

- 單檔描述分析及多檔研究資料集。
- 通道勾選、ROI 編輯、左右同源 ROI 配對與設定檔保存。
- 缺失通道偵測、降級分析警告、排除原因與有效通道數揭露。
- LI 點估計、分類、信賴區間及組內/組間推論。
- 單組前後測、兩組前後測、多時間點 LMM。
- 同一受試者的多 ROI 差異與 ROI × time / ROI × group 交互作用。
- 效果量、95% 信賴區間、多重比較校正、模型診斷摘要。
- 時程圖、LI 圖、paired-line plot、forest plot、ROI heatmap。
- Word 研究報告及機器可讀結果匯出。

### 3.2 本版不納入

- 從原始光強度自動執行完整 motion correction、short-separation regression 或生理訊號回歸；若輸入檔未完成這些處理，報告需揭露限制。
- 3D MNI/腦表面定位、NIRS-SPM 或 AtlasViewer 整合。
- 事件標記自動辨識、完整 HRF basis GLM、功能連結或腦網路分析。
- 與 fMRI、Wada test 的自動一致性分析。
- 雲端上傳、多人協作或病歷系統串接。

## 4. 使用者與主要情境

### 4.1 使用者角色

- 臨床或研究操作員：匯入資料、設定通道與時間窗、執行分析、匯出報告。
- 研究者/統計分析者：建立配對資料、選擇模型、檢查效果量、信賴區間與多重比較結果。
- 審閱者：從 Word 報告確認資料來源、參數、缺失通道、樣本數與計算方法。

### 4.2 主要流程

1. 使用者選擇「單一量測」或「研究資料集」。
2. 匯入 Excel；研究資料集模式可多選檔案或匯入 manifest。
3. 確認受試者、session/time、group、condition 與檔案配對。
4. 選擇 chromophore、分析時間窗、指標、通道與 ROI。
5. 系統執行資料品質檢查，呈現可分析、降級或無效狀態。
6. 使用者選擇 LI、前後測或腦區差異分析。
7. 系統顯示估計值、95% CI、效果量、校正後 p/q 值、圖表與警告。
8. 使用者匯出 Word、結果 Excel/CSV 與分析設定 JSON。

## 5. 共用資料模型

### 5.1 研究資料集 manifest

研究資料集必須支援以 UI 表格編輯，並可由 UTF-8 CSV/XLSX 匯入。每列代表一位受試者的一次量測：

| 欄位 | 必填 | 規則 |
|---|---:|---|
| `subject_id` | 是 | 非空字串；在同一研究中代表同一人 |
| `file_path` | 是 | 指向可讀取的 NIRS Excel |
| `session` | 是 | 預設允許 `pre`、`post`；也可使用 `t0`、`t1`、`t2` 等 |
| `group` | 否 | 單組預設 `all`；兩組以上不可空白 |
| `condition` | 否 | 預設 `task`；用於同一 session 多任務 |
| `measurement_date` | 否 | ISO `YYYY-MM-DD` |
| `task_start` | 否 | 未填時使用專案預設值 |
| `task_end` | 否 | 未填時使用專案預設值 |
| `baseline_start` | 否 | 未填時使用專案預設值 |
| `baseline_end` | 否 | 未填時使用專案預設值 |
| `measure_end` | 否 | 未填時使用專案預設值 |

唯一鍵為 `(subject_id, session, condition)`。重複鍵必須阻止分析並指出衝突列。檔案路徑可相對於 manifest 所在資料夾解析；匯出時保存原始路徑與正規化後路徑。

### 5.2 受試者層級分析表

每個檔案完成單次量測分析後，產生一列或多列標準化結果：

```text
subject_id, group, session, condition, roi, chromophore,
metric_name, metric_value, valid_channel_count, expected_channel_count,
quality_status, warning_codes, source_file, source_file_sha256
```

推論統計只能使用此受試者層級表，不得把原始 frame 當作受試者層級樣本。

### 5.3 ROI 定義

內建 montage：

| ROI ID | 顯示名稱 | 預設通道 | 半球 |
|---|---|---|---|
| `right_pfc` | Right Prefrontal Lobe | `ch1–ch4` | right |
| `anterior_frontal` | Anterior Frontal Lobe | `ch5–ch11` | midline |
| `left_pfc` | Left Prefrontal Lobe | `ch12–ch15` | left |
| `lateral_frontal` | Lateral Frontal Lobe | `right_pfc + left_pfc` | bilateral |

使用者可建立、重新命名及保存 ROI，並指定任意現存通道。LI 分析必須指定一個 left ROI 與一個 right ROI；兩者通道不得重疊。所有結果需保存 ROI 名稱、通道清單及設定版本。

## 6. 共用品質控管與缺失資料規則

### 6.1 通道狀態

每個預期通道分類為：

- `valid`：欄位存在，分析窗內有足夠有限數值。
- `partial`：欄位存在，但部分數值缺失；可依逐時間點有效覆蓋率使用。
- `missing`：欄位不存在。
- `invalid`：全為缺失/無限值、長度不一致或無法轉為數值。
- `excluded_by_user`：使用者主動取消選取。

逐時間點 ROI 平均使用有效通道的等權重 `nanmean`。某時間點的有效通道比例低於 50% 時，該 ROI 時間點為缺失，不以 0 取代。

### 6.2 ROI 品質狀態

- `complete`：所有選取通道有效。
- `degraded`：至少一個選取通道可用，但有 missing、invalid 或 partial 通道；使用剩餘通道分析。
- `invalid`：沒有任何有效通道，或有效資料不足以覆蓋指定分析窗。

系統預設允許 `degraded` 繼續分析，並在畫面及報告顯示「使用 X/Y 通道」。`invalid` ROI 不得回傳 0，必須回傳缺失值與錯誤碼。若 LI 左右任一 ROI 無效，LI 即無效；若 pre/post 任一配對量測缺失，該受試者不進入 complete-case 配對分析，但保留在排除清單。

### 6.3 必要警告碼

| 代碼 | 說明 |
|---|---|
| `W_CHANNEL_MISSING` | 預期通道不存在 |
| `W_CHANNEL_PARTIAL` | 通道含部分缺值 |
| `W_ROI_DEGRADED` | ROI 以剩餘通道計算 |
| `E_ROI_EMPTY` | ROI 無有效通道 |
| `E_WINDOW_OUT_OF_RANGE` | 分析時間窗超出資料範圍 |
| `E_PAIR_INCOMPLETE` | 受試者缺少必要的 pre/post 配對 |
| `W_LI_DENOMINATOR_SMALL` | LI 分母接近 0，結果不穩定 |
| `W_LI_OPPOSITE_SIGNS` | L 與 R 方向相反，比例型 LI 解讀受限 |
| `W_MODEL_CONVERGENCE` | 統計模型未收斂或出現奇異配適 |
| `W_MULTIPLICITY_UNCORRECTED` | 使用者選擇未校正的探索性結果 |

## 7. 分析指標

### 7.1 可選來源指標

每個 ROI、chromophore、session 可選：

1. `baseline_corrected_mean`（預設）

   ```text
   response = mean(task window) - mean(baseline window)
   ```

2. `positive_integral`（相容既有程式）

   ```text
   integral = trapezoid(max(signal_in_task_window, 0), dt)
   ```

3. `signed_integral`

   ```text
   integral = trapezoid(signal_in_task_window, dt)
   ```

4. `centroid_time`（描述用途，不作預設推論端點）

5. `glm_beta`：只有輸入檔已提供 beta，或未來 GLM 模組產生 beta 時才可選；本版不從原始時間序列估計完整 GLM。

同一項分析的 L/R、pre/post、各 ROI 必須使用相同 chromophore、指標、baseline/task window、濾波與通道品質規則。

### 7.2 效果量與區間

- 所有主要推論同時報告原始尺度估計值、95% CI、樣本數及 p 值。
- 配對差異報 `Cohen's dz`；非參數配對檢定報 rank-biserial correlation。
- 兩獨立組報 Hedges' g；ANOVA/LMM 報模型係數及可計算的標準化效果量。
- 置信區間與 bootstrap 必須保存隨機種子；預設 `seed=20260826`。
- 不以「p < .05」單獨判定臨床有意義。

## 8. 功能一：側化指標 LI

### 8.1 計算

對同一量測、相同指標的左右同源 ROI：

```text
LI = (L - R) / (L + R)
```

- LI > 0 表示左向側化；LI < 0 表示右向側化。
- 預設顯示範圍為 `[-1, 1]`，但若 L/R 含負值，數學結果可能超出此範圍；此時不裁切，並顯示警告。
- 分母保護值為 `max(1e-12, 1e-6 × (|L| + |R|))`。若 `|L + R|` 小於或等於保護值，LI 回傳缺失並標示 `W_LI_DENOMINATOR_SMALL`。
- 若 L、R 異號，仍輸出 LI 點估計，但標示 `W_LI_OPPOSITE_SIGNS`，且不自動給出左/右/雙側分類。
- 分類切點預設 `τ=0.10`：`LI > τ` 為 left-dominant、`LI < -τ` 為 right-dominant、其餘為 bilateral。切點可設定，但報告必須列出切點；分類只作描述，不作診斷。
- 報告必須同時列出 L、R、LI、有效通道數、來源指標與時間窗，避免只呈現比例。

### 8.2 LI 不確定性

- 有重複 block 時：以 block 為重抽樣單位，計算 5,000 次 paired bootstrap 的 LI 95% percentile CI。
- 群組分析時：以受試者為重抽樣單位，計算群組平均/中位 LI 的 5,000 次 bootstrap CI。
- 不得以相鄰 frame 作 bootstrap 獨立單位。
- 單一量測且沒有 block 級資料時，只報 LI 點估計，不製造 CI。

### 8.3 LI 統計推論

| 問題 | 預設分析 | 替代分析 |
|---|---|---|
| 單組是否側化 | one-sample t-test，H0: mean LI = 0 | Wilcoxon signed-rank，H0: median LI = 0 |
| 同一組 LI 前後是否改變 | paired t-test | Wilcoxon signed-rank |
| 兩獨立組 LI 是否不同 | Welch t-test | Mann–Whitney U |
| 多時間點/含組別 | random-intercept LMM：`LI ~ time * group + (1 | subject)` | 無自動替代；模型失敗時回報診斷 |

常態性檢查只作診斷顯示，不得依 p 值自動切換統計方法。使用者需在分析前選定主要方法。

### 8.4 LI 圖表

- 左右 ROI 平均時程圖：L、R 疊圖，標示 baseline/task window 與 95% CI（群組模式）。
- 個人 LI strip/violin plot：顯示 0 線與 ±τ 分類線。
- pre/post LI paired-line plot。
- 群組 LI forest plot：估計值、95% CI、樣本數。

## 9. 功能二：NIRS/fNIRS 前後測差異

### 9.1 配對與差值

同一 `subject_id + condition + roi + chromophore + metric_name` 的 session 依研究設定配對。兩次量測定義：

```text
delta_i = metric_i,post - metric_i,pre
```

兩組差異中之差異：

```text
DiD = mean(delta_intervention) - mean(delta_control)
```

不得直接比較跨 session 的原始光強度；必須比較每個 session 內先完成 baseline 校正後的反應或相同定義的特徵。

### 9.2 統計模型

| 研究設計 | 主要模型 |
|---|---|
| 單組 pre/post 各一次 | paired t-test；可預先改選 Wilcoxon |
| 兩組 pre/post 各一次 | LMM：`metric ~ group * time + (1 | subject)`，主要檢定 `group:time` |
| 隨機試驗且需調整 baseline | ANCOVA：`post ~ group + baseline + prespecified_covariates` |
| 三個以上時間點/不等間隔/部分遺漏 | LMM：`metric ~ time * group + (1 + time | subject)`；資料不足支撐 random slope 時改為 random intercept，並記錄原因 |

規則：

- 「介入組顯著、控制組不顯著」不得被報告為兩組變化不同；兩組差異以 `group × time` 為主。
- 配對分析採 complete-case，並列出原始受試者數、完成配對數及各排除原因。
- LMM 可使用符合模型假設的部分遺漏資料，但不得補 0；報告需列各時間點樣本數。
- 可加入的共變量必須在執行前由使用者指定並保存在分析設定中。
- 模型需輸出係數、SE、95% CI、p 值、收斂狀態、殘差 QQ 圖及殘差對擬合值圖。

### 9.3 前後測圖表

- 個人 pre/post paired lines，保留每位受試者方向。
- 群組平均與 95% CI，不以單純 mean ± SEM 長條圖作唯一圖表。
- delta forest plot，按 ROI 顯示原始差、標準化效果量與 CI。
- 多時間點 spaghetti plot 與模型估計趨勢線。

## 10. 功能三：腦區活化差異

### 10.1 分析單位

腦區差異比較以同一受試者、同一 session、同一 condition、同一 chromophore 與同一 metric 的 ROI 結果為輸入。不得直接比較使用不同時間窗或不同前處理設定的 ROI。

### 10.2 分析方法

| 問題 | 主要模型 |
|---|---|
| 同一 session 兩個 ROI | paired t-test；可預先改選 Wilcoxon |
| 同一 session 三個以上 ROI | repeated-measures model：`metric ~ region + (1 | subject)` |
| ROI 的前後變化是否不同 | LMM：`metric ~ region * time + (1 | subject)`，主要檢定 `region:time` |
| 組別、時間與 ROI | LMM：`metric ~ region * time * group + (1 | subject)` |

整體 region 或交互作用顯著後，才執行預先指定的 pairwise contrasts。所有成對比較必須顯示未校正 p 值與校正後值。

### 10.3 多重比較

- 預設校正 family 為同一分析中所有 ROI pairwise contrasts。
- 預設使用 Holm correction；探索性多通道分析可選 Benjamini–Hochberg FDR。
- 使用者可選「不校正」供探索，但畫面與報告必須顯示 `W_MULTIPLICITY_UNCORRECTED`。
- 同一份報告不得只列顯著 ROI；所有納入 family 的比較都要輸出。

### 10.4 腦區圖表

- ROI × session/group heatmap，以共同色階顯示平均反應。
- ROI forest plot，顯示估計差、95% CI 與校正後 p/q 值。
- 三個內建 ROI 的群組時程圖：Anterior Frontal、Left PFC、Right PFC；Lateral Frontal 作衍生 ROI，避免與其組成 ROI 同時進入同一個獨立區域比較模型。

## 11. UI/UX 規格

### 11.1 主導覽

主視窗採四個步驟頁籤，並在左側顯示完成狀態：

1. `資料`：單檔/研究資料集、manifest、配對與檔案檢查。
2. `通道與分析設定`：montage、ROI、chromophore、指標、時間窗、濾波。
3. `結果`：單次指標、LI、前後測、腦區差異及診斷。
4. `報告`：選擇圖表、預覽警告、匯出 Word 與資料表。

### 11.2 通道/ROI 編輯器

- 15 個通道以左右對稱的頭部示意排列，顏色區分 Right PFC、Anterior Frontal、Left PFC。
- 點擊通道可勾選/取消；缺失或無效通道以斜線/灰色顯示，不能偽裝成 0。
- ROI 卡片即時顯示 `有效/預期` 通道數及 `complete/degraded/invalid`。
- LI 設定區分別選 left/right ROI，若通道重疊或任一 ROI 無效，停用「執行 LI」。
- 所有圖表色彩需兼顧色盲辨識，除顏色外同時使用線型、點型與文字標籤。

### 11.3 統計設定防呆

- 使用者先選研究設計，介面才呈現相容模型。
- 選擇兩組 pre/post 時，主結果固定突出 `group × time`，簡單效果放在次要區。
- 顯示實際進入模型的 N、排除 N、各組/時間點 N。
- 未完成配對、樣本不足、零變異、模型未收斂時不顯示誤導性的 p 值。
- 每項分析提供「方法說明」展開區，顯示公式、假設與限制。

## 12. Word 與資料匯出

### 12.1 Word 報告結構

1. 報告標題、個案/研究資訊、產生時間、軟體版本。
2. 資料摘要：檔案數、受試者數、group/session/condition 分布。
3. 分析設定：ROI、通道、chromophore、指標、baseline/task window、濾波、分類切點、統計模型、校正法。
4. 品質控管：每檔 missing/invalid/partial 通道、降級 ROI、排除受試者與警告碼。
5. 單次量測：波形、Integral、Centroid、L/R 原始值。
6. LI：點估計、CI、分類、群組推論及圖表。
7. 前後測：描述統計、delta/DiD、模型係數、效果量、CI、p 值及圖表。
8. 腦區差異：整體檢定、全部 contrasts、校正後結果及圖表。
9. 限制與聲明：fNIRS 為間接血行動力指標；未處理的 motion/systemic confounds；不得作單獨臨床診斷。
10. 分析追溯資訊：來源檔 SHA-256、設定 JSON SHA-256、隨機種子。

### 12.2 伴隨輸出

每次匯出建立同名資料夾，包含：

- `report.docx`
- `subject_level_results.xlsx`
- `statistical_results.csv`
- `exclusions_and_warnings.csv`
- `analysis_config.json`
- `figures/*.png`（300 dpi）

欄位值缺失時使用空白/NA，不使用字串 `missing` 混入數值欄。Word 中可顯示「無法計算」並附原因。

## 13. 軟體架構需求

延續既有「分析純函式不依賴 Qt」原則。建議責任邊界如下；檔名為規格層級命名，實作前可依現有慣例調整，但介面責任不可混合：

| 元件 | 責任 |
|---|---|
| dataset/manifest | 讀取、驗證、配對研究資料集 |
| analysis/quality | 通道狀態、ROI 品質、警告碼與排除原因 |
| analysis/metrics | baseline mean、signed/positive integral、centroid |
| analysis/laterality | LI、分母防護、分類、bootstrap |
| analysis/prepost | delta、DiD、配對資料建立 |
| analysis/regional | ROI contrasts 與比較 family |
| statistics | t/Wilcoxon/Welch/Mann–Whitney、LMM、效果量、CI、多重校正 |
| services | 串接 loader、ROI、metrics、statistics，不直接繪圖 |
| visualization | 從結果物件產生可重現圖表 |
| reporting | 從結構化結果建立 DOCX 與表格輸出 |
| ui | 輸入、互動、進度、結果顯示，不直接計算統計量 |

### 13.1 結果物件共同要求

所有分析結果至少包含：

```text
estimate, standard_error, confidence_interval, statistic, p_value,
adjusted_p_value, effect_size, n_included, n_excluded,
method, assumptions, warnings, provenance
```

不適用欄位使用 null；不得以 0 代替計算失敗。

### 13.2 相依套件原則

- 沿用 NumPy、pandas、SciPy、Matplotlib、openpyxl、python-docx 與 PyQt5。
- LMM/模型診斷可加入 `statsmodels`，版本需鎖定於支援 Python 3.11/3.12 的同一 major 版。
- 不為單一功能引入完整 R 執行環境。
- 所有隨機程序接受顯式 seed，CI 測試可重現。

## 14. 錯誤處理與安全性

- 匯入失敗需指出檔名、工作表、欄位及可修正原因，不顯示原始堆疊給一般使用者。
- 批次中單一檔案失敗時，其餘檔案仍可完成；失敗檔列入排除表。
- 統計模型失敗不得靜默改用另一模型；顯示原因並讓使用者修改設定。
- 報告生成採先寫入暫存檔再移動到目標位置，避免留下半成品。
- 預設不將個案姓名、ID 或檔案內容送往網路；所有分析離線完成。
- log 不記錄完整個案姓名；以 subject_id 或雜湊識別。

## 15. 測試與驗收條件

### 15.1 數值單元測試

- L=3、R=1 時 LI=0.5；L=1、R=3 時 LI=-0.5；L=R>0 時 LI=0。
- L+R 接近 0 時回傳缺失與 `W_LI_DENOMINATOR_SMALL`，不得除以 0。
- 異號 L/R 產生 `W_LI_OPPOSITE_SIGNS`，不自動分類。
- 缺一個通道時 ROI 等於剩餘通道平均，狀態為 `degraded`，且記錄 X/Y。
- ROI 全部通道缺失時為 `invalid`，不得回傳全零波形。
- baseline/task window 超出範圍時阻止該檔分析。
- `delta`、DiD、Holm/FDR 校正以手算小型資料驗證。
- bootstrap 在固定 seed 下產生相同 CI，且重抽樣單位為 block/subject。

### 15.2 統計驗證

- 以已知結果的合成資料比對 SciPy/statsmodels 輸出，檢查 estimate、CI、p 值與效果量。
- 配對資料不能誤用獨立樣本檢定；未配對資料不能進入 paired test。
- 兩組 pre/post 的主結果必須是 `group × time`，不能以兩個組內 p 值取代。
- 三個以上 ROI 的 pairwise 結果須全部出現並屬於同一 correction family。
- 零變異、極小樣本、奇異 LMM 需回傳明確狀態，不輸出看似有效的推論。

### 15.3 整合與 UI 驗收

- 既有單檔 Integral/Centroid 回歸測試保持通過。
- 現代/舊版 Excel 各以正常、缺通道、部分缺值及壞時間軸 fixture 測試。
- 研究資料集可匯入至少 100 個檔案，UI 不凍結，並可取消處理。
- 重啟程式後可重新載入 montage、ROI、分析設定與 manifest。
- Word 報告能開啟，表格數值與 CSV 一致，圖片存在且為 300 dpi。
- 產生的 EXE 在乾淨 Windows 10/11 測試機離線啟動，無需安裝 Python。

### 15.4 完成定義

本功能只有在下列條件全部達成後才視為完成：

- 所有新增與既有自動化測試通過。
- 數值結果經至少一組獨立手算 fixture 與一組去識別化真實資料核對。
- 缺失通道不再被靜默轉成 0。
- 三種分析均可由 UI 完成並匯出 Word/CSV/JSON。
- 報告完整揭露設定、N、排除、警告、效果量、CI 與多重比較方法。
- 領域專家確認 ROI 映射、LI 方向與報告用語；統計審閱者確認模型與效果量。

## 16. 相容性與遷移

- 既有 `NirsAnalysisService.analyze()` 的單檔流程及既有設定檔需保持可用。
- 舊設定沒有 ROI/統計欄位時，自動載入內建 15 通道 montage 與既有時間窗，不改寫原檔；使用者儲存後再寫入新版 schema。
- 既有報告仍可選「傳統版」；研究版報告使用新的結構化結果物件。
- 既有 `front` 對應 `anterior_frontal`，既有 `side` 對應衍生的 `lateral_frontal`；遷移時保留名稱對照於 provenance。

## 17. 風險與控制

| 風險 | 控制方式 |
|---|---|
| 通道號碼不等於跨受試者相同腦區 | 報告 montage 版本；正式研究要求一致探頭配置並揭露定位限制 |
| 頭皮血流/頭動造成假活化 | 顯示輸入前處理聲明；未有 short-separation 時列入限制 |
| LI 分母小或 L/R 異號造成爆值 | 分母防護、異號警告、同報 L/R、不裁切數值 |
| 分析選項過多造成結果挑選 | 保存完整 config、主要端點與方法；所有 contrasts 皆匯出 |
| 多通道/多 ROI 假陽性 | 預設 Holm/FDR，顯示 correction family |
| 小樣本 LMM 不穩 | 顯示收斂/奇異診斷，不自動宣告顯著 |
| pre/post 探頭重新定位降低可靠度 | 報告 session 品質與定位限制；需要時另報 ICC/SEM/Bland–Altman |
| 逆向重建程式與原版行為不完全一致 | 保留 golden-master 比對與領域專家驗收 |

## 18. 開發優先順序

1. 共用資料模型、manifest、ROI 設定與缺失通道品質控管。
2. 單次量測拆分 Left/Right PFC，完成 LI 點估計與報告。
3. 受試者層級表、pre/post 配對、配對檢定、效果量與圖表。
4. 腦區差異、Holm/FDR、多 ROI 結果表與圖表。
5. 群組 LI、group × time、region × time 及 LMM 診斷。
6. 研究版 Word/CSV/JSON 匯出與 Windows EXE 回歸驗證。

每一階段都應能以獨立 fixture 驗收；不得先完成 UI 再補數值測試。

## 19. 方法依據與追溯來源

### 19.1 本機參考資料

- `D:/心理學/NIRSlateral/NIRSlateral_技術文章.md`
- `D:/心理學/NIRSlateral/papers/`
- `D:/心理學/NIRSdiff/NIRSdiff_統計分析技術文章.md`
- `D:/心理學/NIRSdiff/NIRSdiff_文獻整理.md`
- `D:/心理學/NIRSdiff/NIRSdiff_參考文獻.bib`
- `D:/心理學/NIRSParts/README.md`
- `D:/心理學/NIRSParts/英文文獻矩陣.md`
- `D:/心理學/NIRSParts/日文文獻矩陣.md`

### 19.2 已核對的關鍵文獻

1. Borrell JA, Fraser K, Manattu AK, Zuniga JM (2023). *Laterality Index Calculations in a Control Study of Functional Near Infrared Spectroscopy*. Brain Topography, 36(2), 210–222. [DOI:10.1007/s10548-023-00942-3](https://doi.org/10.1007/s10548-023-00942-3).
2. Tak S, Ye JC (2014). *Statistical analysis of fNIRS data: A comprehensive review*. NeuroImage, 85, 72–91. [DOI:10.1016/j.neuroimage.2013.06.016](https://doi.org/10.1016/j.neuroimage.2013.06.016).
3. Yücel MA, Lühmann AV, Scholkmann F, et al. (2021). *Best practices for fNIRS publications*. Neurophotonics, 8(1), 012101. [DOI:10.1117/1.NPh.8.1.012101](https://doi.org/10.1117/1.NPh.8.1.012101).
4. de Rond V, Gilat M, D'Cruz N, Hulzinga F, Orban de Xivry J-J, Nieuwboer A (2023). *Test-retest reliability of functional near-infrared spectroscopy during a finger-tapping and postural task in healthy older adults*. Neurophotonics, 10(2), 025010. [DOI:10.1117/1.NPh.10.2.025010](https://doi.org/10.1117/1.NPh.10.2.025010).
5. Zhou X-Q, Zhang Q-L, Xi X, et al. (2023). *Cortical responses correlate with speech performance in pre-lingually deaf cochlear implant children*. Frontiers in Neuroscience, 17, 1126813. [DOI:10.3389/fnins.2023.1126813](https://doi.org/10.3389/fnins.2023.1126813).

以上 DOI、年份與可列出的作者資訊已於 2026-08-26 重新核對。完整作者清單以 DOI 出版頁為準；本文件未發現重複 DOI。

## 20. 規格審閱決策

本版採以下明確假設，供正式實作前確認：

- 15 通道映射沿用現有程式；Left/Right PFC 為 LI 的預設左右 ROI。
- `baseline_corrected_mean` 是新統計功能的主要端點，既有 Integral/Centroid 保留。
- 統計推論使用多檔「研究資料集」模式；單檔模式不把 frame 當樣本。
- LI 分類預設切點為 ±0.10，但只作描述且可設定。
- 缺通道時以剩餘有效通道等權平均；完整揭露 X/Y，無有效通道時停止該 ROI 計算。
- 多重比較預設 Holm；探索性通道分析可選 FDR。
- 完整 GLM 前處理、short-separation regression 與 3D 腦表面定位留在後續版本。

審閱通過後，下一步才是依本規格建立實作計畫；未取得審閱同意前不開始修改程式。
