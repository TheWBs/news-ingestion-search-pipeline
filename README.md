# AI_assistant
AI-based assistant to identify different forms of misleading content. (DI grįstas asistentas skirtingoms klaidinančio turinio formoms atpažinti)

# Crawler

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
```
docker compose up -d
```
#### Logai:
```
docker compose logs -f
```
#### Manual run (testavimui):
```
docker compose run --rm crawler scrapy crawl lrt_queue -s CLOSESPIDER_PAGECOUNT=20
```
#### Stop:
```
docker compose down
```

# Chunker
```
docker compose run --rm crawler python chunker.py --limit 200 --target-chars 1800 --max-chars 2600 --overlap-paras 1
```
- limit- kiek straipsniu chunkina per viena karta

# Embedder 
```
docker compose run --rm crawler python embedder.py --normalize --limit 100 --batch-size 16
```
- limit- kiek straipsniu embeddina per viena promta
- batch-size- kiek vienu metu embeddina

nerekomenduoju daryti limito virs 100 ir batch-size virs 16. 
might crash or cook cpu :P

# Search
```
docker compose run --rm crawler python search.py "Seimas padidino PVM 2024 metais" --topk 10 --limit 5000 --normalize-query
```
- topk- kiek grazina top atitinkanciu rezultatu
- limit- kiek skirtingu embeddings analizuoja

# Important
Jei nepaaiskinau kazkurio kintamojo reiskias kad jo keisti negaaalima :P
