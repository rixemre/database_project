-- ======================================================
-- MOUNT & BLADE PROJECT - FULL DATABASE SCHEMA
-- ======================================================

SET FOREIGN_KEY_CHECKS = 0;

-- Drop tables if they exist
DROP TABLE IF EXISTS Troop_Upgrade_Paths;
DROP TABLE IF EXISTS Troop_Equipment_Junction;
DROP TABLE IF EXISTS Troops;
DROP TABLE IF EXISTS lord_skills;
DROP TABLE IF EXISTS lord_traits;
DROP TABLE IF EXISTS villages;
DROP TABLE IF EXISTS settlements;
DROP TABLE IF EXISTS clans;
DROP TABLE IF EXISTS factions;
DROP TABLE IF EXISTS lords;
DROP TABLE IF EXISTS Shields;
DROP TABLE IF EXISTS Mounts;
DROP TABLE IF EXISTS Ranged_Weapons;
DROP TABLE IF EXISTS Melee_Weapons;
DROP TABLE IF EXISTS Armors;
DROP TABLE IF EXISTS Items;
DROP TABLE IF EXISTS Item_Types;
DROP TABLE IF EXISTS Skills;
DROP TABLE IF EXISTS Attributes;
DROP TABLE IF EXISTS Culture_Types;

SET FOREIGN_KEY_CHECKS = 1;

-- 1. REFERENCE TABLES (Independent)
CREATE TABLE Culture_Types (
    Culture_Type_ID INT AUTO_INCREMENT PRIMARY KEY,
    Culture_Type_Name VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE Item_Types (
    Item_Type_ID INT AUTO_INCREMENT PRIMARY KEY,
    Item_Type_Name VARCHAR(50) NOT NULL
) ENGINE=InnoDB;

-- 2. ITEMS (Depends on Culture and Item Types)
CREATE TABLE Items (
    Item_ID INT AUTO_INCREMENT PRIMARY KEY,
    Item_Type_ID INT NOT NULL,
    Culture_ID INT NOT NULL,
    Item_Name VARCHAR(100) NOT NULL,
    Weight DECIMAL(5,2),
    Civilian VARCHAR(10),
    FOREIGN KEY (Item_Type_ID) REFERENCES Item_Types(Item_Type_ID),
    FOREIGN KEY (Culture_ID) REFERENCES Culture_Types(Culture_Type_ID)
) ENGINE=InnoDB;

-- 3. ITEM SUB-TYPES (1:1 with Items)
CREATE TABLE Melee_Weapons (
    Item_ID INT PRIMARY KEY,
    Tier INT,
    Swing_Speed INT,
    Swing_Damage INT,
    Thrust_Speed INT,
    Thrust_Damage INT,
    Length INT,
    Handling INT,
    Merchandise VARCHAR(15),
    FOREIGN KEY (Item_ID) REFERENCES Items(Item_ID) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE Ranged_Weapons (
    Item_ID INT PRIMARY KEY,
    Tier INT,
    Skill INT,
    Draw_Speed INT,
    Damage INT,
    Accuracy INT,
    Missile_Speed INT,
    Usable_on_Horseback VARCHAR(10),
    Reload_on_Horseback VARCHAR(10),
    Reload_Speed INT,
    FOREIGN KEY (Item_ID) REFERENCES Items(Item_ID) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE Armors (
    Item_ID INT PRIMARY KEY,
    Leg_Armor_Rating INT,
    Body_Armor_Rating INT,
    Arm_Armor_Rating INT,
    Head_Armor_Rating INT,
    Armor_Rating INT,
    Total_Armor_Rating INT,
    Material VARCHAR(50),
    Merchandise VARCHAR(10),
    FOREIGN KEY (Item_ID) REFERENCES Items(Item_ID) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE Shields (
    Item_ID INT PRIMARY KEY,
    Durability INT,
    Resistance INT,
    Size INT,
    Speed INT,
    Base_Value INT,
    Merchandise VARCHAR(10),
    FOREIGN KEY (Item_ID) REFERENCES Items(Item_ID) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE Mounts (
    Item_ID INT PRIMARY KEY,
    Riding INT,
    Tier INT,
    Charge INT,
    Speed INT,
    Maneuver INT,
    HP INT,
    Mount_Type VARCHAR(50),
    Weight_Bonus DECIMAL(5,2),
    FOREIGN KEY (Item_ID) REFERENCES Items(Item_ID) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4. LORDS (Depends on Culture)
CREATE TABLE lords (
    lord_id INT AUTO_INCREMENT PRIMARY KEY,
    ext_id VARCHAR(128) UNIQUE,
    name VARCHAR(200) NOT NULL,
    gender VARCHAR(20),
    age INT,
    culture_id INT,
    level INT,
    sp_per_lvl INT,
    sum_stats INT,
    traits TEXT,
    source_url TEXT,
    FOREIGN KEY (culture_id) REFERENCES Culture_Types(Culture_Type_ID) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE lord_traits (
    lord_id INT NOT NULL,
    trait VARCHAR(100) NOT NULL,
    PRIMARY KEY (lord_id, trait),
    FOREIGN KEY (lord_id) REFERENCES lords(lord_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE lord_skills (
    lord_id INT NOT NULL,
    skill_id INT NOT NULL,
    value INT,
    PRIMARY KEY (lord_id, skill_id),
    FOREIGN KEY (lord_id) REFERENCES lords(lord_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5. FACTIONS & CLANS (Circular Dependency Handled)
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

-- 6. SETTLEMENTS & VILLAGES
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

-- 7. TROOPS & JUNCTION TABLES
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
) ENGINE=InnoDB;

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
) ENGINE=InnoDB;

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
) ENGINE=InnoDB;

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
) ENGINE=InnoDB;