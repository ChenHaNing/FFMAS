import requests

from src.llm_client import LLMClient


def test_llm_client_retries_on_timeout():
    calls = {"count": 0}

    def fake_post(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise requests.exceptions.Timeout("timeout")
        class Resp:
            def raise_for_status(self):
                return None
            def json(self):
                return {"choices": [{"message": {"content": "{\"ok\": true}"}}]}
        return Resp()

    client = LLMClient(
        provider="deepseek",
        model="deepseek-chat",
        api_key="key",
        base_url="https://api.deepseek.com",
        timeout=1,
        max_retries=3,
        post_fn=fake_post,
    )
    result = client.generate_json("sys", "user")
    assert result["ok"] is True
    assert calls["count"] == 3


def test_llm_client_supports_zhipu_anthropic_messages_endpoint():
    calls = {"url": None, "headers": None, "payload": None}

    def fake_post(url, headers=None, json=None, *_args, **_kwargs):
        calls["url"] = url
        calls["headers"] = headers or {}
        calls["payload"] = json or {}

        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "content": [
                        {"type": "thinking", "thinking": "analysis"},
                        {"type": "text", "text": "{\"ok\": true}"},
                    ]
                }

        return Resp()

    client = LLMClient(
        provider="zhipu",
        model="GLM-4.7",
        api_key="zhipu-key",
        base_url="https://open.bigmodel.cn/api/coding/paas/v4",
        timeout=1,
        max_retries=1,
        post_fn=fake_post,
    )
    result = client.generate_json("sys", "user")
    assert result["ok"] is True
    assert calls["url"] == "https://open.bigmodel.cn/api/coding/paas/v4/v1/messages"
    assert calls["headers"]["x-api-key"] == "zhipu-key"
    assert calls["headers"]["anthropic-version"] == "2023-06-01"
    assert calls["payload"]["model"] == "GLM-4.7"
    assert calls["payload"]["messages"][0]["content"][0]["type"] == "text"


def test_llm_client_supports_minimax_anthropic_messages_endpoint():
    calls = {"url": None, "headers": None, "payload": None}

    def fake_post(url, headers=None, json=None, *_args, **_kwargs):
        calls["url"] = url
        calls["headers"] = headers or {}
        calls["payload"] = json or {}

        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"content": [{"type": "text", "text": "{\"ok\": true}"}]}

        return Resp()

    client = LLMClient(
        provider="minimax",
        model="MiniMax-M2.1",
        api_key="minimax-key",
        base_url="https://api.minimaxi.com/anthropic",
        timeout=1,
        max_retries=1,
        post_fn=fake_post,
    )
    result = client.generate_json("sys", "user")
    assert result["ok"] is True
    assert calls["url"] == "https://api.minimaxi.com/anthropic/v1/messages"
    assert calls["headers"]["x-api-key"] == "minimax-key"
    assert calls["payload"]["model"] == "MiniMax-M2.1"
