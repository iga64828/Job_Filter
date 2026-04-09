---
name: auto-commit-zh
description: 在 Git 專案中產生中文 conventional commit 訊息，先列出建議提交的檔案與 commit 訊息供使用者審核，經確認後才 stage 與 commit。當使用者要求自動 commit、幫忙寫 commit 訊息、用 conventional commit 提交，且希望先審核訊息或檔案時使用。
---

# Auto Commit Zh

這個 skill 用於「先審核，再 commit」。

## 工作方式

1. 先執行 `bash .claude/skills/auto-commit-zh/scripts/preview_commit.sh` 收集目前 git 狀態。
2. 根據使用者要求，區分：
   - 已明確指定要 commit 的檔案
   - 尚未指定，需先提議一組待提交檔案
3. 只根據本次要提交的檔案內容產生 commit 訊息，不把無關變更混進去。
4. commit 訊息必須使用中文 conventional commit，格式為：

```text
<type>[(<scope>)][!]: <中文摘要>
```

範例：

```text
feat(scraper): 支援以中文地區名稱轉換 104 搜尋代碼
fix(config): 修正 104 搜尋參數載入邏輯
chore(skill): 新增可審核的自動 commit 技能
```

## 必要互動

在真的執行 `git add` 或 `git commit` 前，必須先向使用者展示：

- 本次建議提交的檔案清單
- 建議的 commit 訊息

然後明確等待使用者確認。至少要讓使用者能夠：

- 同意目前檔案與訊息
- 修改 commit 訊息
- 增減要提交的檔案
- 取消本次提交

如果使用者要求「我要能審核 commit 訊息及要 commit 的檔案」，就不能直接 commit。

## 執行規則

1. 如果使用者還沒指定檔案：
   - 先根據 `git status --short` 提議一組合理檔案
   - 只把和當前任務直接相關的檔案列進建議清單
2. 如果使用者指定了檔案：
   - 只針對那些檔案產生 commit 訊息與提交建議
3. 使用者確認後：
   - 先執行 `git add -- <files...>`
   - 再用核准後的訊息執行 `git commit -m "<message>"`
4. 若使用者修改檔案清單：
   - 重新檢視該檔案 diff
   - 重新產生一次 commit 訊息給使用者審核
5. 若 staged 內容與核准檔案不一致：
   - 不要直接 commit
   - 先用 `git reset HEAD -- <files...>` 或重新 stage 精準調整
   - 避免把不相關檔案一起送出

## Conventional Commit 類型

- `feat`: 新功能
- `fix`: 修正 bug
- `chore`: 維護、設定、腳本、非功能性調整
- `docs`: 文件變更
- `refactor`: 重構但不改行為
- `test`: 測試新增或修正
- `style`: 純格式調整
- `ci`: CI/CD 相關

## 訊息撰寫規則

- 主旨用中文
- 主旨精簡，聚焦使用者可理解的改動
- 不要加句號
- 除非真的有破壞性變更，否則不要加 `!`
- 沒有明確 scope 時可省略 scope

## 輸出格式

審核階段優先用這個格式回覆：

```text
建議提交檔案:
1. path/to/file_a
2. path/to/file_b

建議 commit 訊息:
chore(skill): 新增可審核的自動 commit 技能
```

然後請使用者確認是否：

- 直接提交
- 修改訊息
- 調整檔案
- 取消
