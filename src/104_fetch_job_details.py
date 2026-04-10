import argparse
import csv
import json
import re
import time
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parent
if PROJECT_ROOT.name == "src":
    PROJECT_ROOT = PROJECT_ROOT.parent

DEFAULT_INPUT_CSV = PROJECT_ROOT / "104_jobs.csv"
DEFAULT_OUTPUT_CSV = PROJECT_ROOT / "104_job_details.csv"
DEFAULT_TIMEOUT = 20
DEFAULT_SLEEP_SECONDS = 0.2
JOB_URL_PATTERN = re.compile(r"https?://www\.104\.com\.tw/job/([^/?#]+)")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
)
OUTPUT_FIELDS = [
    "appearDate",
    "jobName",
    "salary",
    "custName",
    "workExp",
    "jobAddress",
    "jobDescription",
    "welfare",
]


def extract_job_id(job_link: str) -> str | None:
    """從職缺網址抽出 /job/ 後面的 ID，抽不到就回傳 None。"""
    if not job_link:
        return None

    match = JOB_URL_PATTERN.search(job_link.strip())
    return match.group(1) if match else None


def find_key_recursive(obj: Any, target_key: str) -> Any | None:
    """在巢狀 dict/list 中，回傳第一個指定 key 的非空值。"""
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


def clean_text(value: Any) -> str:
    """統一輸出為單行字串，方便直接寫入 CSV。"""
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)

    return " ".join(text.split())


def get_detail_value(data: Any, key: str) -> str:
    """從 detail payload 中取值並清洗成單行文字。"""
    return clean_text(find_key_recursive(data, key))


def normalize_job_detail(data: Any) -> dict[str, str]:
    """將 104 detail payload 整理成固定輸出欄位。"""
    address_region = get_detail_value(data, "addressRegion")
    address_detail = get_detail_value(data, "addressDetail")

    return {
        "appearDate": get_detail_value(data, "appearDate"),
        "jobName": get_detail_value(data, "jobName"),
        "salary": get_detail_value(data, "salary"),
        "custName": get_detail_value(data, "custName"),
        "workExp": get_detail_value(data, "workExp"),
        "jobAddress": f"{address_region}{address_detail}",
        "jobDescription": get_detail_value(data, "jobDescription"),
        "welfare": get_detail_value(data, "welfare"),
    }


def fetch_job_detail(job_id: str, timeout: int) -> dict[str, str]:
    """呼叫單一職缺 API，回傳整理後的職缺資料。"""
    referer = f"https://www.104.com.tw/job/{job_id}"
    api_url = f"https://www.104.com.tw/api/jobs/{job_id}"
    headers = {
        "Referer": referer,
        "User-Agent": USER_AGENT,
    }

    response = requests.get(api_url, headers=headers, timeout=timeout)
    response.raise_for_status()

    payload = response.json()
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    return normalize_job_detail(data)


def load_input_rows(path: str | Path) -> list[dict[str, str]]:
    """讀取輸入 CSV。"""
    with open(path, newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_output_rows(path: str | Path, rows: list[dict[str, str]]) -> None:
    """將整理後的職缺資料寫入 CSV。"""
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    """解析 CLI 參數。"""
    parser = argparse.ArgumentParser(
        description="從 src/104_list_jobs.py 產生的 CSV 抓職缺詳細資料並輸出 CSV"
    )
    parser.add_argument("--input-csv", default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-csv", default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    """CLI 入口：讀取輸入 CSV、抓取詳細資料、輸出結果。"""
    args = parse_args()
    rows = load_input_rows(args.input_csv)

    if args.limit is not None:
        rows = rows[: args.limit]

    output_rows = []
    for idx, row in enumerate(rows, start=1):
        job_link = (row.get("job_link") or "").strip()
        job_id = extract_job_id(job_link)
        if not job_id:
            print(f"[{idx}] 跳過：無法從網址抽出 job id -> {job_link}")
            continue

        try:
            detail = fetch_job_detail(job_id, timeout=args.timeout)
            output_rows.append(detail)
            print(f"[{idx}] 完成 {detail['jobName'] or job_id}")
        except requests.RequestException as exc:
            print(f"[{idx}] 失敗 {job_id}: {exc}")
        except ValueError as exc:
            print(f"[{idx}] 失敗 {job_id}: JSON 解析錯誤 {exc}")

        if args.sleep > 0:
            time.sleep(args.sleep)

    write_output_rows(args.output_csv, output_rows)
    print(f"共寫入 {len(output_rows)} 筆到 {args.output_csv}")


if __name__ == "__main__":
    main()
