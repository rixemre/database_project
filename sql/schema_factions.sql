DROP TABLE IF EXISTS factions;
DROP TABLE IF EXISTS clans;

CREATE TABLE factions (
    faction_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    banner_key VARCHAR(255),
    leader_id VARCHAR(128),
    culture_id INT NOT NULL,
    ruling_clan_id VARCHAR(50),
    FOREIGN KEY (leader_id) REFERENCES lords(ext_id) ON DELETE SET NULL,
    FOREIGN KEY (culture_id) REFERENCES Culture_Types(Culture_Type_ID)
) ENGINE=InnoDB;

CREATE TABLE clans (
    clan_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100),
    tier INT,
    banner_key VARCHAR(255),
    leader_id VARCHAR(128),
    faction_id VARCHAR(50),
    FOREIGN KEY (leader_id) REFERENCES lords(ext_id) ON DELETE SET NULL,
    FOREIGN KEY (faction_id) REFERENCES factions(faction_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Add Ruling Clan FK after Clans table exists
ALTER TABLE factions 
ADD CONSTRAINT fk_faction_ruling_clan 
FOREIGN KEY (ruling_clan_id) REFERENCES clans(clan_id) ON DELETE SET NULL;