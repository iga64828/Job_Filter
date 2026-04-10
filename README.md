#  工作篩選器 (Job_Filter)
對我來說資料工程師就是搞ETL Pipeline\
但是台灣一堆Title寫資料工程師卻要一人兼 `DS`/`DA`/`DevOps`/`前端` 的一條龍缺\
真正符合的缺少之又少\
我每天都要

```
肉眼逐筆看職缺內容 --> 跟我的履歷比對檢查我還缺什麼能力 --> 如果職缺條件有一半都會那就寫自介信投遞
```
某天覺得很煩，想自動化這件事情


## 主要流程
1. 呼叫API/爬蟲 抓取特定Title的職缺
2. 基於職缺URL逐筆抓`title`, `地址`, `工作內容`, `條件要求`, `薪資範圍`
3. 以LLM基於`條件要求`+`工作內容`與我的履歷自動比對並整理我還缺少的東西及對應的自介信
4. 建立對話介面可基於特定職缺跟LLM討論 (自介信修改、職涯諮詢等) 


Tech Stack:
- `Airflow`排程
- `Python`負責ETL
- LLM預計使用Claude或是8B的地端LLM

## 目前專案結構

```text
config/
  104.yaml
data/
  raw/104/
  processed/
  reference/104_area_codes.json
scripts/
  104_list_jobs.py
  104_fetch_job_raw_json.py
  104_fetch_job_details.py
  104_export_job_details_from_json.py
  experiments/yourator_scrape.py
tests/
```

## Pipeline 指令

```bash
python scripts/104_list_jobs.py
python scripts/104_fetch_job_raw_json.py
python scripts/104_export_job_details_from_json.py
python scripts/104_fetch_job_details.py
```
