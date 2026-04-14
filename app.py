import streamlit as st
import pandas as pd
from google.cloud import bigquery
import os
import sys
from pathlib import Path

# Add scripts dir to path to import llm_matcher
sys.path.append(str(Path(__file__).parent / "scripts"))
from llm_matcher import evaluate_job_with_resume, discuss_with_llm

st.set_page_config(page_title="104 Job Matcher AI", page_icon="💼", layout="wide")

st.title("💼 AI 面試助手: Data Engineer 職缺掃描與比對系統")

# Sidebar Configuration
st.sidebar.header("📁 履歷與設定")
uploaded_resume = st.sidebar.file_uploader("上傳你的履歷 (Markdown/TXT)", type=["txt", "md"])
resume_text = ""
if uploaded_resume:
    resume_text = uploaded_resume.read().decode("utf-8")
    st.sidebar.success("履歷載入成功！")

st.sidebar.header("☁️ GCP BigQuery 設定")
project_id = st.sidebar.text_input("GCP Project ID", value="your-project-id")
dataset_id = st.sidebar.text_input("Dataset ID", value="job_data")
table_id = st.sidebar.text_input("Table ID", value="104_processed_jobs")

openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if openai_api_key:
    os.environ["OPENAI_API_KEY"] = openai_api_key

# Load Jobs from BigQuery
@st.cache_data(ttl=3600)
def load_jobs_from_bq(proj, dt, tb):
    try:
        client = bigquery.Client(project=proj)
        query = f"SELECT * FROM `{proj}.{dt}.{tb}` LIMIT 100"
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
            df = load_jobs_from_bq(project_id, dataset_id, table_id)
            if isinstance(df, pd.DataFrame):
                st.session_state["jobs_df"] = df
                st.success(f"成功載入 {len(df)} 筆職缺！")
            else:
                st.error(f"讀取失敗: {df}")

if "jobs_df" in st.session_state and not st.session_state["jobs_df"].empty:
    df = st.session_state["jobs_df"]
    st.dataframe(df[["job_name", "company_name", "location", "salary", "need_employees"]], use_container_width=True)
    
    st.divider()
    st.subheader("🤖 單筆職缺 AI 比對分析")
    
    # Select Job
    job_options = df["job_name"] + " - " + df["company_name"]
    selected_idx = st.selectbox("選擇一個職缺來進行分析", range(len(job_options)), format_func=lambda x: job_options[x])
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
                    st.session_state["chat_history"] = [
                        {"role": "system", "content": "You are a career advisor. You just analyzed a job and generated a cover letter. From now on, assist the user in editing the cover letter or preparing for interview for this job."}
                    ]
                    
if "last_analysis" in st.session_state:
    result = st.session_state["last_analysis"]
    st.markdown(f"### 🎯 匹配程度：**{result.get('match_percentage', 0)}%**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.success("✅ 擁有的匹配技能")
        for s in result.get('matching_skills', []):
            st.markdown(f"- {s}")
    with col2:
        st.error("⚠️ 缺少的 Gap (可以補強的地方)")
        for s in result.get('missing_skills_gap', []):
            st.markdown(f"- {s}")
            
    st.subheader("✉️ 推薦自介信草稿")
    st.text_area("可直接複製修改：", value=result.get('cover_letter', ''), height=300)
    
    # Chat interface for iteration
    st.divider()
    st.subheader("💬 與 AI 討論 (面試準備 / 修改自介信)")
    
    for msg in st.session_state.get("chat_history", [])[1:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("請輸入你想討論的內容... 例如：請幫我把語氣改得更自信一點"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("AI 回覆中..."):
                reply = discuss_with_llm(st.session_state.chat_history)
                st.markdown(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
