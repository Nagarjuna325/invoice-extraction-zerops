import json
import logging
import math
import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LabelMatchResult:
    matched: bool
    field: str
    score: float
    method: str
    rule_score: Optional[float] = None
    semantic_score: Optional[float] = None


class LabelMatcher:
    """
    Hybrid label matcher with rule-based and optional semantic matching.

    Rule-based matching is used by default to preserve current behavior.
    Semantic matching is optional and can be enabled with flags.
    """

    LABEL_SYNONYMS: Dict[str, List[str]] = {
        "invoice_number": [
            "invoice number",
            "invoice no",
            "invoice #",
            "inv number",
            "inv no",
            "inv #",
            "invoice id",
            "document number",
            "reference number",
        ],
        "po_number": [
            "po number",
            "po no",
            "po #",
            "purchase order",
            "purchase order number",
            "your purchase order",
        ],
        "invoice_date": [
            "invoice date",
            "inv date",
            "issue date",
            "issued date",
            "date",
        ],
        "due_date": [
            "due date",
            "payment due",
            "pay by",
            "due on",
        ],
        "total_amount": [
            "total",
            "total amount",
            "invoice total",
            "grand total",
            "amount due",
            "balance due",
        ],
    }

    NEGATIVE_TERMS: Dict[str, List[str]] = {
        "total_amount": ["subtotal", "sub total", "tax", "vat", "gst"],
        "invoice_date": ["due"],
        "due_date": ["invoice"],
        "invoice_number": ["po", "purchase order"],
        "po_number": ["invoice"],
    }

    def __init__(self) -> None:
        self._embedding_provider = None
        self._canonical_embeddings: Dict[str, List[List[float]]] = {}
        self._text_embedding_cache = LruCache(settings.LABEL_EMBED_CACHE_SIZE)

    def match_line(
        self,
        line_text: str,
        field: str,
        label_patterns: Optional[Iterable[re.Pattern]] = None,
    ) -> LabelMatchResult:
        mode = (settings.LABEL_MATCH_MODE or "rule").lower()
        enable_semantic = settings.ENABLE_LABEL_SEMANTIC_MATCH

        rule_result = self._rule_match(line_text, field, label_patterns)
        if mode == "rule" or not enable_semantic:
            return rule_result

        semantic_result = self._semantic_match(line_text, field)

        if mode == "semantic":
            return semantic_result

        # Hybrid mode: rule first, semantic fallback
        if rule_result.matched and not settings.LABEL_MATCH_DEBUG:
            return rule_result

        if rule_result.matched and settings.LABEL_MATCH_DEBUG:
            return self._merge_results(rule_result, semantic_result, "hybrid")

        if semantic_result.matched:
            return semantic_result

        return self._merge_results(rule_result, semantic_result, "hybrid")

    def _rule_match(
        self,
        line_text: str,
        field: str,
        label_patterns: Optional[Iterable[re.Pattern]],
    ) -> LabelMatchResult:
        if not line_text:
            return LabelMatchResult(False, field, 0.0, "rule", rule_score=0.0)

        if self._has_negative_term(line_text, field):
            return LabelMatchResult(False, field, 0.0, "rule", rule_score=0.0)

        if label_patterns:
            for pattern in label_patterns:
                if pattern.search(line_text):
                    return LabelMatchResult(True, field, 0.95, "rule", rule_score=0.95)

        return LabelMatchResult(False, field, 0.0, "rule", rule_score=0.0)

    def _semantic_match(self, line_text: str, field: str) -> LabelMatchResult:
        if not line_text:
            return LabelMatchResult(False, field, 0.0, "semantic", semantic_score=0.0)

        if self._has_negative_term(line_text, field):
            return LabelMatchResult(False, field, 0.0, "semantic", semantic_score=0.0)

        synonyms = self.LABEL_SYNONYMS.get(field, [])
        if not synonyms:
            return LabelMatchResult(False, field, 0.0, "semantic", semantic_score=0.0)

        try:
            score = self._semantic_score(line_text, field, synonyms)
        except Exception as exc:
            logger.warning("Label semantic match failed, falling back to rule-based: %s", exc)
            return LabelMatchResult(False, field, 0.0, "semantic", semantic_score=0.0)

        matched = score >= settings.LABEL_MATCH_MIN_SCORE
        return LabelMatchResult(matched, field, score if matched else 0.0, "semantic", semantic_score=score)

    def _semantic_score(self, text: str, field: str, synonyms: List[str]) -> float:
        if field not in self._canonical_embeddings:
            embeddings = self._embed_texts(synonyms)
            self._canonical_embeddings[field] = embeddings

        text_vec = self._get_text_embedding(text)
        if not text_vec:
            return 0.0

        best = 0.0
        for cand_vec in self._canonical_embeddings[field]:
            sim = cosine_similarity(text_vec, cand_vec)
            if sim > best:
                best = sim
        return float(best)

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        provider = self._get_provider()
        if not provider:
            return []
        return provider.embed_texts(texts)

    def _get_text_embedding(self, text: str) -> Optional[List[float]]:
        normalized = self._normalize_text(text)
        if not normalized:
            return None

        cached = self._text_embedding_cache.get(normalized)
        if cached is not None:
            return cached

        provider = self._get_provider()
        if not provider:
            return None
        embedding = provider.embed_texts([normalized])[0]
        self._text_embedding_cache.set(normalized, embedding)
        return embedding

    def _get_provider(self) -> Optional["EmbeddingProvider"]:
        if self._embedding_provider is not None:
            return self._embedding_provider

        provider_name = (settings.LABEL_EMBED_PROVIDER or "local").lower()
        if provider_name == "anthropic":
            self._embedding_provider = AnthropicEmbeddingProvider(
                api_key=settings.LABEL_EMBED_API_KEY,
                api_url=settings.LABEL_EMBED_API_URL,
                model=settings.LABEL_EMBED_MODEL,
                api_version=settings.LABEL_EMBED_API_VERSION,
                timeout=settings.LABEL_EMBED_TIMEOUT_S,
            )
            return self._embedding_provider

        self._embedding_provider = LocalEmbeddingProvider(settings.LABEL_SEMANTIC_MODEL)
        return self._embedding_provider

    def _has_negative_term(self, text: str, field: str) -> bool:
        negatives = self.NEGATIVE_TERMS.get(field, [])
        if not negatives:
            return False
        lower = text.lower()
        return any(term in lower for term in negatives)

    def _normalize_text(self, text: str) -> str:
        cleaned = re.sub(r"[^a-z0-9#]+", " ", text.lower())
        return " ".join(cleaned.split())

    def _merge_results(
        self,
        rule_result: LabelMatchResult,
        semantic_result: LabelMatchResult,
        method: str,
    ) -> LabelMatchResult:
        result = LabelMatchResult(
            matched=rule_result.matched or semantic_result.matched,
            field=rule_result.field,
            score=rule_result.score if rule_result.matched else semantic_result.score,
            method=method,
            rule_score=rule_result.rule_score,
            semantic_score=semantic_result.semantic_score,
        )
        return result


