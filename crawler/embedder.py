#!/usr/bin/env python3
import os
import argparse
from typing import List, Tuple

import pymysql
import numpy as np

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from sentence_transformers import SentenceTransformer


# -----------------------------
# DB helpers
# -----------------------------
def db_connect():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        autocommit=False,
    )


def fetch_chunks_without_embedding(conn, model_name: str, limit: int) -> List[Tuple[int, str]]:
    """
    Grąžina chunkus, kurie dar neturi embeddings įrašo su šituo modeliu.
    """
    sql = """
        SELECT c.id, c.chunk_text
        FROM article_chunks c
        LEFT JOIN embeddings e
          ON e.chunk_id = c.id AND e.model = %s
        WHERE e.id IS NULL
          AND c.chunk_text IS NOT NULL
          AND c.chunk_text <> ''
        ORDER BY c.id ASC
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (model_name, limit))
        return list(cur.fetchall())


def insert_embeddings(
    conn,
    rows: List[Tuple[int, np.ndarray]],
    model_name: str,
    dims: int,
) -> int:
    """
    Įrašo embeddingus į DB.
    Naudojam INSERT IGNORE, nes turim UNIQUE(chunk_id, model).
    embedding = float32 bytes.
    """
    if not rows:
        return 0

    sql = """
        INSERT IGNORE INTO embeddings (chunk_id, model, dims, embedding)
        VALUES (%s, %s, %s, %s)
    """

    inserted = 0
    with conn.cursor() as cur:
        for chunk_id, vec in rows:
            vec = np.asarray(vec, dtype=np.float32)
            blob = vec.tobytes(order="C")
            cur.execute(sql, (chunk_id, model_name, dims, blob))
            inserted += cur.rowcount
    return inserted


# -----------------------------
# Embedding helpers
# -----------------------------
def embed_texts(
    st_model: SentenceTransformer,
    texts: List[str],
    batch_size: int,
    normalize: bool,
    prefix: str,
) -> np.ndarray:
    """
    Grąžina (N, D) float32.
    E5 rekomendacija: "passage: " dokumentams, "query: " užklausoms.
    """
    if prefix:
        texts = [f"{prefix}{t}" for t in texts]

    emb = st_model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
    )
    return emb.astype(np.float32)


# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for article_chunks into embeddings table.")
    parser.add_argument("--model", type=str, default="intfloat/multilingual-e5-small", help="HF model name")
    parser.add_argument("--limit", type=int, default=500, help="Kiek chunkų apdoroti per vieną run (default: 500)")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size (default: 32)")
    parser.add_argument("--device", type=str, default=None, help="cpu / cuda (default: auto)")
    parser.add_argument("--normalize", action="store_true", help="L2 normalize embeddings (rekomenduojama retrieval)")
    parser.add_argument(
        "--prefix",
        type=str,
        default="passage: ",
        help="Prefix dokumentams (E5: 'passage: '), užklausoms vėliau naudosi 'query: '",
    )
    args = parser.parse_args()
    
    if args.device is not None and not str(args.device).strip():
        args.device = None

    required_env = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [k for k in required_env if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Missing env vars: {', '.join(missing)}")

    print(f"[embedder] loading model: {args.model}")
    st_model = SentenceTransformer(args.model, device=args.device)

    conn = db_connect()
    try:
        chunks = fetch_chunks_without_embedding(conn, args.model, args.limit)
        if not chunks:
            print("[embedder] No chunks without embeddings. Nothing to do.")
            return

        ids = [cid for (cid, _) in chunks]
        texts = [txt for (_, txt) in chunks]

        print(f"[embedder] chunks_to_embed={len(texts)} batch_size={args.batch_size} normalize={args.normalize}")
        vectors = embed_texts(
            st_model=st_model,
            texts=texts,
            batch_size=args.batch_size,
            normalize=args.normalize,
            prefix=args.prefix,
        )

        # dims
        if vectors.ndim != 2:
            raise RuntimeError(f"Unexpected embeddings shape: {vectors.shape}")
        dims = int(vectors.shape[1])

        rows = list(zip(ids, list(vectors)))
        inserted = insert_embeddings(conn, rows, args.model, dims)
        conn.commit()

        print(f"[embedder] done. dims={dims} inserted={inserted} requested={len(rows)}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
