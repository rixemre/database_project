DROP TABLE IF EXISTS villages;
DROP TABLE IF EXISTS settlements;

CREATE TABLE settlements (
    settlement_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50),
    prosperity FLOAT,
    description VARCHAR(1000),
    lord_id VARCHAR(128),
    faction_id VARCHAR(50),
    culture_id INT,
    FOREIGN KEY (lord_id) REFERENCES lords(ext_id) ON DELETE SET NULL,
    FOREIGN KEY (faction_id) REFERENCES factions(faction_id) ON DELETE SET NULL,
    FOREIGN KEY (culture_id) REFERENCES Culture_Types(Culture_Type_ID) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE villages (
    village_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    hearth FLOAT,
    primary_resource VARCHAR(255),
    description VARCHAR(1000),
    culture_id INT,
    settlement_id VARCHAR(100) NOT NULL,
    FOREIGN KEY (culture_id) REFERENCES Culture_Types(Culture_Type_ID) ON DELETE SET NULL,
    FOREIGN KEY (settlement_id) REFERENCES settlements(settlement_id) ON DELETE CASCADE
) ENGINE=InnoDB;