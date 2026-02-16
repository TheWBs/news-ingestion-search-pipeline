# AI_assistant

AI-based assistant to identify different forms of misleading content.\
(DI grįstas asistentas skirtingoms klaidinančio turinio formoms
atpažinti)

------------------------------------------------------------------------

# Architecture

Sistema dabar veikia kaip pilnas pipeline:

Crawler → Chunker → Embedder → Search

`pipeline_scheduler` servisas automatiškai:

1.  Paleidžia crawlerį
2.  Sukuria chunk'us naujiems straipsniams
3.  Sugeneruoja embeddings
4.  Užmiega X minučių
5.  Kartoja ciklą

Visa tai vyksta su viena komanda.

------------------------------------------------------------------------

# Requirements

-   Docker
-   Docker Compose

------------------------------------------------------------------------

# Configuration

`.env` faile gali keisti:

``` env
# --- Crawler ---
CRAWL_EVERY_MIN=15
CLOSESPIDER_PAGECOUNT=50

# --- Chunking ---
CHUNK_LIMIT=200
CHUNK_TARGET_CHARS=1800
CHUNK_MAX_CHARS=2600
CHUNK_OVERLAP_PARAS=1

# --- Embeddings ---
EMBED_MODEL=intfloat/multilingual-e5-small
EMBED_LIMIT=200
EMBED_BATCH_SIZE=16
EMBED_DEVICE=
EMBED_NORMALIZE=1
EMBED_PREFIX=passage:
```

## Pastabos

-   `EMBED_DEVICE=` palik tuščią jei nori auto (CPU).
-   Nerekomenduojama:
    -   `EMBED_LIMIT > 200`
    -   `EMBED_BATCH_SIZE > 16`

Gali per daug apkrauti CPU.

------------------------------------------------------------------------

## Jei pakeitei `.env`

    docker compose down
    docker compose up -d

------------------------------------------------------------------------

# Main Commands

## Paleisti visą sistemą

    docker compose up -d

Tai paleidžia: - DB - Adminer - Pipeline scheduler (crawl + chunk +
embed loop)

------------------------------------------------------------------------

## Logai

Rekomenduojama:

    docker compose logs -f pipeline_scheduler

Jei nori visų servisų logų:

    docker compose logs -f

------------------------------------------------------------------------

## Sustabdyti

    docker compose down

Jei keitei servisų pavadinimus:

    docker compose up -d --remove-orphans

------------------------------------------------------------------------

# Manual Run (Testavimui)

## Tik crawler:

    docker compose run --rm crawler scrapy crawl lrt_queue -s CLOSESPIDER_PAGECOUNT=20

## Tik chunker:

    docker compose run --rm crawler python chunker.py --limit 200 --target-chars 1800 --max-chars 2600 --overlap-paras 1

-   `limit` -- kiek straipsnių chunkina per vieną paleidimą

## Tik embedder:

    docker compose run --rm crawler python embedder.py --normalize --limit 100 --batch-size 16

-   `limit` -- kiek chunk'ų embeddina per vieną paleidimą
-   `batch-size` -- kiek vienu metu siunčia modeliui

------------------------------------------------------------------------

# Search

    docker compose run --rm crawler python search.py "Seimas padidino PVM 2024 metais" --topk 10 --limit 5000 --normalize-query

-   `topk` -- kiek geriausių rezultatų grąžina
-   `limit` -- kiek embeddingų analizuoja
-   `--normalize-query` -- rekomenduojama jei naudotas normalize
    embeddinant

------------------------------------------------------------------------


# Important

-   Jei kažkurio kintamojo nepaaiškinau -- geriau jo nekeisti :P


------------------------------------------------------------------------

JOKŪBAS OUT