# 中文 Conventional Commit

在 Git 專案中，先審核要提交的檔案與 commit 訊息，再執行 commit。

## 步驟

1. 先執行 `bash .claude/skills/auto-commit-zh/scripts/preview_commit.sh` 查看目前變更。
2. 根據使用者要求，整理出本次建議提交的檔案清單。
3. 只根據這批檔案的變更內容，產生一則中文 conventional commit 訊息。
4. 先向使用者展示：
   - 建議提交檔案
   - 建議 commit 訊息
5. 明確等待使用者確認。允許使用者：
   - 直接提交
   - 修改訊息
   - 調整檔案
   - 取消
6. 使用者確認後才執行：
   - `git add -- <files...>`
   - `git commit -m "<message>"`

## 訊息格式

```text
<type>[(<scope>)][!]: <中文摘要>
```

範例：

```text
feat(scraper): 支援以中文地區名稱轉換 104 搜尋代碼
fix(config): 修正搜尋參數載入方式
chore(skill): 新增可審核的中文自動 commit 技能
```

## 類型

- `feat`: 新功能
- `fix`: 修正 bug
- `chore`: 維護、設定、腳本、非功能性調整
- `docs`: 文件變更
- `refactor`: 重構但不改行為
- `test`: 測試新增或修正
- `style`: 純格式調整
- `ci`: CI/CD 相關

## 規則

- commit 訊息主旨必須是中文
- 主旨要精簡且具體
- 不要加句號
- 除非是破壞性變更，否則不要加 `!`
- 使用者要求可審核時，不能直接 commit
- 不要把無關檔案一起提交
