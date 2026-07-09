#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any, Dict

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test an OpenAI-compatible vLLM endpoint before running Anirvium benchmarks.")
    parser.add_argument("--base-url", default=os.getenv("LLM_BASE_URL", "http://localhost:8001/v1"))
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", "anirvium-text"))
    parser.add_argument("--api-key", default=os.getenv("LLM_API_KEY", "dummy"))
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def request(client: httpx.Client, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
    response = client.request(method, url, **kwargs)
    response.raise_for_status()
    return response.json()


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {args.api_key}"}
    started = time.perf_counter()

    with httpx.Client(timeout=args.timeout, headers=headers) as client:
        models = request(client, "GET", f"{base_url}/models")
        completion = request(
            client,
            "POST",
            f"{base_url}/chat/completions",
            json={
                "model": args.model,
                "messages": [
                    {"role": "system", "content": "You are a concise readiness test."},
                    {"role": "user", "content": "Reply with exactly: anirvium-ready"},
                ],
                "temperature": 0,
                "max_tokens": 16,
            },
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    content = completion["choices"][0]["message"]["content"].strip()
    report = {
        "status": "ok",
        "base_url": base_url,
        "model": args.model,
        "elapsed_ms": elapsed_ms,
        "model_count": len(models.get("data", [])),
        "response": content,
        "usage": completion.get("usage", {}),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
