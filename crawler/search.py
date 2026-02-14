#!/usr/bin/env python3
import os
import argparse
from typing import List, Dict, Any, Tuple

import numpy as np
import pymysql

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from sentence_transformers import SentenceTransformer


def db_connect():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        autocommit=True,
    )


def fetch_embeddings_with_context(
    conn,
    model_name: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Grąžina embeddingus + chunk tekstą + straipsnio metadata.
    """
    sql = """
        SELECT
            e.id AS embedding_id,
            e.chunk_id,
            e.dims,
            e.embedding,
            c.article_id,
            c.chunk_index,
            c.chunk_text,
            a.title,
            a.canonical_url,
            a.published_at
        FROM embeddings e
        JOIN article_chunks c ON c.id = e.chunk_id
        JOIN articles a ON a.id = c.article_id
        WHERE e.model = %s
        ORDER BY e.id ASC
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (model_name, limit))
        rows = cur.fetchall()

    out = []
    for r in rows:
        out.append(
            {
                "embedding_id": r[0],
                "chunk_id": r[1],
                "dims": int(r[2]),
                "embedding_blob": r[3],
                "article_id": r[4],
                "chunk_index": r[5],
                "chunk_text": r[6],
                "title": r[7],
                "canonical_url": r[8],
                "published_at": r[9],
            }
        )
    return out


def blob_to_vec(blob: bytes, dims: int) -> np.ndarray:
    v = np.frombuffer(blob, dtype=np.float32)
    if v.size != dims:
        # jei DB įrašas blogas / dims nesutampa
        raise ValueError(f"Embedding dims mismatch: expected {dims}, got {v.size}")
    return v


def cosine_sim_matrix(query_vec: np.ndarray, mat: np.ndarray) -> np.ndarray:
    """
    cosine(query, each row of mat)
    """
    q = query_vec.astype(np.float32)
    m = mat.astype(np.float32)

    qn = np.linalg.norm(q) + 1e-12
    mn = np.linalg.norm(m, axis=1) + 1e-12
    return (m @ q) / (mn * qn)


def main():
    parser = argparse.ArgumentParser(description="Semantic search prototype over stored chunk embeddings.")
    parser.add_argument("query", type=str, help="Vartotojo claim / užklausa (lietuviškai)")
    parser.add_argument("--model", type=str, default="intfloat/multilingual-e5-small", help="Model name (must match embeddings.model)")
    parser.add_argument("--topk", type=int, default=10, help="Kiek rezultatų grąžinti (default: 10)")
    parser.add_argument("--limit", type=int, default=5000, help="Kiek embeddingų iš DB užkrauti į RAM (default: 5000)")
    parser.add_argument("--device", type=str, default=None, help="cpu/cuda (default: auto)")
    parser.add_argument("--normalize-query", action="store_true", help="Normalizuoti query embedding (rekomenduojama)")
    parser.add_argument("--show-chars", type=int, default=350, help="Kiek chunk teksto simbolių parodyti (default: 350)")
    args = parser.parse_args()

    required_env = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [k for k in required_env if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Missing env vars: {', '.join(missing)}")

    conn = db_connect()
    try:
        rows = fetch_embeddings_with_context(conn, args.model, args.limit)
    finally:
        conn.close()

    if not rows:
        print("[search] No embeddings found for this model. (embeddings table empty or model mismatch)")
        return

    dims = rows[0]["dims"]
    # load matrix
    vecs = np.vstack([blob_to_vec(r["embedding_blob"], dims) for r in rows]).astype(np.float32)

    # embed query (E5: naudoti prefix "query: ")
    st_model = SentenceTransformer(args.model, device=args.device)
    q_text = f"query: {args.query}"
    q_vec = st_model.encode([q_text], convert_to_numpy=True, show_progress_bar=False)[0].astype(np.float32)

    if args.normalize_query:
        n = np.linalg.norm(q_vec) + 1e-12
        q_vec = q_vec / n

    scores = cosine_sim_matrix(q_vec, vecs)
    topk = min(args.topk, scores.size)
    idxs = np.argpartition(-scores, topk - 1)[:topk]
    idxs = idxs[np.argsort(-scores[idxs])]

    print(f"[search] model={args.model} dims={dims} searched={len(rows)} topk={topk}\n")

    for rank, i in enumerate(idxs, start=1):
        r = rows[int(i)]
        s = float(scores[int(i)])
        snippet = (r["chunk_text"] or "").strip().replace("\n", " ")
        if len(snippet) > args.show_chars:
            snippet = snippet[: args.show_chars] + "…"

        print(f"{rank}. score={s:.4f}  article_id={r['article_id']}  chunk_id={r['chunk_id']}  idx={r['chunk_index']}")
        print(f"   title: {r['title']}")
        print(f"   url:   {r['canonical_url']}")
        if r["published_at"]:
            print(f"   published_at: {r['published_at']}")
        print(f"   text:  {snippet}\n")


if __name__ == "__main__":
    main()
