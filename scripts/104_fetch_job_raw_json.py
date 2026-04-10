import argparse
import csv
import json
import re
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_INPUT_CSV = PROJECT_ROOT / "data" / "processed" / "104_jobs.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "104"
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


def fetch_job_raw_payload(job_id: str, timeout: int) -> dict | list:
    """呼叫單一職缺 API，回傳原始 JSON payload。"""
    referer = f"https://www.104.com.tw/job/{job_id}"
    api_url = f"https://www.104.com.tw/api/jobs/{job_id}"
    headers = {
        "Referer": referer,
        "User-Agent": USER_AGENT,
    }

    response = requests.get(api_url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def save_payload(output_dir: Path, job_id: str, payload: dict | list) -> Path:
    """將原始 payload 存成單一 JSON 檔案。"""
    output_path = output_dir / f"{job_id}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="從 data/processed/104_jobs.csv 逐筆抓職缺原始 JSON 並存到 data/raw/104"
    )
    parser.add_argument("--input-csv", default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(args.input_csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if args.limit is not None:
        rows = rows[: args.limit]

    success_count = 0
    for idx, row in enumerate(rows, start=1):
        job_link = (row.get("job_link") or "").strip()
        job_id = extract_job_id(job_link)
        if not job_id:
            print(f"[{idx}] 跳過：無法從網址抽出 job id -> {job_link}")
            continue

        try:
            payload = fetch_job_raw_payload(job_id, timeout=args.timeout)
            output_path = save_payload(output_dir=output_dir, job_id=job_id, payload=payload)
            success_count += 1
            print(f"[{idx}] 完成 {job_id} -> {output_path}")
        except requests.RequestException as exc:
            print(f"[{idx}] 失敗 {job_id}: {exc}")
        except ValueError as exc:
            print(f"[{idx}] 失敗 {job_id}: JSON 解析錯誤 {exc}")

        if args.sleep > 0:
            time.sleep(args.sleep)

    print(f"共寫入 {success_count} 筆到 {output_dir}")


if __name__ == "__main__":
    main()
