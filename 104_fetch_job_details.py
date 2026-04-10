import argparse
import csv
import json
import re
import time
from pathlib import Path

import requests

DEFAULT_INPUT_CSV = Path(__file__).parent / "104_jobs.csv"
DEFAULT_OUTPUT_CSV = Path(__file__).parent / "104_job_details.csv"
DEFAULT_TIMEOUT = 20
DEFAULT_SLEEP_SECONDS = 0.2
JOB_URL_PATTERN = re.compile(r"https?://www\.104\.com\.tw/job/([^/?#]+)")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
)


def extract_job_id(job_link: str) -> str | None:
    """從職缺網址抽出 /job/ 後面的 ID，抽不到就回傳 None。"""
    if not job_link:
        return None
    match = JOB_URL_PATTERN.search(job_link.strip())
    return match.group(1) if match else None


def find_key_recursive(obj, target_key: str):
    """在巢狀 dict/list 中，回傳第一個指定 key 的非空值。"""
    # 104 詳情 JSON 常有巢狀結構，且不同職缺節點位置可能不同。
    # 先檢查最外層，如果沒有該 key，就把該層所有子節點逐一拿去重新跑這個 function
    # 再一層一層往下找
    # 可避免把路徑寫死。
    if isinstance(obj, dict):
        current_value = obj.get(target_key)
        if current_value not in (None, ""):
            return current_value
        children = obj.values()
    elif isinstance(obj, list):
        children = obj
    else:
        return None

    for child in children:
        found_value = find_key_recursive(child, target_key)
        if found_value not in (None, ""):
            return found_value
    return None


def clean_text(value) -> str:
    """統一輸出為單行字串，方便直接寫入 CSV。"""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        # 物件型欄位（例如 welfare）轉成 JSON 字串保留完整資訊。
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return " ".join(text.split())


def fetch_job_detail(job_id: str, timeout: int) -> dict:
    """呼叫單一職缺 API，回傳目標四欄資料。"""
    referer = f"https://www.104.com.tw/job/{job_id}"
    api_url = f"https://www.104.com.tw/api/jobs/{job_id}"
    headers = {
        # Referer 要和 job_id 對得上，較不容易被站方視為異常請求。
        "Referer": referer,
        "User-Agent": USER_AGENT,
    }

    response = requests.get(api_url, headers=headers, timeout=timeout)
    response.raise_for_status()

    payload = response.json()
    data = payload.get("data", payload) if isinstance(payload, dict) else payload

    # 輸出固定欄位，確保後續 CSV schema 穩定。
    return {
        "salary": clean_text(find_key_recursive(data, "salary")),
        "jobDescription": clean_text(find_key_recursive(data, "jobDescription")),
        "welfare": clean_text(find_key_recursive(data, "welfare")),
        "jobName": clean_text(find_key_recursive(data, "jobName")),
    }


def main():
    # 這支程式假設 input CSV 至少有一欄 `job_link`（由 104_list_jobs.py 產生）。
    parser = argparse.ArgumentParser(
        description="從 104_list_jobs.py 產生的 CSV 抓職缺詳細資料並輸出 CSV"
    )
    parser.add_argument("--input-csv", default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-csv", default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    with open(args.input_csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # 方便先跑小樣本驗證，確認格式/內容正確後再全量跑。
    if args.limit is not None:
        rows = rows[: args.limit]

    # 主流程：逐筆抽 job_id -> 呼叫 API -> 只保留四個目標欄位。
    output_rows = []
    for idx, row in enumerate(rows, start=1):
        job_link = (row.get("job_link") or "").strip()
        job_id = extract_job_id(job_link)
        if not job_id:
            print(f"[{idx}] 跳過：無法從網址抽出 job id -> {job_link}")
            continue

        try:
            detail = fetch_job_detail(job_id, timeout=args.timeout)
            output_rows.append(
                {
                    "appearDate": detail["appearDate"],
                    "jobName": detail["jobName"],
                    "salary": detail["salary"],
                    "custName": detail["custName"],
                    "workExp": detail["workExp"],
                    "jobAddress": detail["addressRegion"] + detail["addressDetail"],
                    "jobDescription": detail["jobDescription"],
                    "welfare": detail["welfare"],
                }
            )
            print(f"[{idx}] 完成 {detail['jobName']}")
        except requests.RequestException as exc:
            print(f"[{idx}] 失敗 {job_id}: {exc}")
        except ValueError as exc:
            print(f"[{idx}] 失敗 {job_id}: JSON 解析錯誤 {exc}")

        if args.sleep > 0:
            # 請求節流：避免短時間大量打 API 被限流。
            time.sleep(args.sleep)

    fieldnames = [
        "salary",
        "jobDescription",
        "welfare",
        "jobName",
    ]
    with open(args.output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"共寫入 {len(output_rows)} 筆到 {args.output_csv}")


if __name__ == "__main__":
    main()
