# News Ingestion & Semantic Search Pipeline

## Overview

**News Ingestion & Search Pipeline** is an end-to-end Data Engineering
project that implements a production-style data workflow for crawling,
processing, embedding, storing, and semantically searching news
articles.

This project demonstrates practical experience with:

-   Data ingestion at scale
-   ETL design patterns
-   Containerized microservices
-   Relational + vector storage
-   Embedding-based semantic retrieval
-   Queue-driven crawling architecture

The system is built using Dockerized services and follows modular
pipeline design principles common in modern data platforms.

------------------------------------------------------------------------

## Architecture

The project follows a staged data pipeline architecture:

1.  **Data Ingestion Layer**
    -   Web crawler (Scrapy-based)
    -   URL queue management
    -   Incremental crawling
    -   Retry & priority handling
2.  **Raw Storage Layer**
    -   MariaDB
    -   Metadata normalization
    -   Source tracking
3.  **Transformation Layer (ETL)**
    -   Text cleaning
    -   Content normalization
    -   Structured schema enforcement
4.  **Embedding Layer**
    -   Vector embedding generation
    -   Embedding persistence in database
    -   Scalable batch processing
5.  **Search Layer**
    -   Semantic similarity search
    -   Query-to-embedding transformation

This mirrors real-world data platform design used in analytics and
search infrastructure.

------------------------------------------------------------------------

## Key Data Engineering Concepts Demonstrated

-   ETL pipeline design
-   Queue-based ingestion strategy
-   Idempotent crawling
-   Container orchestration with Docker Compose
-   Database schema modeling
-   Data normalization & transformation
-   Batch embedding generation
-   Embeddings similarity search
-   Separation of concerns across services

------------------------------------------------------------------------

## Tech Stack

-   **Python** -- Crawling, transformation, embedding pipeline
-   **Scrapy** -- Web data ingestion
-   **MariaDB** -- Database
-   **Vector embeddings** -- Semantic indexing
-   **Docker & Docker Compose** -- Service orchestration
-   **Adminer** -- Database inspection

------------------------------------------------------------------------

## Data Flow

    URL Queue → Crawler → Raw Article Storage → ETL Processing → Embedding Generation → Vector Storage → Semantic Search

The pipeline is designed to be modular and extensible, allowing new
sources, embedding models, or search strategies to be added without
major refactoring.

------------------------------------------------------------------------

## Project Goals

This project was built to simulate real-world Data Engineering workflows
including:

-   Designing reliable ingestion systems
-   Managing structured and semi-structured data
-   Building scalable transformation pipelines
-   Implementing semantic search capabilities
-   Working with containerized data infrastructure

It focuses on engineering robustness rather than UI-level features.

------------------------------------------------------------------------

## Scalability Considerations

The architecture supports:

-   Horizontal crawler scaling
-   Incremental crawling
-   Batch embedding processing
-   Future migration to distributed vector databases

The system can be extended to support streaming ingestion, distributed
task queues, or cloud deployment.

------------------------------------------------------------------------

## Future Improvements

-   Distributed task queue
-   Vector index optimization
-   Cloud deployment
-   Airflow orchestration
  
------------------------------------------------------------------------

## Author

All development and architecture: **Jokūbas Griežė**, **github.com/TheWBs**\
Initial repository setup: Dark-Rose-404

------------------------------------------------------------------------

## Where is this project used?

This project has been used in a AI based software to detect missleading
information based on Lithuanian article sites.\
It is also used in development of a software meant to help writers cite
souces and information, from different European article sites.


------------------------------------------------------------------------

# Deployment & Operations

## Requirements

-   Docker
-   Docker Compose

------------------------------------------------------------------------

## Configuration

`.env` you can change:

``` env
# --- Crawler ---
CRAWL_EVERY_MIN=15
CLOSESPIDER_PAGECOUNT=50
```
-  `CRAWL_EVERY_MIN` -- How long the pipeline sleeps between cycles
-  `CLOSESPIDER_PAGECOUNT` -- Limit of articles fetched
```

# --- Chunking ---
CHUNK_LIMIT=200
CHUNK_TARGET_CHARS=1800
CHUNK_MAX_CHARS=2600
CHUNK_OVERLAP_PARAS=1
```
-  `CHUNK_LIMIT` -- Amount of articles being chunked

```

# --- Embeddings ---
EMBED_MODEL=intfloat/multilingual-e5-small
EMBED_LIMIT=200
EMBED_BATCH_SIZE=16
EMBED_DEVICE=
EMBED_NORMALIZE=1
EMBED_PREFIX=passage:
```
- `EMBED_MODEL` -- Embedder model
- `EMBED_LIMIT` -- Amount of chunks being embedded during one pipeline cycle
- `EMBED_BATCH_SIZE` --Amount of chunks embedded at the same time

### Pastabos

-   `EMBED_DEVICE=` leave empty for auto (CPU).
-   Not recomended:
    -   `EMBED_LIMIT > 200`
    -   `EMBED_BATCH_SIZE > 32`

It might overload the cpu if working without gpu. 
Feel free to go much higher with a gpu.

------------------------------------------------------------------------

### If you change `.env` run:

    docker compose down
    docker compose up -d

------------------------------------------------------------------------

## Main Commands

### Run all systen

    docker compose up -d

It runs: - DB - Adminer - Pipeline scheduler (crawl + chunk +
embed loop)

------------------------------------------------------------------------

### Logs

Recomended (pipeline logs):

    docker compose logs -f pipeline_scheduler

For all logs:

    docker compose logs -f

------------------------------------------------------------------------

### Stop

    docker compose down

If you changed the names of services:

    docker compose up -d --remove-orphans

------------------------------------------------------------------------

## Manual Run (For testing purposes)

### Only crawler:

    docker compose run --rm crawler scrapy crawl lrt_queue -s CLOSESPIDER_PAGECOUNT=20

### Only chunker:

    docker compose run --rm crawler python chunker.py --limit 200 --target-chars 1800 --max-chars 2600 --overlap-paras 1

-   `limit` -- Amount of articles being chunked

### Tik embedder:

    docker compose run --rm crawler python embedder.py --normalize --limit 100 --batch-size 16

-   `limit` -- Amount of chunks being embedded during one pipeline cycle
-   `batch-size` -- Amount of chunks embedded at the same time

------------------------------------------------------------------------

## Search

    docker compose run --rm crawler python search.py "Seimas padidino PVM 2024 metais" --topk 10 --limit 5000 --normalize-query

-   `topk` -- k amount of results returned
-   `limit` -- Amount of embeddings analysed

------------------------------------------------------------------------

Thanks for reviewing this project.
If you have any questions about the architecture or design decisions, feel free to reach out.
— Jokūbas Griežė


