CREATE TABLE IF NOT EXISTS article_chunks (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  article_id BIGINT NOT NULL,
  chunk_index INT NOT NULL,
  chunk_text MEDIUMTEXT NOT NULL,
  chunk_hash BINARY(16) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_article_chunk (article_id, chunk_index),
  UNIQUE KEY uq_chunk_hash (chunk_hash),
  KEY ix_chunks_article (article_id),
  CONSTRAINT fk_chunks_article FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS embeddings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  chunk_id BIGINT NOT NULL,
  model VARCHAR(255) NOT NULL,
  dims INT NOT NULL,
  embedding LONGBLOB NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_embeddings_chunk_model (chunk_id, model),
  KEY ix_embeddings_model (model),
  CONSTRAINT fk_embeddings_chunk FOREIGN KEY (chunk_id) REFERENCES article_chunks(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
