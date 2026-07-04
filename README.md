# 英語角落 EnCorner

靜態英文學習資源網站，部署於 GitHub Pages。

**Live**: https://iangithub.github.io/en-learning/

## 功能

- **英文聽力高頻句** — 20 個生活情境、511 句美國人日常溝通高頻句(派對、點餐、看診、面試、閒聊⋯⋯)。
- **TOEIC 高頻單字** — 2,722 個五星高頻字彙,依 15 個商務情境分類。

每張字卡:正面為英文 + 發音 + 中文;翻面提供時態/文法重點、替換說法、詞性變化、延伸例句與考點提示。支援隨機、遮中文自測、只看未學會、自動發音,學習進度存於瀏覽器 localStorage。

## 技術

- 純靜態 HTML/CSS/JS,無建置流程、無執行期外部 API。
- 所有內容為預先生成:
  - 字卡內容:Azure OpenAI `gpt-5.5`
  - 發音 MP3:Azure Speech TTS(Ava / Andrew 神經語音,對話句男女聲交替)
  - 插圖:Azure OpenAI `gpt-image-2`(轉 WebP)
- 生成腳本在 `tools/`,憑證讀取自倉庫外的 `../aiconfig.json`(不進版控)。

## 開發

```bash
python -m http.server 8000   # 本機預覽
```

資料來源規格(`spec/`,不進版控):英文聽力高頻句 PDF、TOEIC 字彙 JSON。
