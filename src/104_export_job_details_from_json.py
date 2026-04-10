import argparse
import csv
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
if PROJECT_ROOT.name == "src":
    PROJECT_ROOT = PROJECT_ROOT.parent

DEFAULT_INPUT_DIR = PROJECT_ROOT / "mock_object_storage"
DEFAULT_OUTPUT_CSV = PROJECT_ROOT / "104_job_details.csv"
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


def normalize_job_detail(payload: Any) -> dict[str, str]:
    """將 104 原始 JSON payload 整理成固定輸出欄位。"""
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
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


def load_payload(path: Path) -> Any:
    """讀取單一 JSON 檔案。"""
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def iter_json_files(input_dir: Path) -> list[Path]:
    """列出輸入資料夾內的 JSON 檔案。"""
    return sorted(path for path in input_dir.glob("*.json") if path.is_file())


def write_output_rows(path: str | Path, rows: list[dict[str, str]]) -> None:
    """將整理後的職缺資料寫入 CSV。"""
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    """解析 CLI 參數。"""
    parser = argparse.ArgumentParser(
        description="從 mock_object_storage 讀取 104 職缺原始 JSON 並輸出 CSV"
    )
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-csv", default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    """CLI 入口：讀取 JSON 檔、整理欄位、輸出 CSV。"""
    args = parse_args()
    input_dir = Path(args.input_dir)
    json_files = iter_json_files(input_dir)

    if args.limit is not None:
        json_files = json_files[: args.limit]

    output_rows = []
    for idx, json_file in enumerate(json_files, start=1):
        try:
            payload = load_payload(json_file)
            detail = normalize_job_detail(payload)
            output_rows.append(detail)
            print(f"[{idx}] 完成 {json_file.name} -> {detail['jobName'] or 'unknown'}")
        except json.JSONDecodeError as exc:
            print(f"[{idx}] 失敗 {json_file.name}: JSON 解析錯誤 {exc}")
        except OSError as exc:
            print(f"[{idx}] 失敗 {json_file.name}: 讀檔錯誤 {exc}")

    write_output_rows(args.output_csv, output_rows)
    print(f"共寫入 {len(output_rows)} 筆到 {args.output_csv}")


if __name__ == "__main__":
    main()
