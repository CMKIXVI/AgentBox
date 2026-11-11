# Extracted from: 2025/Build agentic platform.md
# Preserved as a research reference; not production-ready.
# Its tool implementations are in tools.py and require security redesign.

import time
import json
from typing import Tuple
from .tools import http_tool, safe_eval_tool, llm_call

class AgentExecutor:
    def __init__(self, task_id: str, prompt: str, max_steps: int, allowed_tools: list):
        self.task_id = task_id
        self.prompt = prompt
        self.max_steps = max_steps
        self.allowed_tools = allowed_tools
        self.logs = []

    def run(self) -> Tuple[str, str]:
        context = {"history": []}
        for step in range(1, self.max_steps + 1):
            prompt = self._build_prompt(step, context)
            self.logs.append(f"STEP {step} - PROMPT:\n{prompt}")
            response = llm_call(prompt)
            self.logs.append(f"LLM RESP:\n{response}")

            try:
                parsed = json.loads(response)
            except Exception:
                self.logs.append("LLM response not JSON; treating as final answer.")
                return response, "\n".join(self.logs)

            action = parsed.get("action")
            if action == "final_answer":
                return parsed.get("answer", ""), "\n".join(self.logs)

            if action == "http_get" and "http" in self.allowed_tools:
                url = parsed.get("args", {}).get("url")
                out = http_tool(url)
                context["history"].append({"action": action, "output": out})
                self.logs.append(f"HTTP GET {url} -> {out[:200]}")
            elif action == "run_code" and "run_code" in self.allowed_tools:
                code = parsed.get("args", {}).get("code")
                out = safe_eval_tool(code)
                context["history"].append({"action": action, "output": out})
                self.logs.append(f"RUN_CODE -> {out}")
            else:
                self.logs.append(f"Unknown or disallowed action: {action}")
                return "Error: unknown or disallowed action", "\n".join(self.logs)

            time.sleep(0.2)

        return "Max steps reached without final answer", "\n".join(self.logs)

    def _build_prompt(self, step, context):
        ctx = json.dumps(context, indent=2)
        return f"""
You are an agent. Task prompt:
{self.prompt}

Tools allowed: {self.allowed_tools}

Context:
{ctx}

Instruction: At this step produce exact JSON with either:
{{"action":"final_answer","answer":"..."}}
or
{{"action":"http_get","args":{{"url":"https://..."}}}}
or
{{"action":"run_code","args":{{"code":"print(2+2)"}}}}
Respond ONLY with JSON.
"""
