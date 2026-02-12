-- Troops
CREATE TABLE IF NOT EXISTS Troops (
  troop_id     INTEGER PRIMARY KEY,
  name         TEXT NOT NULL,
  tier         INTEGER NOT NULL,
  wage         INTEGER NOT NULL,
  is_mounted   INTEGER NOT NULL,
  culture_id   INTEGER,
  FOREIGN KEY (culture_id) REFERENCES Culture_Types(Culture_Type_ID)
    ON DELETE SET NULL
    ON UPDATE CASCADE
);

-- Troop_Skills (one row per troop, wide skill columns)
CREATE TABLE IF NOT EXISTS Troop_Skills (
  troop_id     INTEGER PRIMARY KEY,
  one_handed   INTEGER NOT NULL DEFAULT 0,
  two_handed   INTEGER NOT NULL DEFAULT 0,
  polearm      INTEGER NOT NULL DEFAULT 0,
  bow          INTEGER NOT NULL DEFAULT 0,
  crossbow     INTEGER NOT NULL DEFAULT 0,
  throwing     INTEGER NOT NULL DEFAULT 0,
  riding       INTEGER NOT NULL DEFAULT 0,
  athletics    INTEGER NOT NULL DEFAULT 0,
  tactics      INTEGER NOT NULL DEFAULT 0,
  scouting     INTEGER NOT NULL DEFAULT 0,
  roguery      INTEGER NOT NULL DEFAULT 0,
  charm        INTEGER NOT NULL DEFAULT 0,
  leadership   INTEGER NOT NULL DEFAULT 0,
  trade        INTEGER NOT NULL DEFAULT 0,
  steward      INTEGER NOT NULL DEFAULT 0,
  medicine     INTEGER NOT NULL DEFAULT 0,
  engineering  INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (troop_id) REFERENCES Troops(troop_id)
    ON DELETE CASCADE
);

-- Troop_Upgrade_Paths (same shape as your data)
CREATE TABLE IF NOT EXISTS Troop_Upgrade_Paths (
  base_troop_id     INTEGER NOT NULL,
  upgraded_troop_id INTEGER NOT NULL,
  xp_cost           INTEGER NOT NULL,
  PRIMARY KEY (base_troop_id, upgraded_troop_id),
  FOREIGN KEY (base_troop_id) REFERENCES Troops(troop_id)
    ON DELETE CASCADE,
  FOREIGN KEY (upgraded_troop_id) REFERENCES Troops(troop_id)
    ON DELETE CASCADE
);

-- Troop_Equipment_Junction (FIXED: slot is now VARCHAR with fixed length)
CREATE TABLE IF NOT EXISTS Troop_Equipment_Junction (
  troop_id INTEGER NOT NULL,
  item_id  INTEGER NOT NULL,
  slot     VARCHAR(50) NOT NULL,
  PRIMARY KEY (troop_id, item_id, slot),
  FOREIGN KEY (troop_id) REFERENCES Troops(troop_id) 
    ON DELETE CASCADE,
  FOREIGN KEY (item_id) REFERENCES Items(item_id) 
    ON DELETE CASCADE
);