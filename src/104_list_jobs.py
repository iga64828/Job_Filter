import argparse
import json
from pathlib import Path
from pprint import pprint
from urllib.parse import parse_qsl, urlencode, urlparse

import pandas as pd
import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
if PROJECT_ROOT.name == "src":
    PROJECT_ROOT = PROJECT_ROOT.parent

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "104_config.yaml"
DEFAULT_AREA_CODES_PATH = PROJECT_ROOT / "104_area_codes.json"
DEFAULT_HEADERS = {
    "Referer": "https://www.104.com.tw/jobs/search/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
}
DEFAULT_URL = "https://www.104.com.tw/jobs/search/api/jobs"


def load_config(path: str | Path) -> dict:
    """讀取 YAML 設定檔並回傳 dict。"""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_area_code_map(path: str | Path) -> dict[str, str]:
    """讀取地區中文名稱與代碼對照表。"""
    with open(path, encoding="utf-8") as f:
        raw_map = json.load(f) or {}
    return {str(key): str(value) for key, value in raw_map.items()}


def resolve_area_codes(
    area_names: list[str], area_code_map: dict[str, str], custom_map: dict | None = None
) -> str:
    """將中文地區名稱轉成 104 area 代碼字串。"""
    area_map = area_code_map.copy()
    if custom_map:
        area_map.update({str(key): str(value) for key, value in custom_map.items()})

    resolved_codes = []
    for raw_name in area_names:
        name = str(raw_name).strip()
        if not name:
            continue

        code = area_map.get(name)
        if code is None:
            suffix_matches = sorted(
                {
                    area_code
                    for area_name, area_code in area_map.items()
                    if area_name.endswith(name)
                }
            )
            if len(suffix_matches) == 1:
                code = suffix_matches[0]

        if code is None:
            raise ValueError(f"找不到地區代碼: {name}")

        resolved_codes.append(code)

    return ",".join(dict.fromkeys(resolved_codes))


def build_request_parts(config: dict, page: int | None = None) -> tuple[str, dict]:
    """從 YAML 組出 API URL 與 query params。"""
    request_config = config.get("request", {})
    raw_url = request_config.get("url", DEFAULT_URL)

    parsed = urlparse(raw_url)
    base_url = (
        f"{parsed.scheme}://{parsed.netloc}{parsed.path}" if parsed.scheme else raw_url
    )

    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    raw_params = request_config.get("params", {}).copy()
    area_names = raw_params.pop("area_names", None)
    area_map = request_config.get("area_map", {})
    area_codes_path = request_config.get("area_codes_path", DEFAULT_AREA_CODES_PATH)
    area_code_map = load_area_code_map(area_codes_path)

    params.update(
        {
            str(key): str(value)
            for key, value in raw_params.items()
            if value not in (None, "")
        }
    )

    if area_names:
        if isinstance(area_names, str):
            area_names = [name.strip() for name in area_names.split(",")]
        params["area"] = resolve_area_codes(
            area_names, area_code_map=area_code_map, custom_map=area_map
        )

    if page is not None:
        params["page"] = str(page)

    return base_url or DEFAULT_URL, params


def build_debug_url(url: str, params: dict) -> str:
    """輸出目前實際請求 URL 供除錯。"""
    return f"{url}?{urlencode(params, safe=', ')}"


def fetch_jobs(url: str, headers: dict, params: dict, timeout: int) -> list[dict]:
    """呼叫 104 搜尋 API 並回傳職缺陣列。"""
    response = requests.get(url, headers=headers, params=params, timeout=timeout)
    response.raise_for_status()

    payload = response.json()
    data = payload.get("data")
    if isinstance(data, list):
        jobs = data
    else:
        jobs = []

    if not isinstance(jobs, list):
        raise ValueError("104 API 回傳格式異常，data.list 不是陣列")

    return jobs


def format_address(item: dict) -> str:
    """將 104 職缺地址欄位組成單一字串。"""
    parts = [
        str(
            item.get("jobAddrNoDesc") or item.get("jobAddrNoDescSnippet") or ""
        ).strip(),
        str(item.get("jobAddress") or item.get("jobAddressSnippet") or "").strip(),
    ]
    return "".join(part for part in parts if part)


def normalize_job(raw_job: dict) -> dict:
    """整理 API 回傳欄位，輸出一致的 CSV 結構。"""
    job_name = raw_job.get("jobName") or raw_job.get("jobNameSnippet") or ""
    job_link = raw_job.get("link", {}).get("job") or ""
    company_name = raw_job.get("custName") or ""
    address = format_address(raw_job)

    return {
        "job_name": job_name,
        "job_link": job_link,
        "company_name": company_name,
        "address": address,
    }


def crawl_104_jobs(config: dict) -> list[dict]:
    """依 YAML 設定抓取多頁職缺。"""
    timeout = int(config.get("timeout", 30))
    headers = DEFAULT_HEADERS.copy()

    request_config = config.get("request", {})
    start_page = int(request_config.get("start_page", 1))
    max_pages = int(config.get("max_pages", 1))

    jobs = []
    dedup = {}

    for offset in range(max_pages):
        current_page = start_page + offset
        url, params = build_request_parts(config, page=current_page)
        print(f"抓取第 {current_page} 頁: {build_debug_url(url, params)}")

        raw_jobs = fetch_jobs(url=url, headers=headers, params=params, timeout=timeout)
        print(f"第 {current_page} 頁 API 回傳 {len(raw_jobs)} 筆")

        for raw_job in raw_jobs:
            normalized = normalize_job(raw_job)
            if not normalized["job_name"] or not normalized["job_link"]:
                continue

            dedup[normalized["job_link"]] = normalized

    jobs.extend(dedup.values())
    return jobs


def main():
    """CLI 入口：讀設定、抓資料、輸出 CSV。"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", default=DEFAULT_CONFIG_PATH, help="Path to YAML config file"
    )
    args = parser.parse_args()

    config = load_config(args.config)

    jobs = crawl_104_jobs(config)
    df = pd.DataFrame(jobs)
    pprint(df)
    df.to_csv(config["output_csv"], index=False, encoding="utf-8-sig")

    print(df.head())
    print(f"總共 {len(df)} 筆，已輸出到 {config['output_csv']}")


if __name__ == "__main__":
    main()
