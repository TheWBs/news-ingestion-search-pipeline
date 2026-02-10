CREATE TABLE IF NOT EXISTS sources (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  domain VARCHAR(255) NOT NULL,
  UNIQUE KEY uq_sources_domain (domain)
);

CREATE TABLE IF NOT EXISTS topics (
  id INT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(64) NOT NULL,
  name VARCHAR(128) NOT NULL,
  UNIQUE KEY uq_topics_code (code)
);

CREATE TABLE IF NOT EXISTS urls (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source_id INT NOT NULL,
  url TEXT NOT NULL,
  url_hash BINARY(16) NOT NULL,
  status ENUM('queued','fetching','fetched','failed') NOT NULL DEFAULT 'queued',
  priority INT NOT NULL DEFAULT 0,
  attempts INT NOT NULL DEFAULT 0,
  next_fetch_at DATETIME NULL,
  discovered_from_url_id BIGINT NULL,
  last_error VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_urls_hash (url_hash),
  KEY ix_urls_status_next (status, next_fetch_at),
  CONSTRAINT fk_urls_source FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS fetches (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  url_id BIGINT NOT NULL,
  http_status INT NULL,
  content_type VARCHAR(255) NULL,
  final_url TEXT NULL,
  response_ms INT NULL,
  error_type VARCHAR(32) NULL,
  error_message VARCHAR(255) NULL,
  body MEDIUMTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_fetches_url_id (url_id),
  CONSTRAINT fk_fetches_url FOREIGN KEY (url_id) REFERENCES urls(id)
);

CREATE TABLE IF NOT EXISTS articles (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source_id INT NOT NULL,
  url_id BIGINT NOT NULL,
  canonical_url TEXT NOT NULL,
  title TEXT NOT NULL,
  published_at DATETIME NULL,
  author VARCHAR(255) NULL,
  topic_id INT NULL,
  text MEDIUMTEXT NOT NULL,
  text_hash BINARY(16) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_articles_text_hash (text_hash),
  KEY ix_articles_published (published_at),
  CONSTRAINT fk_articles_source FOREIGN KEY (source_id) REFERENCES sources(id),
  CONSTRAINT fk_articles_url FOREIGN KEY (url_id) REFERENCES urls(id),
  CONSTRAINT fk_articles_topic FOREIGN KEY (topic_id) REFERENCES topics(id)
);
