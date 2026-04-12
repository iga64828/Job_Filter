import argparse
import csv
import json
import re
import time
from pathlib import Path

import requests
from google.cloud import storage

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_INPUT_CSV = PROJECT_ROOT / "data" / "processed" / "104_jobs.csv"
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


def upload_payload_to_gcs(
    bucket: storage.Bucket,
    blob_name: str,
    payload: dict | list,
    overwrite: bool,
) -> bool:
    """
    將 payload 上傳到 GCS。
    回傳 True 代表有寫入；False 代表因檔案已存在且未開啟 overwrite 而跳過。
    """
    blob = bucket.blob(blob_name)
    if not overwrite and blob.exists():
        return False

    blob.upload_from_string(
        json.dumps(payload, ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="從 104_jobs.csv 抓原始 JSON，並直接上傳到 GCP Cloud Storage"
    )
    parser.add_argument("--input-csv", default=DEFAULT_INPUT_CSV)
    parser.add_argument("--bucket", required=True, help="GCS bucket 名稱")
    parser.add_argument(
        "--prefix",
        default="raw/104",
        help="GCS 物件前綴（例如 raw/104 或 jobs/104/raw）",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="GCP project ID（不帶則使用環境預設認證專案）",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="若 GCS 已存在同名物件則覆蓋",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    storage_client = storage.Client(project=args.project)
    bucket = storage_client.bucket(args.bucket)
    prefix = args.prefix.strip("/")

    with open(args.input_csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if args.limit is not None:
        rows = rows[: args.limit]

    uploaded_count = 0
    skipped_count = 0
    failed_count = 0

    for idx, row in enumerate(rows, start=1):
        job_link = (row.get("job_link") or "").strip()
        job_id = extract_job_id(job_link)
        if not job_id:
            skipped_count += 1
            print(f"[{idx}] 跳過：無法從網址抽出 job id -> {job_link}")
            continue

        try:
            payload = fetch_job_raw_payload(job_id, timeout=args.timeout)
            blob_name = f"{prefix}/{job_id}.json" if prefix else f"{job_id}.json"
            wrote = upload_payload_to_gcs(
                bucket=bucket,
                blob_name=blob_name,
                payload=payload,
                overwrite=args.overwrite,
            )

            if wrote:
                uploaded_count += 1
                print(
                    f"[{idx}] 完成 {job_id} -> gs://{args.bucket}/{blob_name}"
                )
            else:
                skipped_count += 1
                print(
                    f"[{idx}] 跳過 {job_id}：已存在 gs://{args.bucket}/{blob_name}"
                )
        except requests.RequestException as exc:
            failed_count += 1
            print(f"[{idx}] 失敗 {job_id}: {exc}")
        except ValueError as exc:
            failed_count += 1
            print(f"[{idx}] 失敗 {job_id}: JSON 解析錯誤 {exc}")
        except Exception as exc:
            failed_count += 1
            print(f"[{idx}] 失敗 {job_id}: GCS 上傳錯誤 {exc}")

        if args.sleep > 0:
            time.sleep(args.sleep)

    print(
        "完成。"
        f"上傳 {uploaded_count} 筆，跳過 {skipped_count} 筆，失敗 {failed_count} 筆。"
    )


if __name__ == "__main__":
    main()
