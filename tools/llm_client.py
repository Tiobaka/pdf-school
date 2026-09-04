#!/usr/bin/env python3
"""
llm_client.py - Platform-agnostic LLM backend for PDF-School.
Connects to Gemini, OpenAI, Anthropic, OpenRouter, Groq, or local Ollama
using pure HTTP requests. Zero heavy vendor SDKs required.
"""

import os
import sys
from pathlib import Path

# Automatically use local virtualenv interpreter if invoked with system python
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
if _venv_python.exists() and sys.prefix != str(PROJECT_ROOT / ".venv"):
    os.execv(str(_venv_python), [str(_venv_python)] + sys.argv)


import json
import re
from typing import Any

import requests
from dotenv import load_dotenv
from rich.console import Console

# Load .env if present from project root
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()


console = Console()


def get_llm_config() -> tuple[str, str, str, str | None]:
    """
    Detects active LLM configuration from environment variables.
    Returns: (provider, api_key, model_name, base_url)
    """
    provider = os.getenv("LLM_PROVIDER", "").lower()
    model = os.getenv("LLM_MODEL", "")

    # 1. Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if provider == "gemini" or (not provider and gemini_key):
        return (
            "gemini",
            gemini_key or "",
            model or "gemini-2.5-flash",
            "https://generativelanguage.googleapis.com/v1beta/models",
        )

    # 2. OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if provider == "openai" or (not provider and openai_key and not os.getenv("OPENAI_BASE_URL")):
        return (
            "openai",
            openai_key or "",
            model or "gpt-4o-mini",
            "https://api.openai.com/v1/chat/completions",
        )

    # 3. Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if provider == "anthropic" or (not provider and anthropic_key):
        return (
            "anthropic",
            anthropic_key or "",
            model or "claude-3-5-haiku-20241022",
            "https://api.anthropic.com/v1/messages",
        )

    # 4. OpenRouter / Groq / Ollama / Custom OpenAI-Compatible
    base_url = (
        os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL") or os.getenv("OLLAMA_BASE_URL")
    )
    if base_url or provider in ["openrouter", "groq", "ollama", "custom"]:
        api_key = (
            os.getenv("OPENROUTER_API_KEY")
            or os.getenv("GROQ_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "ollama"
        )
        target_url = base_url if base_url else "http://localhost:11434/v1/chat/completions"
        if not target_url.endswith("/chat/completions"):
            target_url = target_url.rstrip("/") + "/chat/completions"
        return ("openai_compatible", api_key, model or "llama3.2", target_url)

    return ("none", "", "", None)


def clean_json_response(raw_text: str) -> dict[str, Any]:
    """
    Strips markdown code fencing and parses JSON cleanly.
    """
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    data = json.loads(text)
    return data if isinstance(data, dict) else {}


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
    provider, api_key_opt, model, base_url_opt = get_llm_config()

    if provider == "none":
        raise ValueError(
            "No LLM provider configured! Please set one of the following environment variables (or add to .env):\n"
            "  - GEMINI_API_KEY\n"
            "  - OPENAI_API_KEY\n"
            "  - ANTHROPIC_API_KEY\n"
            "  - OPENAI_BASE_URL (for Ollama, vLLM, OpenRouter, Groq)"
        )

    api_key: str = api_key_opt or ""
    base_url: str = base_url_opt or ""
    headers: dict[str, str] = {}
    timeout_secs = 60

    if provider == "gemini":
        url = f"{base_url}/{model}:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "contents": [
                {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}
            ],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_secs)
        resp.raise_for_status()
        data = resp.json()
        return str(data["candidates"][0]["content"]["parts"][0]["text"])

    elif provider == "anthropic":
        url = base_url
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": 4096,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_secs)
        resp.raise_for_status()
        data = resp.json()
        return str(data["content"][0]["text"])

    elif provider in ["openai", "openai_compatible"]:
        url = base_url
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_secs)
        resp.raise_for_status()
        data = resp.json()
        return str(data["choices"][0]["message"]["content"])

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def generate_structured_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    raw_response = call_llm(system_prompt, user_prompt)
    return clean_json_response(raw_response)


def main():
    provider, api_key, model, base_url = get_llm_config()
    console.print("[bold cyan]PDF-School Platform-Agnostic LLM Client[/bold cyan]")
    console.print(f"  • Provider: [bold]{provider}[/bold]")
    console.print(f"  • Model:    [bold]{model}[/bold]")
    console.print(f"  • Base URL: [dim]{base_url}[/dim]")
    console.print(f"  • Key set:  {'[green]Yes[/green]' if api_key else '[red]No[/red]'}")

    if provider == "none":
        console.print(
            "\n[yellow]To enable automatic question forging without an IDE agent, create a .env file:[/yellow]"
        )
        console.print("  echo 'GEMINI_API_KEY=your_key_here' > .env")
        console.print("  # or: OPENAI_API_KEY=sk-...")
        console.print("  # or: ANTHROPIC_API_KEY=sk-ant-...")
        console.print("  # or: OPENAI_BASE_URL=http://localhost:11434/v1 (for local Ollama)")
    else:
        console.print("\n[green]✔ Backend ready for automated question generation.[/green]")


if __name__ == "__main__":
    main()
