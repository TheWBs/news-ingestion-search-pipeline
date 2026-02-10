# PVP Crawler

## Requirements
- Docker + Docker Compose

## Run
1. Start:
   docker compose up -d
2. Logs:
   docker compose logs -f

## Crawler:
1. Run
   docker compose run --rm crawler scrapy crawl lrt_queue -s CLOSESPIDER_PAGECOUNT=20

   (CLOSESPIDER_PAGECOUNT nustato kiek padaro fetchu)

## Stop
docker compose down