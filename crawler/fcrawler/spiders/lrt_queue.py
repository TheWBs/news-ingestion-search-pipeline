import os
import time
import json
import pymysql
import scrapy
from datetime import datetime, timezone

# ✅ LRT SOURCE WHITELIST (tik šitos šaknys)
LRT_ALLOWED_ROOTS = [
    "https://www.lrt.lt/naujienos/lietuvoje",
    "https://www.lrt.lt/naujienos/verslas",
    "https://www.lrt.lt/naujienos/pasaulyje",
    "https://www.lrt.lt/naujienos/mokslas-ir-it",
]

# ✅ URL blacklist (papildomas filtras – net jei kur nors praslystų linkai)
BAD_URL_SUBSTRINGS = (
    "/sportas", "/kultura", "/gyvenimas", "/pramogos",
    "/video", "/fotogalerija", "/tiesiogiai", "/live", "/muzika",
    "/tavo-lrt", "/eismas", "/verslo-pozicija", "/sveikata",
    "/laisvalaikis", "/svietimas", "/nuomones",
)


class LrtQueueSpider(scrapy.Spider):
    name = "lrt_queue"

    custom_settings = {
        "DOWNLOAD_TIMEOUT": 20,
        "RETRY_TIMES": 2,
        "REDIRECT_ENABLED": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 0.5,
        "AUTOTHROTTLE_MAX_DELAY": 5.0,
        "ROBOTSTXT_OBEY": True,
        "LOG_LEVEL": "INFO",
    }

    # ---------- DB ----------
    def _db(self):
        return pymysql.connect(
            host=os.environ["DB_HOST"],
            port=int(os.environ.get("DB_PORT", "3306")),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"],
            charset="utf8mb4",
            autocommit=True,
        )

    # ---------- Scrapy entry ----------
    def start_requests(self):
        conn = self._db()
        try:
            self._reset_stuck_fetching(conn)

            next_row = self._claim_next_url(conn)
            if not next_row:
                self.logger.info("No queued URLs.")
                return

            url_id, url = next_row
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={"url_id": url_id, "start_ms": int(time.time() * 1000)},
            )
        finally:
            conn.close()

    def parse(self, response):
        url_id = response.meta["url_id"]
        start_ms = response.meta["start_ms"]
        elapsed = int(time.time() * 1000) - start_ms

        # ✅ Hard guard: jei out-of-scope (pvz. DB liko šiukšlių) – neapdorojam
        if not self._is_allowed_url(response.url):
            conn = self._db()
            try:
                self._mark_fetched(conn, url_id, response.url)  # kad nebesuktų
            finally:
                conn.close()
            return

        conn = self._db()
        try:
            self._save_fetch(conn, url_id, response, elapsed)
            self._mark_fetched(conn, url_id, response.url)

            new_urls = self._extract_lrt_links(response)
            self._enqueue_urls(conn, new_urls, discovered_from_url_id=url_id)

            if self._looks_like_article(response):
                title = self._extract_title(response)
                text = self._extract_article_text(response)
                published_at = self._extract_published_at(response)
                author = self._extract_author(response)

                self._save_article(
                    conn,
                    source_id=1,
                    url_id=url_id,
                    canonical_url=response.url,
                    title=title,
                    published_at=published_at,
                    author=author,
                    text=text,
                )

            next_row = self._claim_next_url(conn)
            if next_row:
                next_id, next_url = next_row
                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse,
                    meta={"url_id": next_id, "start_ms": int(time.time() * 1000)},
                )
            else:
                self.logger.info("Queue empty.")
        finally:
            conn.close()

    # ---------- Queue / status ----------
    def _reset_stuck_fetching(self, conn):
        with conn.cursor() as cur:
            cur.execute("UPDATE urls SET status='queued' WHERE status='fetching'")

    def _claim_next_url(self, conn):
        # ✅ DB-level whitelist: imam tik URL po allowed roots
        likes = [root + "%" for root in LRT_ALLOWED_ROOTS]
        where_like = " OR ".join(["url LIKE %s"] * len(likes))

        sql = f"""
            SELECT id, url
            FROM urls
            WHERE status='queued'
              AND (next_fetch_at IS NULL OR next_fetch_at <= NOW())
              AND ({where_like})
            ORDER BY priority DESC, id ASC
            LIMIT 1
        """

        with conn.cursor() as cur:
            cur.execute(sql, likes)
            row = cur.fetchone()
            if not row:
                return None

            url_id, url = row
            cur.execute(
                "UPDATE urls SET status='fetching', attempts=attempts+1 WHERE id=%s",
                (url_id,),
            )
            return url_id, url

    def _mark_fetched(self, conn, url_id, response_url: str):
        # entrypoint’ai (priority>=10) – refetch; straipsniai – fetched once
        with conn.cursor() as cur:
            cur.execute("SELECT priority FROM urls WHERE id=%s", (url_id,))
            row = cur.fetchone()
            priority = int(row[0]) if row else 0

            if priority >= 10:
                cur.execute(
                    "UPDATE urls SET status='queued', next_fetch_at = NOW() + INTERVAL 15 MINUTE WHERE id=%s",
                    (url_id,),
                )
            else:
                cur.execute("UPDATE urls SET status='fetched' WHERE id=%s", (url_id,))

    def _enqueue_urls(self, conn, urls, discovered_from_url_id):
        if not urls:
            return
        with conn.cursor() as cur:
            for u in urls:
                cur.execute(
                    """
                    INSERT IGNORE INTO urls (source_id, url, url_hash, status, priority, discovered_from_url_id)
                    VALUES (1, %s, UNHEX(MD5(%s)), 'queued', 0, %s)
                    """,
                    (u, u, discovered_from_url_id),
                )

    # ---------- URL filters ----------
    def _is_allowed_url(self, url: str) -> bool:
        if not url.startswith("https://www.lrt.lt/"):
            return False
        if any(bad in url for bad in BAD_URL_SUBSTRINGS):
            return False
        return any(url.startswith(root) for root in LRT_ALLOWED_ROOTS)

    def _extract_lrt_links(self, response):
        links = response.css("a::attr(href)").getall()
        out = []

        for href in links:
            if not href:
                continue
            url = response.urljoin(href).split("#")[0]

            if not self._is_allowed_url(url):
                continue

            out.append(url)

        return list(set(out))

    # ---------- Article detection / extraction ----------
    def _looks_like_article(self, response) -> bool:
        url = response.url
        bad = ("/fotogalerija", "/video", "/tiesiogiai", "/live")
        if any(x in url for x in bad):
            return False

        if not response.css("article"):
            return False

        title = self._extract_title(response)
        text = self._extract_article_text(response)
        if not title or not text:
            return False
        if len(text) < 300:
            return False

        return True

    def _extract_title(self, response):
        t = response.css("article h1::text, h1::text").get()
        return t.strip() if t else None

    def _extract_article_text(self, response):
        paras = response.css("article p::text").getall()
        text = "\n".join([p.strip() for p in paras if p and p.strip()])
        return text if text else None

    # ---------- published_at / author (meta + JSON-LD) ----------
    def _parse_iso_datetime_to_utc_naive(self, s: str):
        if not s:
            return None
        s = s.strip()
        try:
            # handle "Z"
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                # jei be timezone – paliekam kaip local-naive (geriau nei NULL)
                return dt
            dt_utc = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt_utc
        except Exception:
            return None

    def _extract_published_at(self, response):
        # 1) OpenGraph
        og = response.css('meta[property="article:published_time"]::attr(content)').get()
        dt = self._parse_iso_datetime_to_utc_naive(og)
        if dt:
            return dt

        # 2) JSON-LD
        for obj in self._extract_jsonld_objects(response):
            val = obj.get("datePublished") or obj.get("dateCreated")
            if isinstance(val, str):
                dt = self._parse_iso_datetime_to_utc_naive(val)
                if dt:
                    return dt

        # 3) fallback (never NULL if you want): use fetch time is not available here, so return None
        return None

    def _extract_author(self, response):
        # 1) meta author
        a = response.css('meta[name="author"]::attr(content)').get()
        if a and a.strip():
            return a.strip()

        # 2) JSON-LD
        for obj in self._extract_jsonld_objects(response):
            auth = obj.get("author")
            name = None
            if isinstance(auth, dict):
                name = auth.get("name")
            elif isinstance(auth, list):
                # take first author name if list
                for it in auth:
                    if isinstance(it, dict) and it.get("name"):
                        name = it.get("name")
                        break
                    if isinstance(it, str) and it.strip():
                        name = it.strip()
                        break
            elif isinstance(auth, str):
                name = auth

            if name and str(name).strip():
                return str(name).strip()

        # 3) fallback
        return "LRT.lt"

    def _extract_jsonld_objects(self, response):
        out = []
        scripts = response.css('script[type="application/ld+json"]::text').getall()
        for s in scripts:
            if not s:
                continue
            s = s.strip()
            try:
                data = json.loads(s)
                if isinstance(data, dict):
                    out.append(data)
                elif isinstance(data, list):
                    out.extend([x for x in data if isinstance(x, dict)])
            except Exception:
                continue
        return out

    # ---------- Fetch save ----------
    def _save_fetch(self, conn, url_id, response, elapsed_ms):
        body = response.text
        MAX_CHARS = 200_000
        if body and len(body) > MAX_CHARS:
            body = body[:MAX_CHARS]

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fetches (url_id, http_status, content_type, final_url, response_ms, body)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    url_id,
                    response.status,
                    response.headers.get("Content-Type", b"").decode("utf-8", "ignore"),
                    response.url,
                    elapsed_ms,
                    body,
                ),
            )

    # ---------- Article save ----------
    def _save_article(self, conn, source_id, url_id, canonical_url, title, published_at, author, text):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO articles (source_id, url_id, canonical_url, title, published_at, author, text, text_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, UNHEX(MD5(%s)))
                ON DUPLICATE KEY UPDATE
                  title = VALUES(title),
                  published_at = VALUES(published_at),
                  author = VALUES(author),
                  text = VALUES(text),
                  updated_at = CURRENT_TIMESTAMP
                """,
                (source_id, url_id, canonical_url, title, published_at, author, text, text),
            )
