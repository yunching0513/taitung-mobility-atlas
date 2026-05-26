# Taitung Mobility Atlas — 01 Traffic Safety

台東縣交通安全地圖｜十年回顧（民 105–114 / 2016–2025）

互動式單頁地圖儀表板，以警政署 A1 級道路交通事故開放資料為基礎，視覺化呈現台東縣十年的死亡事故空間分布、年度趨勢與多維拆解。

## 線上預覽

GitHub Pages：`https://yunching0513.github.io/taitung-mobility-atlas/`

## 內容概要

- **01 — Decade Overview**：419 人 / 402 件 / 2016–2025
- **02 — Year-over-Year**：年度趨勢折線、運具組成堆疊棒、Top 10 鄉鎮 × 10 年熱力圖、2025 年快照
- **03 — Spatial Distribution**：Leaflet 互動地圖（2018+ 有經緯度），可依年份、運具篩選；點圓點看事件明細
- **04 — Headline Finding**：機車佔約 47% 的關鍵發現
- **05 — Breakdown**：鄉鎮、運具、道路類別、光線、24 小時、12 月份切面
- **06 — Notes**：資料來源說明與年度欄位差異

## 資料來源

- [內政部警政署 — 警政統計](https://www.npa.gov.tw/) 之 A1 級交通事故公開資料
- 透過 [政府資料開放平臺 data.gov.tw](https://data.gov.tw/) 取得，包含
  [歷史交通事故資料 (12197)](https://data.gov.tw/dataset/12197)、[A1 與 A2 (130110)](https://data.gov.tw/en/datasets/130110)、[111 年傷亡 (161199)](https://data.gov.tw/dataset/161199) 等

A1 定義：造成人員當場或 24 小時內死亡之道路交通事故。

## 資料欄位完整度

| 年度 | Schema | 經緯度 | 完整欄位（道路類別、肇因、光線等） |
|---|---|---|---|
| 2016 | 簡式 | ✗ | ✗ |
| 2017 | 簡式 | ✗ | ✗ |
| 2018–2020 | 完整 | ✓ | ✓ |
| 2021 | 簡式 | ✓ | ✗ |
| 2022–2025 | 完整 | ✓ | ✓ |

2016 與 2017 無經緯度，故地圖區段僅顯示 2018+ 事件，但所有年份皆納入趨勢／時間／月份統計。

## 檔案

```
index.html                       # 主頁面（單檔含所有 CSS + UI）
taitung_a1.js                    # 事件級資料與年度彙整 (window.TAITUNG_A1 / TAITUNG_YEARLY)
taitung_a1.json                  # 事件級資料 JSON
taitung_yearly_summary.json      # 年度彙整 JSON
extract_taitung_all.py           # 從原始 CSV 萃取的腳本（CSV 不附在 repo 中）
```

## 自行重跑

```bash
# 1. 從 data.gov.tw 下載 105–114 年 A1 CSV，放到 ./資料/<年>年傷亡道路交通事故資料/ 之下
# 2. 跑萃取腳本
python3 extract_taitung_all.py
# 會輸出 taitung_a1.json / taitung_yearly_summary.json / taitung_a1.js
```

## 設計

採用 Vision Zero Taiwan (VZT) 視覺風格：
- Lime `#C8D400` 為唯一強調色
- Noto Sans TC + Space Grotesk 字體組合
- 大量留白、超細字重 (100–300) 對大字號的對比
- 圓環為核心幾何元素，象徵「零」死亡願景

地圖底圖：CARTO Positron。

## 開發者

吳昀慶 · Designed for 台東縣交通安全分析

## 授權

程式碼：MIT。資料：依政府資料開放平臺授權條款，可自由使用，請註明來源。
