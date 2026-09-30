"""
memory/hybrid.py — Hybrid BM25 + dense retrieval (Task 2 advanced feature)

Combines BM25 lexical scores with cosine similarity from a local
sentence-transformers embedding model.

Interface matches bm25_search exactly:
  docs = [{"id": str, "text": str}, ...]
  returns [{"id": str, "score": float}, ...]  (high to low, top k)

Design constraints:
- MUST NOT modify memory/bm25.py.
- sentence_transformers is imported lazily so pure BM25 path has zero overhead.
- Score fusion: fused = alpha * norm_bm25 + (1 - alpha) * cosine_sim
"""

from __future__ import annotations

from memory.bm25 import bm25_search


def hybrid_search(
    query: str,
    docs: list[dict],
    k: int = 8,
    alpha: float = 0.5,
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> list[dict]:
    """
    Rank *docs* against *query* using fused BM25 + dense embedding scores.

    Parameters
    ----------
    query:
        Natural-language query string.
    docs:
        List of {"id": str, "text": str} dicts — same format as bm25_search.
    k:
        Maximum number of results to return.
    alpha:
        Weight for BM25 component in [0, 1].
        1.0 = pure BM25;  0.0 = pure cosine similarity.
    model_name:
        HuggingFace sentence-transformers model identifier.

    Returns
    -------
    list of {"id": str, "score": float}
        Sorted by descending fused score. Same format as bm25_search.

    Raises
    ------
    ImportError
        If sentence_transformers is not installed.
    """
    # Lazy import — bm25.py never pays this cost
    try:
        from sentence_transformers import SentenceTransformer, util  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "sentence_transformers is required for hybrid_search. "
            "Install it with: pip install sentence-transformers"
        ) from exc

    if not docs or k == 0:
        return []

    N = len(docs)

    # ------------------------------------------------------------------
    # BM25 component — score every document (k=N for full ranking)
    # ------------------------------------------------------------------
    bm25_results = bm25_search(query, docs, k=N)

    # Rebuild score array indexed by position in docs
    id_to_pos = {d["id"]: i for i, d in enumerate(docs)}
    bm25_scores = [0.0] * N
    for r in bm25_results:
        pos = id_to_pos.get(r["id"])
        if pos is not None:
            bm25_scores[pos] = r["score"]

    # Min-max normalise to [0, 1]
    max_bm25 = max(bm25_scores)
    if max_bm25 > 0:
        norm_bm25 = [s / max_bm25 for s in bm25_scores]
    else:
        norm_bm25 = [0.0] * N

    # ------------------------------------------------------------------
    # Dense embedding component
    # ------------------------------------------------------------------
    model = SentenceTransformer(model_name)
    texts = [d["text"] for d in docs]

    q_emb = model.encode(query, convert_to_tensor=True)
    c_embs = model.encode(texts, convert_to_tensor=True)
    cos_sims = util.cos_sim(q_emb, c_embs)[0].tolist()  # list of N floats

    # ------------------------------------------------------------------
    # Score fusion + sort
    # ------------------------------------------------------------------
    fused = [
        {"id": docs[i]["id"], "score": alpha * norm_bm25[i] + (1.0 - alpha) * cos_sims[i]}
        for i in range(N)
    ]
    fused.sort(key=lambda x: -x["score"])
    return fused[:k]
