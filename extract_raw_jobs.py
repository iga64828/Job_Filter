import argparse
import json
from pathlib import Path

import requests

DEFAULT_URL = "https://www.104.com.tw/jobs/search/api/jobs"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.104.com.tw/jobs/search/",
    "Accept": "application/json, text/plain, */*",
}


def format_salary(item: dict) -> str:
    """將 104 職缺薪資欄位轉成可讀字串。"""
    if item.get("salaryDesc"):
        return str(item["salaryDesc"])

    low = item.get("salaryLow")
    high = item.get("salaryHigh")

    if low == 0 and high == 0:
        return "面議"

    if low is None and high is None:
        return ""

    if high == 9999999 and low is not None:
        return f"月薪 {low:,} 元以上"

    if low is not None and high is not None:
        return f"月薪 {low:,} - {high:,} 元"

    if low is not None:
        return f"月薪 {low:,} 元"

    return f"月薪最高 {high:,} 元"


def extract_jobs(raw_data: dict) -> list[dict]:
    jobs = raw_data.get("data", [])
    result = []

    for item in jobs:
        result.append(
            {
                "company_name": item.get("custName", ""),
                "salary": format_salary(item),
                "job_title": item.get("jobName", ""),
                "job_link": (item.get("link") or {}).get("job", ""),
            }
        )

    return result


def parse_key_value_pairs(values: list[str], splitter: str, arg_name: str) -> dict:
    parsed = {}
    for value in values:
        if splitter not in value:
            raise ValueError(f"{arg_name} 格式錯誤: {value}")
        key, raw_val = value.split(splitter, 1)
        key = key.strip()
        raw_val = raw_val.strip()
        if not key:
            raise ValueError(f"{arg_name} key 不可為空: {value}")
        parsed[key] = raw_val
    return parsed


def fetch_raw_json(url: str, headers: dict, params: dict) -> dict:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="以指定 request 與 header 抓取 JSON，並抽取公司名稱、薪水、職缺標題、職缺連結"
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="API URL")
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help='自訂 header，格式: "Key: Value"，可重複帶入',
    )
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help='查詢參數，格式: "key=value"，可重複帶入',
    )
    parser.add_argument(
        "--raw-output",
        default="raw.json",
        help="原始 JSON 輸出路徑",
    )
    parser.add_argument("--output", default="raw_extracted.json", help="輸出 JSON 路徑")
    args = parser.parse_args()

    headers = DEFAULT_HEADERS.copy()
    headers.update(parse_key_value_pairs(args.header, ":", "--header"))

    params = parse_key_value_pairs(args.param, "=", "--param")
    if not params:
        params = {"keyword": "資料工程師", "page": "1"}

    raw_data = fetch_raw_json(args.url, headers=headers, params=params)

    raw_output_path = Path(args.raw_output)
    output_path = Path(args.output)

    with raw_output_path.open("w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)

    result = extract_jobs(raw_data)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"已抓取 JSON，輸出至: {raw_output_path}")
    print(f"已抽取 {len(result)} 筆職缺，輸出至: {output_path}")


if __name__ == "__main__":
    main()
