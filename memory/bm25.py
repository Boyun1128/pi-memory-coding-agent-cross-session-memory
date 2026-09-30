"""BM25-lite：給每筆文件對查詢打相關度分數，回傳排序後的前 K 筆。整個作業的核心。
tokenize() 已給你；bm25_search() 的計分要你填。"""
from __future__ import annotations
import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    """小寫化後，取出英數字詞與單個 CJK 字元。不做 stemming。（已提供）"""
    return _TOKEN_RE.findall(text.lower())


def bm25_search(
    query: str,
    docs: list[dict],
    k: int = 8,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[dict]:
    """
    標準 BM25 排序。
    docs = [{"id": str, "text": str}, ...]
    回傳 [{"id": str, "score": float}, ...]（高到低，前 k 筆）。

      score(q,d) = Σ_qi IDF(qi) * (tf*(k1+1)) / (tf + k1*(1 - b + b*|d|/avgdl))
      IDF(qi)    = ln( (N - n + 0.5)/(n + 0.5) + 1 )
      tf  = qi 在 d 出現次數
      |d| = d 詞數
      avgdl = 平均詞數
      N   = 文件數
      n   = 含 qi 的文件數
    """
    # Guard: 空語料或空查詢
    if not docs:
        return []

    N = len(docs)
    query_terms = tokenize(query)

    # -----------------------------------------------------------------------
    # Step 1 — 斷詞 + 統計
    # -----------------------------------------------------------------------
    tokenized = [tokenize(d["text"]) for d in docs]
    doc_lengths = [len(t) for t in tokenized]
    avgdl = sum(doc_lengths) / N

    # Document frequency：每個詞在多少篇文件出現（每篇只算一次）
    df: dict[str, int] = {}
    for tokens in tokenized:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1

    # -----------------------------------------------------------------------
    # Step 2 — 對每篇文件打分
    # -----------------------------------------------------------------------
    results = []
    for i, doc in enumerate(docs):
        if not query_terms:
            # 空 query → 分數 0，但仍保留在結果中（維持穩定順序）
            results.append({"id": doc["id"], "score": 0.0})
            continue

        tf_counts = Counter(tokenized[i])
        doc_len = doc_lengths[i]
        score = 0.0

        for term in query_terms:
            tf = tf_counts.get(term, 0)
            if tf == 0:
                continue  # 此詞不在文件中，貢獻 0

            n = df.get(term, 0)
            # Robertson–Spärck-Jones +1 smoothed IDF（保證非負）
            idf = math.log((N - n + 0.5) / (n + 0.5) + 1)
            # BM25 Okapi TF 分量
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1.0 - b + b * doc_len / avgdl)
            score += idf * numerator / denominator

        results.append({"id": doc["id"], "score": score})

    # -----------------------------------------------------------------------
    # Step 3 — 排序：分數高到低；同分保持原始插入順序（stable sort）
    # -----------------------------------------------------------------------
    results.sort(key=lambda x: -x["score"])
    return results[:k]
