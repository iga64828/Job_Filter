import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

APP_ROOT = Path(__file__).parent

# Add scripts dir to path to import llm_matcher
sys.path.append(str(APP_ROOT / "scripts"))
from llm_matcher import discuss_with_llm, evaluate_job_with_resume


def load_app_config() -> dict:
    config_path = APP_ROOT / "config" / "app.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


app_cfg = load_app_config()

st.set_page_config(page_title="104 Job Matcher AI", page_icon="💼", layout="wide")

st.title("💼 AI 面試助手: Data Engineer 職缺掃描與比對系統")

# Sidebar Configuration
st.sidebar.header("📁 履歷與設定")

default_resume_folder = app_cfg.get("resume", {}).get("folder", "data/resumes")
resume_folder = st.sidebar.text_input(
    "履歷資料夾路徑", value=str(APP_ROOT / default_resume_folder)
)

resume_text = ""
resume_folder_path = Path(resume_folder)
if resume_folder_path.is_dir():
    md_files = sorted(resume_folder_path.glob("*.md"))
    if md_files:
        selected_file = st.sidebar.selectbox(
            "選擇履歷檔案",
            md_files,
            format_func=lambda p: p.name,
        )
        resume_text = selected_file.read_text(encoding="utf-8")
        st.sidebar.success(f"已載入：{selected_file.name}")
    else:
        st.sidebar.warning("資料夾內沒有 .md 檔案。")
elif resume_folder:
    st.sidebar.error("找不到該資料夾，請確認路徑是否正確。")

st.sidebar.header("☁️ GCP BigQuery 設定")
bq_cfg = app_cfg.get("bigquery", {})
project_id = st.sidebar.text_input("GCP Project ID", value=bq_cfg.get("project_id", ""))
dataset_id = st.sidebar.text_input(
    "Dataset ID", value=bq_cfg.get("dataset_id", "job_data")
)
table_id = st.sidebar.text_input(
    "Table ID", value=bq_cfg.get("table_id", "104_processed_jobs")
)
bq_limit = bq_cfg.get("limit", 100)
bq_cache_ttl = bq_cfg.get("cache_ttl", 3600)

st.sidebar.header("🔑 API 金鑰")
env_key = os.environ.get("OPENAI_API_KEY", "")
if env_key:
    st.sidebar.success("OpenAI API Key 已從環境變數載入。")
else:
    manual_key = st.sidebar.text_input("OpenAI API Key", type="password")
    if manual_key:
        os.environ["OPENAI_API_KEY"] = manual_key


# Load Jobs from BigQuery
@st.cache_data(ttl=bq_cache_ttl)
def load_jobs_from_bq(proj, dt, tb, limit):
    try:
        client = bigquery.Client(project=proj)
        query = f"SELECT * FROM `{proj}.{dt}.{tb}` LIMIT {limit}"
        df = client.query(query).to_dataframe()
        return df
    except Exception as e:
        return str(e)


st.subheader("📋 職缺清單 (From BigQuery)")
if st.button("🔄 讀取/刷新職缺"):
    if project_id == "your-project-id":
        st.warning("請先在左側輸入正確的 GCP Project ID。")
    else:
        with st.spinner("從 BigQuery 讀取職缺中..."):
            df = load_jobs_from_bq(project_id, dataset_id, table_id, bq_limit)
            if isinstance(df, pd.DataFrame):
                st.session_state["jobs_df"] = df
                st.success(f"成功載入 {len(df)} 筆職缺！")
            else:
                st.error(f"讀取失敗: {df}")

if "jobs_df" in st.session_state and not st.session_state["jobs_df"].empty:
    df = st.session_state["jobs_df"]
    st.dataframe(
        df[["job_name", "company_name", "location", "salary", "need_employees"]],
        use_container_width=True,
    )

    st.divider()
    st.subheader("🤖 單筆職缺 AI 比對分析")

    # Select Job
    job_options = df["job_name"] + " - " + df["company_name"]
    selected_idx = st.selectbox(
        "選擇一個職缺來進行分析",
        range(len(job_options)),
        format_func=lambda x: job_options[x],
    )
    selected_job = df.iloc[selected_idx].to_dict()

    with st.expander("展開查看職缺詳細內容"):
        st.json(selected_job)

    if st.button("🪄 開始 AI 分析與產生自介信"):
        if not resume_text:
            st.error("請先在左側上傳履歷！")
        elif not os.environ.get("OPENAI_API_KEY"):
            st.error("請先在左側輸入 OpenAI API Key！")
        else:
            with st.spinner("AI 正在閱讀履歷與職缺，請稍候..."):
                result = evaluate_job_with_resume(resume_text, selected_job)

                if "error" in result:
                    st.error(result["error"])
                else:
                    st.session_state["last_analysis"] = result
                    chat_system_msg = app_cfg.get("chat", {}).get(
                        "system_message",
                        "You are a career advisor. You just analyzed a job and generated a cover letter. From now on, assist the user in editing the cover letter or preparing for interview for this job.",
                    )
                    st.session_state["chat_history"] = [
                        {"role": "system", "content": chat_system_msg}
                    ]

if "last_analysis" in st.session_state:
    result = st.session_state["last_analysis"]
    st.markdown(f"### 🎯 匹配程度：**{result.get('match_percentage', 0)}%**")

    col1, col2 = st.columns(2)
    with col1:
        st.success("✅ 擁有的匹配技能")
        for s in result.get("matching_skills", []):
            st.markdown(f"- {s}")
    with col2:
        st.error("⚠️ 缺少的 Gap (可以補強的地方)")
        for s in result.get("missing_skills_gap", []):
            st.markdown(f"- {s}")

    st.subheader("✉️ 推薦自介信草稿")
    st.text_area("可直接複製修改：", value=result.get("cover_letter", ""), height=300)

    # Chat interface for iteration
    st.divider()
    st.subheader("💬 與 AI 討論 (面試準備 / 修改自介信)")

    for msg in st.session_state.get("chat_history", [])[1:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(
        "請輸入你想討論的內容... 例如：請幫我把語氣改得更自信一點"
    ):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("AI 回覆中..."):
                reply = discuss_with_llm(st.session_state.chat_history)
                st.markdown(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
