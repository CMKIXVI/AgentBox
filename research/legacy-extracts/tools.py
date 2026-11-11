# Extracted from: 2025/Build agentic platform.md
# Preserved verbatim in substance as a research reference.
# WARNING: safe_eval_tool executes arbitrary Python. Do not expose or use it
# with untrusted agent output. A subprocess timeout is not a sandbox.

import httpx, subprocess, os
from dotenv import load_dotenv
load_dotenv()

import openai
openai.api_key = os.getenv("OPENAI_API_KEY")

def llm_call(prompt: str) -> str:
    resp = openai.Completion.create(
        model="gpt-4o-mini",
        prompt=prompt,
        max_tokens=512,
        temperature=0.2
    )
    return resp.choices[0].text.strip()

def http_tool(url: str) -> str:
    try:
        r = httpx.get(url, timeout=10.0)
        return f"status:{r.status_code}\n{r.text[:2000]}"
    except Exception as e:
        return f"HTTP error: {str(e)}"

def safe_eval_tool(code: str) -> str:
    # Source comment warns this is limited and recommends proper sandboxing.
    try:
        proc = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=5
        )
        return proc.stdout + proc.stderr
    except Exception as e:
        return f"Error running code: {str(e)}"
