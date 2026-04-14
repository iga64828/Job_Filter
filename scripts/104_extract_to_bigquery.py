import argparse
import json
from pathlib import Path
from typing import Any

from google.cloud import bigquery

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "raw" / "104"

def get_field(data: dict, keys: list, default: Any = "") -> Any:
    """Safely traverse a nested dictionary."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data if data is not None else default

def parse_list_of_dicts(items: Any, key: str = "description") -> str:
    """Extract comma separated values from a list of dicts."""
    if not isinstance(items, list):
        return ""
    return ", ".join([str(item.get(key, "")) for item in items if isinstance(item, dict) and item.get(key)])

def process_job_json(filepath: Path) -> dict:
    """Parse raw JSON and extract the 21 required fields."""
    with open(filepath, "r", encoding="utf-8") as f:
        payload = json.load(f)
    
    # Depending on the API, actual data might be inside 'data' key or root
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    
    job_category = parse_list_of_dicts(get_field(data, ["jobDetail", "jobCategory"]))
    skills = parse_list_of_dicts(get_field(data, ["condition", "skill"]))
    specialty = parse_list_of_dicts(get_field(data, ["condition", "specialty"]))
    
    address_region = str(get_field(data, ["jobDetail", "addressRegion"]))
    address_detail = str(get_field(data, ["jobDetail", "addressDetail"]))
    job_location = f"{address_region}{address_detail}"
    
    return {
        "job_name": str(get_field(data, ["header", "jobName"])),
        "company_name": str(get_field(data, ["header", "custName"])),
        "job_description": str(get_field(data, ["jobDetail", "jobDescription"])),
        "salary": str(get_field(data, ["jobDetail", "salary"])),
        "job_category": job_category,
        "education_requirement": str(get_field(data, ["condition", "edu"])),
        "work_experience": str(get_field(data, ["condition", "workExp"])),
        "work_skills": skills,
        "familiar_tools": specialty,
        "other_conditions": str(get_field(data, ["condition", "other"])),
        "is_remote": str(get_field(data, ["jobDetail", "remoteWork"])),
        "location": job_location,
        "longitude": float(get_field(data, ["jobDetail", "longitude"], 0.0) or 0.0),
        "latitude": float(get_field(data, ["jobDetail", "latitude"], 0.0) or 0.0),
        "need_employees": str(get_field(data, ["jobDetail", "needEmp"])),
        "start_working_day": str(get_field(data, ["jobDetail", "startWorkingDay"])),
        "hr_name": str(get_field(data, ["contact", "hrName"])),
        "hr_email": str(get_field(data, ["contact", "email"])),
        "hr_reply_message": str(get_field(data, ["contact", "reply"])),
        "industry": str(get_field(data, ["industry"])),
        "company_size": str(get_field(data, ["employees"]))
    }

def load_to_bigquery(rows: list[dict], project_id: str, dataset_id: str, table_id: str):
    """Load parsed data directly to BigQuery."""
    client = bigquery.Client(project=project_id) if project_id else bigquery.Client()
    
    table_ref = f"{client.project}.{dataset_id}.{table_id}"
    
    # Define schema explicitly based on requested 21 fields
    schema = [
        bigquery.SchemaField("job_name", "STRING"),
        bigquery.SchemaField("company_name", "STRING"),
        bigquery.SchemaField("job_description", "STRING"),
        bigquery.SchemaField("salary", "STRING"),
        bigquery.SchemaField("job_category", "STRING"),
        bigquery.SchemaField("education_requirement", "STRING"),
        bigquery.SchemaField("work_experience", "STRING"),
        bigquery.SchemaField("work_skills", "STRING"),
        bigquery.SchemaField("familiar_tools", "STRING"),
        bigquery.SchemaField("other_conditions", "STRING"),
        bigquery.SchemaField("is_remote", "STRING"),
        bigquery.SchemaField("location", "STRING"),
        bigquery.SchemaField("longitude", "FLOAT"),
        bigquery.SchemaField("latitude", "FLOAT"),
        bigquery.SchemaField("need_employees", "STRING"),
        bigquery.SchemaField("start_working_day", "STRING"),
        bigquery.SchemaField("hr_name", "STRING"),
        bigquery.SchemaField("hr_email", "STRING"),
        bigquery.SchemaField("hr_reply_message", "STRING"),
        bigquery.SchemaField("industry", "STRING"),
        bigquery.SchemaField("company_size", "STRING")
    ]
    
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE, # or WRITE_APPEND
    )
    
    print(f"Uploading {len(rows)} rows to BigQuery table {table_ref}...")
    job = client.load_table_from_json(rows, table_ref, job_config=job_config)
    job.result() # Wait for job to finish
    print(f"Loaded {job.output_rows} rows into {table_ref}.")

def main():
    parser = argparse.ArgumentParser(description="Extract 21 fields from 104 raw JSON and load to BigQuery.")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR, help="Path to raw json directories.")
    parser.add_argument("--project-id", default=None, help="GCP Project ID")
    parser.add_argument("--dataset-id", required=True, help="BigQuery Dataset ID")
    parser.add_argument("--table-id", required=True, help="BigQuery Table ID")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    json_files = sorted([p for p in input_dir.glob("*.json") if p.is_file()])
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return

    processed_rows = []
    failed_counts = 0
    for filepath in json_files:
        try:
            row = process_job_json(filepath)
            processed_rows.append(row)
        except Exception as e:
            print(f"Failed to process {filepath.name}: {e}")
            failed_counts += 1
            
    print(f"Successfully parsed {len(processed_rows)} jobs. Failed: {failed_counts}.")
    
    if processed_rows:
        load_to_bigquery(
            rows=processed_rows, 
            project_id=args.project_id, 
            dataset_id=args.dataset_id, 
            table_id=args.table_id
        )

if __name__ == "__main__":
    main()
