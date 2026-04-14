#!/usr/bin/env python3
"""Multi-model query wrapper for /multi-plan and /multi-execute.

Calls Gemini or OpenAI APIs and returns structured JSON responses.
Uses only Python stdlib (no pip dependencies required).

Usage:
    python scripts/multi-model-query.py --model gemini --prompt "Analyze this architecture..."
    python scripts/multi-model-query.py --model openai --prompt "Suggest implementation..." --role "You are a backend expert"
    python scripts/multi-model-query.py --check  # Verify which API keys are configured

Environment variables:
    GOOGLE_AI_KEY   - Google AI Studio API key for Gemini
    OPENAI_API_KEY  - OpenAI API key for GPT models

Returns JSON:
    {"model": "gemini-2.0-flash", "available": true, "response": "..."}
    {"model": "gemini-2.0-flash", "available": false, "error": "GOOGLE_AI_KEY not set"}
"""

import argparse
import json
import os
import urllib.error
import urllib.request


def query_gemini(prompt: str, role: str = "", model: str = "gemini-2.0-flash") -> dict:
    """Query Google Gemini API."""
    key = os.environ.get("GOOGLE_AI_KEY", "")
    if not key:
        return {"model": model, "available": False, "error": "GOOGLE_AI_KEY not set"}

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )

    # Build content parts
    contents = []
    if role:
        contents.append({"role": "user", "parts": [{"text": role}]})
        contents.append({"role": "model", "parts": [{"text": "Understood. I'll follow that role."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = json.dumps({"contents": contents}).encode()

    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )

    try:
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return {"model": model, "available": True, "response": text}
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        return {"model": model, "available": False, "error": f"HTTP {e.code}: {body}"}
    except urllib.error.URLError as e:
        return {"model": model, "available": False, "error": f"Connection error: {e.reason}"}
    except (KeyError, IndexError) as e:
        return {"model": model, "available": False, "error": f"Unexpected response format: {e}"}
    except Exception as e:
        return {"model": model, "available": False, "error": str(e)}


def query_openai(prompt: str, role: str = "", model: str = "gpt-4o") -> dict:
    """Query OpenAI API."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return {"model": model, "available": False, "error": "OPENAI_API_KEY not set"}

    url = "https://api.openai.com/v1/chat/completions"

    messages = []
    if role:
        messages.append({"role": "system", "content": role})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({"model": model, "messages": messages}).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )

    try:
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())
        text = result["choices"][0]["message"]["content"]
        return {"model": model, "available": True, "response": text}
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        return {"model": model, "available": False, "error": f"HTTP {e.code}: {body}"}
    except urllib.error.URLError as e:
        return {"model": model, "available": False, "error": f"Connection error: {e.reason}"}
    except (KeyError, IndexError) as e:
        return {"model": model, "available": False, "error": f"Unexpected response format: {e}"}
    except Exception as e:
        return {"model": model, "available": False, "error": str(e)}


def check_keys() -> dict:
    """Check which API keys are configured."""
    return {
        "gemini": {
            "configured": bool(os.environ.get("GOOGLE_AI_KEY")),
            "env_var": "GOOGLE_AI_KEY",
        },
        "openai": {
            "configured": bool(os.environ.get("OPENAI_API_KEY")),
            "env_var": "OPENAI_API_KEY",
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Query external AI models")
    parser.add_argument(
        "--model",
        choices=["gemini", "openai"],
        help="Which model to query",
    )
    parser.add_argument("--prompt", help="The prompt to send")
    parser.add_argument(
        "--role", default="", help="System/role prompt (optional)"
    )
    parser.add_argument(
        "--gemini-model",
        default="gemini-2.0-flash",
        help="Gemini model ID (default: gemini-2.0-flash)",
    )
    parser.add_argument(
        "--openai-model",
        default="gpt-4o",
        help="OpenAI model ID (default: gpt-4o)",
    )
    parser.add_argument(
        "--check", action="store_true", help="Check API key availability"
    )

    args = parser.parse_args()

    if args.check:
        print(json.dumps(check_keys(), indent=2))
        return

    if not args.model or not args.prompt:
        parser.error("--model and --prompt are required (unless using --check)")

    if args.model == "gemini":
        result = query_gemini(args.prompt, args.role, args.gemini_model)
    elif args.model == "openai":
        result = query_openai(args.prompt, args.role, args.openai_model)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
