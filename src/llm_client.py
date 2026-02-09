import json
import time
from typing import Any, Dict, List, Optional, Callable
import requests


class LLMClient:
    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
        base_url: str,
        timeout: int = 60,
        max_retries: int = 2,
        post_fn: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._post = post_fn or requests.post

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        provider = self.provider.lower().strip()
        if provider == "deepseek":
            return self._openai_chat_completion(
                endpoint_path="/v1/chat/completions",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema,
                temperature=temperature,
            )
        if provider in {"zhipu", "glm", "bigmodel", "minimax", "anthropic"}:
            return self._anthropic_messages(
                endpoint_path="/v1/messages",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema,
                temperature=temperature,
            )
        raise ValueError(f"Unsupported provider: {self.provider}")

    def _openai_chat_completion(
        self,
        endpoint_path: str,
        system_prompt: str,
        user_prompt: str,
        schema: Optional[Dict[str, Any]],
        temperature: float,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint_path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        schema_hint = ""
        if schema:
            schema_hint = (
                "\n\nReturn JSON only that matches this schema (no markdown):\n"
                + json.dumps(schema, ensure_ascii=False)
            )
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt + schema_hint},
            ],
        }
        data = self._post_with_retry(url, headers, payload)
        content = data["choices"][0]["message"]["content"]
        return _safe_json_parse(content)

    def _anthropic_messages(
        self,
        endpoint_path: str,
        system_prompt: str,
        user_prompt: str,
        schema: Optional[Dict[str, Any]],
        temperature: float,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint_path}"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        schema_hint = ""
        if schema:
            schema_hint = (
                "\n\nReturn JSON only that matches this schema (no markdown):\n"
                + json.dumps(schema, ensure_ascii=False)
            )
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt + schema_hint,
                        }
                    ],
                }
            ],
        }
        data = self._post_with_retry(url, headers, payload)
        content = _extract_anthropic_text(data)
        return _safe_json_parse(content)

    def _post_with_retry(self, url: str, headers: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = None
        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._post(url, headers=headers, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                last_err = exc
                time.sleep(min(2 ** attempt, 4))
        if resp is None:
            raise last_err
        raise RuntimeError("LLM request failed without response payload")


def _extract_anthropic_text(data: Dict[str, Any]) -> str:
    content = data.get("content")
    if isinstance(content, list):
        blocks: List[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "text":
                continue
            text = str(block.get("text", "")).strip()
            if text:
                blocks.append(text)
        if blocks:
            return "\n".join(blocks)
    if isinstance(content, str) and content.strip():
        return content

    # Fallback for non-standard gateways that still use OpenAI-like shape.
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        text = str(message.get("content", "")).strip()
        if text:
            return text
    raise KeyError("No textual content found in Anthropic-style response")


def _safe_json_parse(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])
