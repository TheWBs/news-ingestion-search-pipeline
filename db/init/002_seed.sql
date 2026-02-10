INSERT IGNORE INTO sources (id, name, domain) VALUES (1, 'LRT', 'lrt.lt');

INSERT IGNORE INTO topics (code, name) VALUES
('politika','Politika / valdžia / vyriausybė'),
('ekonomika','Ekonomika / finansai'),
('saugumas','Saugumas / gynyba / karas'),
('mokslas','Mokslas / IT');

-- URL hash: UNHEX(MD5(url)) -> 16 bytes
INSERT IGNORE INTO urls (source_id, url, url_hash, status, priority)
VALUES
(1, 'https://www.lrt.lt/naujienos/lietuvoje', UNHEX(MD5('https://www.lrt.lt/naujienos/lietuvoje')), 'queued', 10),
(1, 'https://www.lrt.lt/naujienos/verslas', UNHEX(MD5('https://www.lrt.lt/naujienos/verslas')), 'queued', 10),
(1, 'https://www.lrt.lt/naujienos/pasaulyje', UNHEX(MD5('https://www.lrt.lt/naujienos/pasaulyje')), 'queued', 10),
(1, 'https://www.lrt.lt/naujienos/mokslas-ir-it', UNHEX(MD5('https://www.lrt.lt/naujienos/mokslas-ir-it')), 'queued', 10);