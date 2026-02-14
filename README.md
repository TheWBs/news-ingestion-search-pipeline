# AI_assistant
AI-based assistant to identify different forms of misleading content. (DI grįstas asistentas skirtingoms klaidinančio turinio formoms atpažinti)

# PVP Crawler

## Requirements
- Docker  
- Docker Compose  

---

## Configuration

`.env` faile gali keisti:

```env
CRAWL_EVERY_MIN=15        # kas kiek minučių paleisti crawlerį
CLOSESPIDER_PAGECOUNT=50  # kiek fetchų vieno paleidimo metu
```

jei pakeiti .env paleidimas:
```
docker compose down
docker compose up -d
```

## Komandos
#### Run:
docker compose up -d
#### Logai:
docker compose logs -f
#### Manual run (testavimui):
docker compose run --rm crawler scrapy crawl lrt_queue -s CLOSESPIDER_PAGECOUNT=20
#### Stop:
docker compose down