class LruCache:
    def __init__(self, max_size: int) -> None:
        self.max_size = max(1, int(max_size or 256))
        self._data: OrderedDict[str, List[float]] = OrderedDict()

    def get(self, key: str) -> Optional[List[float]]:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def set(self, key: str, value: List[float]) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        if len(self._data) > self.max_size:
            self._data.popitem(last=False)


class EmbeddingProvider:
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._backend = None
        self._model = None
        self._tokenizer = None
        self._load_local_model()

    def _load_local_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer(self.model_name)
            self._backend = "sentence_transformers"
            return
        except Exception as exc:
            logger.info("SentenceTransformer not available, using transformers backend: %s", exc)

        try:
            from transformers import AutoModel, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name)
            self._model.eval()
            self._backend = "transformers"
        except Exception as exc:
            logger.warning("Failed to load local embedding model '%s': %s", self.model_name, exc)
            self._backend = None

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not self._model:
            return [[0.0] * 8 for _ in texts]

        if self._backend == "sentence_transformers":
            embeddings = self._model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()

        return self._embed_with_transformers(texts)

    def _embed_with_transformers(self, texts: List[str]) -> List[List[float]]:
        import torch

        if not self._tokenizer or not self._model:
            return [[0.0] * 8 for _ in texts]

        encoded = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=64,
        )
        with torch.no_grad():
            outputs = self._model(**encoded)
            token_embeddings = outputs.last_hidden_state
            attention_mask = encoded.get("attention_mask")
            if attention_mask is None:
                pooled = token_embeddings.mean(dim=1)
            else:
                mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                summed = (token_embeddings * mask).sum(dim=1)
                counts = mask.sum(dim=1).clamp(min=1e-9)
                pooled = summed / counts
            normalized = torch.nn.functional.normalize(pooled, p=2, dim=1)
        return normalized.cpu().tolist()


class AnthropicEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        api_key: str,
        api_url: str,
        model: str,
        api_version: str,
        timeout: float,
    ) -> None:
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.api_version = api_version
        self.timeout = timeout

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key or not self.api_url:
            raise RuntimeError("Anthropic embedding API is not configured")

        payload = {"model": self.model, "input": texts}
        data = json.dumps(payload).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
        }

        request = urllib_request(self.api_url, data=data, headers=headers, timeout=self.timeout)
        with request as response:
            raw = response.read().decode("utf-8")
        parsed = json.loads(raw)
        embeddings = parsed.get("data") or []
        if not embeddings:
            raise RuntimeError("Anthropic embedding response missing data")
        return [item.get("embedding", []) for item in embeddings]


def urllib_request(url: str, data: bytes, headers: Dict[str, str], timeout: float):
    import urllib.request

    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    return urllib.request.urlopen(request, timeout=timeout)


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


label_matcher = LabelMatcher()
