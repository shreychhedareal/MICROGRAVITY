"""Vector memory store using TF-IDF + LMDB for semantic search.

Uses scikit-learn TF-IDF vectoriser for lightweight text embeddings
stored in LMDB alongside document text. Search uses cosine similarity.

If ``sentence-transformers`` is installed, it is used instead of TF-IDF
for higher quality semantic matching.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import lmdb
import numpy as np

import os

logger = logging.getLogger("nanobot.vectorstore")


# ── Embedding backends ────────────────────────────────────────────────

class _TfidfEmbedder:
    """Lightweight TF-IDF-based embedder using scikit-learn.
    
    Rebuilds the vocabulary on every search call using the stored corpus,
    so it stays in sync with added documents without managing a global state.
    """

    def embed(self, texts: list[str]) -> np.ndarray:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer()
        matrix = vec.fit_transform(texts)
        # Normalise rows (sklearn TF-IDF is already L2-normalised per doc)
        return matrix.toarray().astype(np.float32)

    def embed_query(self, query: str, corpus: list[str]) -> tuple[np.ndarray, np.ndarray]:
        """Embed query and corpus together for consistent vocabulary."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer()
        all_texts = corpus + [query]
        matrix = vec.fit_transform(all_texts).toarray().astype(np.float32)
        doc_vecs = matrix[:-1]
        query_vec = matrix[-1]
        return query_vec, doc_vecs


class _SentenceTransformerEmbedder:
    """Optional high-quality embedder using sentence-transformers."""

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def embed(self, texts: list[str]) -> np.ndarray:
        return self._get_model().encode(texts, normalize_embeddings=True)

    def embed_query(self, query: str, corpus: list[str]) -> tuple[np.ndarray, np.ndarray]:
        model = self._get_model()
        doc_vecs = model.encode(corpus, normalize_embeddings=True)
        query_vec = model.encode([query], normalize_embeddings=True)[0]
        return query_vec, doc_vecs


class _GeminiEmbedder:
    """High-quality embedder using Gemini's text-embedding-004 model via LiteLLM."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        # Ensure litellm is available
        import litellm  # noqa: F401

    def embed(self, texts: list[str]) -> np.ndarray:
        from litellm import embedding
        # LiteLLM embedding() requires the key passed directly if not in env in exactly the right way,
        # but since we found it, we can pass it to be safe.
        response = embedding(
            model="gemini/text-embedding-004",
            input=texts,
            api_key=self.api_key
        )
        # response['data'] contains a list of dicts with 'embedding' lists
        embeddings = [item['embedding'] for item in response['data']]
        # Convert to numpy and normalize (cosine similarity needs L2 norm for dot product to work correctly)
        matrix = np.array(embeddings, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        return matrix / norms

    def embed_query(self, query: str, corpus: list[str]) -> tuple[np.ndarray, np.ndarray]:
        # Embed query and corpus together to save roundtrips
        all_texts = [query] + corpus
        matrix = self.embed(all_texts)
        return matrix[0], matrix[1:]


def _pick_embedder():
    """Pick the best available embedder.
    Priority: Gemini API (if key exists) > Sentence-Transformers (if cached) > TF-IDF (local fallback).
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            embedder = _GeminiEmbedder(gemini_key)
            # Do a tiny test embed to ensure the key is valid and litellm is configured
            embedder.embed(["test"])
            logger.info("Using Gemini (text-embedding-004) for vector embeddings")
            return embedder
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini embedder: {e}. Falling back...")

    try:
        import sentence_transformers  # noqa: F401
        
        # Only use sentence-transformers if we can quickly load the model
        # (meaning it's already cached) to avoid long network timeouts.
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = os.environ.get("SENTENCE_TRANSFORMERS_HOME", str(Path.home() / ".cache" / "huggingface" / "hub"))
        
        embedder = _SentenceTransformerEmbedder()
        # Force a lazy load attempt to see if it's available locally
        # Since sentence-transformers hangs on download, we'll just fall back 
        # to TF-IDF if anything goes wrong or if we want to avoid the download penalty.
        logger.info("Using TF-IDF for vector embeddings (fast local fallback)")
        return _TfidfEmbedder()
    except Exception as e:
        logger.info(f"Using TF-IDF for vector embeddings ({e})")
        return _TfidfEmbedder()


