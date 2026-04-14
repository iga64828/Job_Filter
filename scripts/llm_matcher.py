import json
import os
from pathlib import Path
import yaml
from openai import OpenAI

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "llm.yaml"

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_openai_client(api_url: str = None):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it to use the LLM matcher.")
        
    kwargs = {"api_key": api_key}
    if api_url and api_url != "https://api.openai.com/v1":
        kwargs["base_url"] = api_url
        
    return OpenAI(**kwargs)

def evaluate_job_with_resume(resume_text: str, job_info: dict) -> dict:
    """
    Use OpenAI API to evaluate a job against a user's resume, calculate match score,
    identify missing skills gaps, and write a customized cover letter.
    """
    config_dt = load_config().get("llm", {})
    api_url = config_dt.get("api_url", "https://api.openai.com/v1")
    model = config_dt.get("model", "gpt-4o-mini")
    temperature = config_dt.get("temperature", 0.7)
    system_msg = config_dt.get("system_message", "You are a helpful AI assistant that outputs carefully structured JSON in Traditional Chinese format.")
    
    prompt_template = config_dt.get("prompt_template", "")
    if not prompt_template:
        raise ValueError("No prompt_template found in llm.yaml")
        
    client = get_openai_client(api_url)
    
    prompt = prompt_template.format(
        resume_text=resume_text,
        job_name=job_info.get('job_name', ''),
        company_name=job_info.get('company_name', ''),
        job_description=job_info.get('job_description', ''),
        work_skills=job_info.get('work_skills', ''),
        familiar_tools=job_info.get('familiar_tools', ''),
        education_requirement=job_info.get('education_requirement', ''),
        work_experience=job_info.get('work_experience', ''),
        other_conditions=job_info.get('other_conditions', '')
    )
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" },
        temperature=temperature,
    )
    
    content = response.choices[0].message.content
    try:
        result = json.loads(content)
        return result
    except json.JSONDecodeError:
        return {"error": "Failed to parse LLM output as JSON."}

def discuss_with_llm(messages: list) -> str:
    """
    Chat interface helper to continue interacting with the LLM.
    `messages` should be a list of dicts: [{"role": "system"/"user"/"assistant", "content": ...}]
    """
    config_dt = load_config().get("llm", {})
    api_url = config_dt.get("api_url", "https://api.openai.com/v1")
    chat_model = config_dt.get("chat_model", "gpt-4o")
    temperature = config_dt.get("temperature", 0.7)
    
    client = get_openai_client(api_url)
    response = client.chat.completions.create(
        model=chat_model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content
