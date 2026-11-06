"""LLM adapter (T4): the language model behind the agents, configured only in .env and therefore exchangeable.

  AGENT_API_KEY      key of the provider (never committed)
  AGENT_PROVIDER     openai | anthropic | azure | gemini | compatible  (empty = detected from the key)
  AGENT_MODEL        model / deployment name (anthropic: default claude-sonnet-5-5)
  AGENT_BASE_URL     only for azure (endpoint) or compatible (any OpenAI-compatible server)
  AGENT_API_VERSION  only for azure
  (the older AZURE_OPENAI_ENDPOINT/_API_KEY/_DEPLOYMENT/_API_VERSION still work)

All providers are called through the OpenAI SDK (their OpenAI-compatible endpoints) with function calling.
The model only chooses tools, parameters and templates (product principle "no AI hallucinations"); it never
produces a number that is shown or stored. Every call is logged in ops.llm_call (model, deployment, purpose,
token counts, duration) for the protocol and MODELLE.md. Without configuration the agents run in the offline
mode: a deterministic German intent parser (statagent/agents/intent.py) – labelled as such in the UI.
"""
import json
import os
import time

from statagent.config import connect

BASE_URLS = {"anthropic": "https://api.anthropic.com/v1/", "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/"}
DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5"}
LABELS = {"openai": "OpenAI", "anthropic": "Anthropic", "azure": "Azure OpenAI", "gemini": "Google Gemini", "compatible": "OpenAI-kompatibel"}


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def llm_config() -> dict:
    key = _env("AGENT_API_KEY")
    if not key and _env("AZURE_OPENAI_API_KEY"):                  # older configuration
        return {"provider": "azure", "api_key": _env("AZURE_OPENAI_API_KEY"), "model": _env("AZURE_OPENAI_DEPLOYMENT"),
                "base_url": _env("AZURE_OPENAI_ENDPOINT"), "api_version": _env("AZURE_OPENAI_API_VERSION")}
    provider = _env("AGENT_PROVIDER").lower()
    if not provider and key:
        provider = ("anthropic" if key.startswith("sk-ant-") else "gemini" if key.startswith("AIza")
                    else "compatible" if _env("AGENT_BASE_URL") else "openai")
    return {"provider": provider, "api_key": key, "model": _env("AGENT_MODEL") or DEFAULT_MODELS.get(provider, ""),
            "base_url": _env("AGENT_BASE_URL") or BASE_URLS.get(provider, ""), "api_version": _env("AGENT_API_VERSION")}


def _missing(c: dict) -> list[str]:
    miss = [] if c["api_key"] else ["AGENT_API_KEY"]
    if not c["model"]:
        miss.append("AGENT_MODEL")
    if c["provider"] in ("azure", "compatible") and not c["base_url"]:
        miss.append("AGENT_BASE_URL")
    return miss


def llm_status() -> dict:
    c = llm_config()
    configured = bool(c["api_key"]) and not _missing(c)
    host = c["base_url"].split("//")[-1].split("/")[0] if c["base_url"] else ("api.openai.com" if c["provider"] == "openai" else None)
    label = LABELS.get(c["provider"], c["provider"] or "–")
    return {"configured": configured, "provider": label if configured else None, "model": c["model"] or None,
            "deployment": c["model"] or None, "api_version": c["api_version"] or None, "endpoint_host": host,
            "missing": _missing(c) if c["api_key"] else [],
            "mode": "llm" if configured else "offline",
            "mode_label": f"Agent · {label} · {c['model']}" if configured else "Offline-Modus (regelbasierte Absichtserkennung, kein Sprachmodell)"}


class LLMUnavailable(RuntimeError):
    pass


def _client():
    c = llm_config()
    if not c["api_key"] or _missing(c):
        raise LLMUnavailable("Kein Sprachmodell konfiguriert (AGENT_API_KEY / AGENT_MODEL in .env)")
    if c["provider"] == "azure":
        from openai import AzureOpenAI
        return AzureOpenAI(azure_endpoint=c["base_url"], api_key=c["api_key"], api_version=c["api_version"] or "2024-10-21",
                           timeout=60, max_retries=1), c
    from openai import OpenAI
    return OpenAI(api_key=c["api_key"], base_url=c["base_url"] or None, timeout=60, max_retries=1), c


def chat(messages: list[dict], tools: list[dict] | None = None, purpose: str = "", tool_choice="auto",
         response_format: dict | None = None) -> dict:
    """One chat completion. Returns {"content", "tool_calls": [{name, arguments}], "model"}; logs the call."""
    client, c = _client()
    deployment = c["model"]
    started = time.time()
    kwargs = {"model": deployment, "messages": messages}
    if tools:
        kwargs |= {"tools": tools, "tool_choice": tool_choice}
    if response_format:
        kwargs["response_format"] = response_format
    if c["provider"] == "anthropic":
        kwargs["max_tokens"] = 2048
    error = None
    try:
        try:
            resp = client.chat.completions.create(**kwargs)
        except Exception as exc:
            # some models refuse forced tool use ("required"/a named tool) – retry once with "auto"; the prompt asks for one tool
            if tools and tool_choice != "auto" and "tool_choice" in str(exc):
                _log(deployment, None, purpose, None, None, time.time() - started, f"retry with tool_choice=auto: {str(exc)[:300]}")
                kwargs["tool_choice"] = "auto"
                resp = client.chat.completions.create(**kwargs)
            else:
                raise
    except Exception as exc:
        error = str(exc)[:500]
        _log(deployment, None, purpose, None, None, time.time() - started, error)
        raise LLMUnavailable(f"Modellaufruf fehlgeschlagen ({LABELS.get(c['provider'], c['provider'])}): {error}") from exc
    msg = resp.choices[0].message
    calls = []
    for tc in msg.tool_calls or []:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})
    usage = getattr(resp, "usage", None)
    _log(deployment, resp.model, purpose, getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None),
         time.time() - started, None)
    return {"content": msg.content or "", "tool_calls": calls, "model": resp.model or deployment, "deployment": deployment}


def _log(deployment, model, purpose, tokens_in, tokens_out, seconds, error):
    try:
        with connect() as conn:
            conn.execute("""INSERT INTO ops.llm_call (deployment, model, purpose, tokens_in, tokens_out, seconds, error)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)""", (deployment, model, purpose[:200], tokens_in, tokens_out,
                                                                     round(seconds, 2), error))
    except Exception:
        pass  # logging must never break an answer; the answer log (ops.answer) records the model too