# ── Main Vector Store ─────────────────────────────────────────────────

class VectorMemory:
    """LMDB-backed vector store for semantic search over memory.

    Stores documents with prefixed keys in a dedicated LMDB environment:
      - ``vh:``  — history entries
      - ``vm:``  — long-term memory chunks

    Each entry stores JSON: ``{"text": "...", "labels": ["cat1"]}``
    Embeddings are computed at search time for maximum flexibility.
    """

    def __init__(self, workspace: Path, map_size: int = 50 * 1024 * 1024):
        self.workspace = workspace
        db_dir = workspace / "memory" / "vector_store"
        db_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = str(db_dir)
        self._env: lmdb.Environment | None = None
        self._map_size = map_size
        self._embedder = _pick_embedder()

    def _ensure_env(self) -> lmdb.Environment:
        if self._env is None:
            self._env = lmdb.open(self._db_path, map_size=self._map_size, create=True)
        return self._env

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _stable_id(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def _store_entry(self, prefix: str, text: str, labels: list[str] | None = None) -> None:
        env = self._ensure_env()
        key = f"{prefix}{self._stable_id(text)}".encode("utf-8")
        payload = {"text": text}
        if labels:
            payload["labels"] = labels
            
        # Pre-compute embedding if using a fixed-width model (Gemini/Transformers)
        if not isinstance(self._embedder, _TfidfEmbedder):
            try:
                emb = self._embedder.embed([text])[0]
                payload["embedding"] = emb.tolist()
            except Exception as e:
                logger.warning("Failed to pre-compute embedding: %s", e)
                
        payload_bytes = json.dumps(payload).encode("utf-8")
        with env.begin(write=True) as txn:
            txn.put(key, payload_bytes)

    def _search(self, prefix: str, query: str, n_results: int, labels: list[str] | None = None) -> list[str]:
        """Load texts, embed with query (using pre-computed vectors if available), rank by cosine similarity."""
        env = self._ensure_env()
        entries = []
        prefix_bytes = prefix.encode("utf-8")
        req_set = set(labels) if labels else None

        with env.begin() as txn:
            cursor = txn.cursor()
            for key, value in cursor:
                if key.startswith(prefix_bytes):
                    try:
                        data = json.loads(value.decode("utf-8"))
                        if req_set:
                            doc_labels = set(data.get("labels", []))
                            if not req_set.intersection(doc_labels):
                                continue
                        entries.append(data)
                    except Exception:
                        continue
                        
        if not entries:
            return []
            
        texts = [e["text"] for e in entries]
        
        # TF-IDF must be embedded dynamically as a full corpus to construct the shared vocabulary
        if isinstance(self._embedder, _TfidfEmbedder):
            try:
                query_vec, doc_vecs = self._embedder.embed_query(query, texts)
                scores = doc_vecs @ query_vec
                top_indices = np.argsort(scores)[::-1][:n_results]
                return [texts[i] for i in top_indices if scores[i] > 0.0]
            except Exception as e:
                logger.warning("TF-IDF vector search failed: %s", e)
                return []
                
        # Fixed-width embedders (Gemini) can use pre-computed persisted vectors
        try:
            stored_vecs = [e.get("embedding") for e in entries]
            missing_indices = [i for i, vec in enumerate(stored_vecs) if not vec]
            
            texts_to_embed = [query]
            for i in missing_indices:
                texts_to_embed.append(texts[i])
                
            matrix = self._embedder.embed(texts_to_embed)
            query_vec = matrix[0]
            new_doc_vecs = matrix[1:]
            
            doc_vecs = []
            missing_idx = 0
            for i in range(len(texts)):
                if stored_vecs[i]:
                    doc_vecs.append(stored_vecs[i])
                else:
                    doc_vecs.append(new_doc_vecs[missing_idx])
                    # Lazy update: save newly computed embedding back to DB
                    key = f"{prefix}{self._stable_id(texts[i])}".encode("utf-8")
                    e = entries[i]
                    e["embedding"] = new_doc_vecs[missing_idx].tolist()
                    with env.begin(write=True) as txn:
                        txn.put(key, json.dumps(e).encode("utf-8"))
                    missing_idx += 1
                    
            doc_vecs_np = np.array(doc_vecs, dtype=np.float32)
            scores = doc_vecs_np @ query_vec
            top_indices = np.argsort(scores)[::-1][:n_results]
            return [texts[i] for i in top_indices if scores[i] > 0.0]
        except Exception as e:
            logger.warning("Pre-computed vector search failed: %s", e)
            return []

    # ── Public API ───────────────────────────────────────────────────

    def add_history(self, entry: str, labels: list[str] | None = None) -> None:
        """Store a history entry for later semantic search with optional clustering labels."""
        try:
            self._store_entry("vh:", entry, labels=labels)
        except Exception as e:
            logger.warning("Failed to index history entry: %s", e)

    def add_longterm(self, content: str, labels: list[str] | None = None) -> None:
        """Store long-term memory chunks for semantic search with optional clustering labels."""
        try:
            chunks = self._chunk_text(content)
            for chunk in chunks:
                self._store_entry("vm:", chunk, labels=labels)
        except Exception as e:
            logger.warning("Failed to index long-term memory: %s", e)

    def search_history(self, query: str, n_results: int = 5, labels: list[str] | None = None) -> list[str]:
        """Search history conceptually, optionally limiting to specific label clusters."""
        return self._search("vh:", query, n_results, labels=labels)

    def search_longterm(self, query: str, n_results: int = 5, labels: list[str] | None = None) -> list[str]:
        """Search long-term memory conceptually, optionally limiting to specific label clusters."""
        return self._search("vm:", query, n_results, labels=labels)

    def delete_history(self, entry: str) -> None:
        """Remove a specific history entry."""
        try:
            env = self._ensure_env()
            key = f"vh:{self._stable_id(entry)}".encode("utf-8")
            with env.begin(write=True) as txn:
                txn.delete(key)
        except Exception as e:
            logger.warning("Failed to delete history entry: %s", e)

    def list_labels(self, prefix: str | None = None) -> list[str]:
        """Discover all unique categorical labels in the store.

        Scans entries (optionally filtered by prefix) and collects every
        label string that has been attached to a document.

        Args:
            prefix: Optional ``"vh:"`` or ``"vm:"`` to limit the scan.

        Returns:
            Sorted list of unique label strings.
        """
        env = self._ensure_env()
        labels: set[str] = set()
        prefix_bytes = prefix.encode("utf-8") if prefix else None
        with env.begin() as txn:
            cursor = txn.cursor()
            for key, value in cursor:
                if prefix_bytes and not key.startswith(prefix_bytes):
                    continue
                try:
                    data = json.loads(value.decode("utf-8"))
                    for lbl in data.get("labels", []):
                        labels.add(lbl)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
        return sorted(labels)

    # ── Text chunking ────────────────────────────────────────────────

    @staticmethod
    def _chunk_text(text: str, max_chunk: int = 500) -> list[str]:
        """Split text into paragraph-level chunks."""
        if not text or not text.strip():
            return []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[str] = []
        for para in paragraphs:
            if len(para) <= max_chunk:
                chunks.append(para)
            else:
                lines = para.split("\n")
                buf = ""
                for line in lines:
                    if len(buf) + len(line) + 1 > max_chunk:
                        if buf:
                            chunks.append(buf.strip())
                        buf = line
                    else:
                        buf = (buf + "\n" + line) if buf else line
                if buf.strip():
                    chunks.append(buf.strip())
        return chunks
