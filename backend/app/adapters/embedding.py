"""EmbeddingAdapter：默认 bge-m3。

优先 HTTP 端点（OpenAI 兼容 /embeddings）；未配置端点时用本地 transformers 加载 BAAI/bge-m3。
缺配置且无法本地加载时，明确失败，不返回伪造向量。
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Sequence

import httpx


class EmbeddingNotConfigured(RuntimeError):
    pass


class EmbeddingAdapter:
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        backend: str | None = None,
    ) -> None:
        self.endpoint = (endpoint if endpoint is not None else os.getenv("EMBEDDING_ENDPOINT", "")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("EMBEDDING_API_KEY", "")
        self.model = model or os.getenv("EMBEDDING_MODEL", "bge-m3")
        self.backend = (backend or os.getenv("EMBEDDING_BACKEND", "auto")).lower()
        self._tokenizer = None
        self._model = None
        self._device = os.getenv("EMBEDDING_DEVICE", "cpu")

    @property
    def model_id(self) -> str:
        if self.endpoint and self.backend != "local":
            return f"http:{self.model}"
        local_name = os.getenv("EMBEDDING_LOCAL_MODEL", "BAAI/bge-m3")
        if self.model in ("bge-m3", "BAAI/bge-m3"):
            return f"local:{local_name}"
        return f"local:{self.model}"

    def available(self) -> bool:
        if self.backend == "http":
            return bool(self.endpoint)
        return True

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        use_http = bool(self.endpoint) and self.backend != "local"
        if use_http:
            return self._embed_http(list(texts))
        if self.backend in ("local", "auto"):
            return self._embed_local(list(texts))
        raise EmbeddingNotConfigured(
            "未配置 EMBEDDING_ENDPOINT，且 EMBEDDING_BACKEND 不允许本地模型；无法生成向量"
        )

    def _embed_http(self, texts: list[str]) -> list[list[float]]:
        url = self.endpoint if self.endpoint.endswith("/embeddings") else f"{self.endpoint}/embeddings"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": self.model, "input": texts}
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"嵌入服务调用失败: {exc}") from exc
        items = data.get("data")
        if not isinstance(items, list) or len(items) != len(texts):
            raise RuntimeError("嵌入服务返回格式异常或条数不匹配")
        vectors: list[list[float]] = []
        for item in sorted(items, key=lambda x: x.get("index", 0)):
            vec = item.get("embedding")
            if not isinstance(vec, list) or not vec:
                raise RuntimeError("嵌入服务返回空向量")
            vectors.append([float(x) for x in vec])
        return vectors

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        tokenizer, model = self._load_local()
        import torch

        # bge 系列常用 CLS 池化 + L2 归一化
        encoded = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=int(os.getenv("EMBEDDING_MAX_LENGTH", "512")),
            return_tensors="pt",
        )
        encoded = {k: v.to(self._device) for k, v in encoded.items()}
        with torch.no_grad():
            out = model(**encoded)
            # CLS
            emb = out.last_hidden_state[:, 0]
            emb = torch.nn.functional.normalize(emb, p=2, dim=1)
        return [row.detach().cpu().tolist() for row in emb]

    def _load_local(self):
        if self._model is not None and self._tokenizer is not None:
            return self._tokenizer, self._model
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise EmbeddingNotConfigured(
                "本地嵌入需要安装 transformers 与 torch；或配置 EMBEDDING_ENDPOINT"
            ) from exc

        name = os.getenv("EMBEDDING_LOCAL_MODEL", "BAAI/bge-m3")
        if self.model and "/" in self.model:
            name = self.model
        local_only = os.getenv("EMBEDDING_LOCAL_FILES_ONLY", "0") in ("1", "true", "True")
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(name, local_files_only=local_only)
            self._model = AutoModel.from_pretrained(name, local_files_only=local_only)
        except Exception:
            # 网络不稳时优先用本地缓存
            self._tokenizer = AutoTokenizer.from_pretrained(name, local_files_only=True)
            self._model = AutoModel.from_pretrained(name, local_files_only=True)
        self._model.to(self._device)
        self._model.eval()
        return self._tokenizer, self._model


@lru_cache(maxsize=1)
def get_embedding_adapter() -> EmbeddingAdapter:
    return EmbeddingAdapter()
