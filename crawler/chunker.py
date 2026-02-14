#!/usr/bin/env python3
import os
import re
import argparse
import hashlib
from typing import List, Tuple

import pymysql

try:
    # optional (jei paleisi ne per docker compose env)
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# -----------------------------
# Chunking helpers
# -----------------------------
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

def normalize_text(text: str) -> str:
    # sutvarko whitespace, bet palieka pastraipas
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # pašalinam labai daug tuščių eilučių
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def split_paragraphs(text: str) -> List[str]:
    # pastraipos pagal tuščias eilutes
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p and p.strip()]
    return paras

def split_sentences(text: str) -> List[str]:
    # paprastas sakinių skaidymas
    parts = _SENT_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p and p.strip()]

def build_chunks(
    paragraphs: List[str],
    target_chars: int,
    max_chars: int,
    overlap_paras: int,
) -> List[str]:
    """
    Kraunam pastraipas į chunkus iki target_chars (leidžiam viršyti iki max_chars).
    Jei pastraipa per ilga -> splitinam sakiniais.
    Overlap darom paskutinėmis overlap_paras pastraipomis.
    """
    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0

    def flush_with_overlap():
        nonlocal cur, cur_len
        if not cur:
            return
        chunk = "\n".join(cur).strip()
        if chunk:
            chunks.append(chunk)

        # overlap: pasiimam paskutines pastraipas kaip startą kitam chunkui
        if overlap_paras > 0 and len(cur) > 0:
            overlap = cur[-overlap_paras:]
        else:
            overlap = []
        cur = overlap[:]
        cur_len = sum(len(x) + 1 for x in cur)

    for para in paragraphs:
        if len(para) > max_chars:
            # per ilga pastraipa -> skaidom sakiniais ir kraunam sakinius
            sentences = split_sentences(para)
            for s in sentences:
                if not s:
                    continue
                # jei vienas sakinys irgi milžiniškas -> pjaustom tiesiog gabalais
                if len(s) > max_chars:
                    for i in range(0, len(s), max_chars):
                        piece = s[i : i + max_chars]
                        if cur_len + len(piece) + 1 > max_chars and cur:
                            flush_with_overlap()
                        cur.append(piece)
                        cur_len += len(piece) + 1
                        if cur_len >= target_chars:
                            flush_with_overlap()
                    continue

                if cur_len + len(s) + 1 > max_chars and cur:
                    flush_with_overlap()
                cur.append(s)
                cur_len += len(s) + 1
                if cur_len >= target_chars:
                    flush_with_overlap()
            continue

        # normalus para
        if cur_len + len(para) + 2 > max_chars and cur:
            flush_with_overlap()

        cur.append(para)
        cur_len += len(para) + 2

        if cur_len >= target_chars:
            flush_with_overlap()

    # likutis
    if cur:
        chunk = "\n".join(cur).strip()
        if chunk:
            chunks.append(chunk)

    return chunks


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
        autocommit=False,  # valdysim commit patys
    )

def md5_bin16(s: str) -> bytes:
    return hashlib.md5(s.encode("utf-8")).digest()

def fetch_articles_without_chunks(conn, limit: int) -> List[Tuple[int, str]]:
    sql = """
        SELECT a.id, a.text
        FROM articles a
        LEFT JOIN article_chunks c ON c.article_id = a.id
        WHERE c.id IS NULL
          AND a.text IS NOT NULL
          AND a.text <> ''
        ORDER BY a.id ASC
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (limit,))
        return list(cur.fetchall())

def insert_chunks(conn, article_id: int, chunks: List[str]) -> int:
    """
    Įrašo chunkus į article_chunks.
    Idempotentiška per UNIQUE(article_id, chunk_index).
    chunk_hash čia darom iš (article_id, chunk_index, chunk_text), kad nesprogtų nuo global UNIQUE(chunk_hash).
    """
    if not chunks:
        return 0

    inserted = 0
    sql = """
        INSERT IGNORE INTO article_chunks (article_id, chunk_index, chunk_text, chunk_hash)
        VALUES (%s, %s, %s, %s)
    """

    with conn.cursor() as cur:
        for idx, chunk_text in enumerate(chunks):
            # hash input įtraukiam article_id + idx, kad būtų unikalus (nes pas tave chunk_hash yra UNIQUE globaliai)
            h = md5_bin16(f"{article_id}:{idx}:{chunk_text}")
            cur.execute(sql, (article_id, idx, chunk_text, h))
            inserted += cur.rowcount  # 1 jei įrašė, 0 jei ignoravo
    return inserted


# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Chunk articles into article_chunks table.")
    parser.add_argument("--limit", type=int, default=50, help="Kiek straipsnių apdoroti per vieną run (default: 50)")
    parser.add_argument("--target-chars", type=int, default=1500, help="Target chunk dydis simboliais (default: 1500)")
    parser.add_argument("--max-chars", type=int, default=2200, help="Max chunk dydis simboliais (default: 2200)")
    parser.add_argument("--overlap-paras", type=int, default=1, help="Kiek paskutinių pastraipų persidengia (default: 1)")
    args = parser.parse_args()

    required_env = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [k for k in required_env if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Missing env vars: {', '.join(missing)}")

    conn = db_connect()
    try:
        articles = fetch_articles_without_chunks(conn, args.limit)
        if not articles:
            print("[chunker] No articles without chunks. Nothing to do.")
            return

        total_articles = 0
        total_chunks = 0

        for (article_id, text) in articles:
            text = normalize_text(text)
            if not text:
                continue

            paras = split_paragraphs(text)
            chunks = build_chunks(
                paragraphs=paras,
                target_chars=args.target_chars,
                max_chars=args.max_chars,
                overlap_paras=args.overlap_paras,
            )

            inserted = insert_chunks(conn, article_id, chunks)
            conn.commit()

            total_articles += 1
            total_chunks += inserted
            print(f"[chunker] article_id={article_id} chunks={len(chunks)} inserted={inserted}")

        print(f"[chunker] Done. articles_processed={total_articles} chunks_inserted={total_chunks}")

    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
