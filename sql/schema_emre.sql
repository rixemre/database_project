-- Lords (ana tablo)
CREATE TABLE lords (
  lord_id       SERIAL PRIMARY KEY,       -- internal pk
  ext_id        VARCHAR(128) UNIQUE,      -- wiki slug (eşleşme için)
  clan_id       INTEGER,                  -- FK -> clans (ekip arkadaşın)
  name          VARCHAR(200) NOT NULL,
  gender        VARCHAR(20),
  age           INTEGER,
  culture_id    INTEGER,                  -- FK -> cultures
  level         INTEGER,
  sp_per_lvl    INTEGER,
  sum_stats     INTEGER,
  traits        TEXT,                     -- raw traits yedeği
  source_url    TEXT NOT NULL
);

-- Lord_Skills (N:N eşleşme gibi düşün; lord x skill)
CREATE TABLE lord_skills (
  lord_id   INTEGER NOT NULL,
  skill_id  INTEGER NOT NULL,             -- FK -> skills
  value     INTEGER,
  PRIMARY KEY (lord_id, skill_id)
);

-- Lord_Traits (çok-değerli alanı normalize ettik)
CREATE TABLE lord_traits (
  lord_id INTEGER NOT NULL,
  trait   VARCHAR(100) NOT NULL,
  PRIMARY KEY (lord_id, trait)
);
