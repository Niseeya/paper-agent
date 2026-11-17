"""RerankerAdapter：混合检索后必须调用。

优先 HTTP；否则本地 transformers Cross-Encoder（默认 BAAI/bge-reranker-v2-m3）。
未配置且本地不可用时明确失败。
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Sequence

import httpx


class RerankerNotConfigured(RuntimeError):
    pass


class RerankerAdapter:
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        backend: str | None = None,
    ) -> None:
        self.endpoint = (endpoint if endpoint is not None else os.getenv("RERANKER_ENDPOINT", "")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("RERANKER_API_KEY", "")
        self.model = model or os.getenv("RERANKER_MODEL", "bge-reranker-v2-m3")
        self.backend = (backend or os.getenv("RERANKER_BACKEND", "auto")).lower()
        self._tokenizer = None
        self._model = None
        self._device = os.getenv("RERANKER_DEVICE", os.getenv("EMBEDDING_DEVICE", "cpu"))

    @property
    def model_id(self) -> str:
        if self.endpoint and self.backend != "local":
            return f"http:{self.model}"
        local_name = os.getenv("RERANKER_LOCAL_MODEL", "BAAI/bge-reranker-v2-m3")
        if self.model in ("bge-reranker-v2-m3", "BAAI/bge-reranker-v2-m3"):
            return f"local:{local_name}"
        return f"local:{self.model}"

    def rerank(self, query: str, documents: Sequence[str], top_k: int | None = None) -> list[tuple[int, float]]:
        if not documents:
            return []
        use_http = bool(self.endpoint) and self.backend != "local"
        if use_http:
            ranked = self._rerank_http(query, list(documents))
        elif self.backend in ("local", "auto"):
            ranked = self._rerank_local(query, list(documents))
        else:
            raise RerankerNotConfigured(
                "未配置 RERANKER_ENDPOINT，且 RERANKER_BACKEND 不允许本地模型；混合检索后无法重排序"
            )
        if top_k is not None:
            ranked = ranked[:top_k]
        return ranked

    def _rerank_http(self, query: str, documents: list[str]) -> list[tuple[int, float]]:
        url = self.endpoint if self.endpoint.endswith("/rerank") else f"{self.endpoint}/rerank"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": self.model, "query": query, "documents": documents}
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"重排序服务调用失败: {exc}") from exc
        results = data.get("results") or data.get("data") or []
        out: list[tuple[int, float]] = []
        for item in results:
            idx = int(item.get("index", item.get("corpus_id", -1)))
            score = float(item.get("relevance_score", item.get("score", 0.0)))
            if idx >= 0:
                out.append((idx, score))
        if not out:
            raise RuntimeError("重排序服务未返回有效结果")
        out.sort(key=lambda x: x[1], reverse=True)
        return out

    def _rerank_local(self, query: str, documents: list[str]) -> list[tuple[int, float]]:
        tokenizer, model = self._load_local()
        import torch

        pairs = [(query, d) for d in documents]
        scores: list[float] = []
        batch_size = int(os.getenv("RERANKER_BATCH_SIZE", "8"))
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i : i + batch_size]
            encoded = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=int(os.getenv("RERANKER_MAX_LENGTH", "512")),
                return_tensors="pt",
            )
            encoded = {k: v.to(self._device) for k, v in encoded.items()}
            with torch.no_grad():
                logits = model(**encoded, return_dict=True).logits
                # 二分类取正类，或回归分数
                if logits.shape[-1] == 1:
                    batch_scores = logits.squeeze(-1)
                else:
                    batch_scores = logits[:, 1]
                scores.extend(float(x) for x in batch_scores.detach().cpu())
        return sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

    def _load_local(self):
        if self._model is not None and self._tokenizer is not None:
            return self._tokenizer, self._model
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise RerankerNotConfigured(
                "本地重排序需要安装 transformers 与 torch；或配置 RERANKER_ENDPOINT"
            ) from exc

        name = os.getenv("RERANKER_LOCAL_MODEL", "BAAI/bge-reranker-v2-m3")
        if self.model and "/" in self.model:
            name = self.model
        # 默认优先本地缓存；首次缺失时再联网（由调用方准备好镜像/代理）
        local_only = os.getenv("RERANKER_LOCAL_FILES_ONLY", "0") in ("1", "true", "True")
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(name, local_files_only=local_only)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                name, local_files_only=local_only
            )
        except Exception:
            self._tokenizer = AutoTokenizer.from_pretrained(name, local_files_only=True)
            self._model = AutoModelForSequenceClassification.from_pretrained(name, local_files_only=True)
        self._model.to(self._device)
        self._model.eval()
        return self._tokenizer, self._model


@lru_cache(maxsize=1)
def get_reranker_adapter() -> RerankerAdapter:
    return RerankerAdapter()
