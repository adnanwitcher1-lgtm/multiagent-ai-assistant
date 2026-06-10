import re
import asyncio
from functools import lru_cache
from langchain_community.llms import Ollama

# ── Model factory (cached so we don't recreate on every call) ──────────────────
@lru_cache(maxsize=1)
def _get_llm() -> Ollama:
    return Ollama(
        model="tinyllama",
        temperature=0.5,
        num_predict=256,   # reduced: planner/reviewer rarely need more
        num_ctx=512,       # reduced: keeps KV-cache small → faster prefill
        num_thread=4,      # explicit thread count (tune to your CPU cores)
        repeat_penalty=1.1,# discourages repetition → shorter outputs
        top_k=20,          # narrow sampling pool → faster token selection
        base_url="http://localhost:11434",
    )

def strip_markdown_fences(text: str) -> str:
    text = re.sub(r'^```\w*\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n```$', '', text.strip(), flags=re.MULTILINE)
    return text.strip()

# ── Shared async wrapper so llm.invoke() doesn't block the event loop ─────────
async def _invoke(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_llm().invoke, prompt)

# ── Agents ────────────────────────────────────────────────────────────────────
async def planner_agent(prompt: str) -> str:
    system_prompt = (
        "You are an expert software architect. "
        "Produce a numbered step-by-step implementation plan. "
        "Be specific about data structures, algorithms, and file layout. "
        "No code — only the plan. Max 100 words."  # tighter word budget
    )
    response = await _invoke(f"{system_prompt}\n\nTask: {prompt}")
    return strip_markdown_fences(response)

async def coder_agent(prompt: str, plan: str) -> str:
    system_prompt = (
        "You are a senior engineer. "
        "Write complete production-quality code with imports, error handling, "
        "and docstrings. Return ONLY raw code."
    )
    response = await _invoke(
        f"{system_prompt}\n\nTask: {prompt}\n\nPlan:\n{plan}\n\nCode:"
    )
    return strip_markdown_fences(response)

async def reviewer_agent(prompt: str, plan: str, code: str) -> str:
    system_prompt = (
        "You are a meticulous code reviewer. "
        "Fix bugs, edge cases, and security flaws. "
        "Return ONLY the final corrected code."
    )
    response = await _invoke(
        f"{system_prompt}\n\nTask: {prompt}\n\nPlan:\n{plan}\n\nCode:\n{code}\n\nFixed code:"
    )
    return strip_markdown_fences(response)