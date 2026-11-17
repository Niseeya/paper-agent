"""ChatModelAdapter：OpenAI 兼容对话接口。

配置来自管理端 ModelConfig（经 llm_settings.build_chat_adapter），不在此写死密钥与端点。
"""

from __future__ import annotations

import httpx


class ChatNotConfigured(RuntimeError):
    pass


class ChatModelAdapter:
    def __init__(
        self,
        *,
        endpoint: str = "",
        api_key: str = "",
        model: str = "",
    ) -> None:
        self.endpoint = (endpoint or "").rstrip("/")
        self.api_key = api_key or ""
        self.model = model or ""

    @property
    def model_id(self) -> str:
        return f"http:{self.model}" if self.model else "unconfigured"

    def available(self) -> bool:
        return bool(self.endpoint and self.model and self.api_key)

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.2, max_tokens: int = 1200) -> str:
        if not self.available():
            raise ChatNotConfigured("未配置对话模型（请在管理后台填写 endpoint / model / API Key）")
        url = self.endpoint if self.endpoint.endswith("/chat/completions") else f"{self.endpoint}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"对话模型返回格式异常: {exc}") from exc


def get_chat_adapter() -> ChatModelAdapter:
    """从数据库读取当前启用的对话模型配置。"""
    from backend.app.services.llm_settings import build_chat_adapter

    return build_chat_adapter()
