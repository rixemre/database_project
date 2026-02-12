-- ======================================================
-- MOUNT & BLADE II: BANNERLORD DATABASE SCHEMA
-- ======================================================
-- This schema uses "Class Table Inheritance" (Normalization).
-- The 'Items' table stores shared attributes, while sub-tables 
-- (Armors, Weapons, etc.) store type-specific technical data.
-- ======================================================

-- ------------------------------------------------------
-- 1. CLEANUP: Drop dependent tables before main tables
-- ------------------------------------------------------

DROP TABLE IF EXISTS Shields;
DROP TABLE IF EXISTS Mounts;
DROP TABLE IF EXISTS Ranged_Weapons;
DROP TABLE IF EXISTS Melee_Weapons;
DROP TABLE IF EXISTS Armors;
DROP TABLE IF EXISTS Items;
DROP TABLE IF EXISTS Item_Types;
DROP TABLE IF EXISTS Culture_Types;

SET FOREIGN_KEY_CHECKS = 1; -- Re-enable checks

-- ------------------------------------------------------
-- 2. REFERENCE TABLES
-- ------------------------------------------------------

-- Culture_Types: Defines faction origins (e.g., Empire, Sturgia, Battania)
CREATE TABLE Culture_Types (
    Culture_Type_ID INT AUTO_INCREMENT PRIMARY KEY,
    Culture_Type_Name VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

-- Item_Types: Defines categories (e.g., One Handed Sword, Body Armor, Horse)
CREATE TABLE Item_Types (
    Item_Type_ID INT AUTO_INCREMENT PRIMARY KEY,
    Item_Type_Name VARCHAR(50) NOT NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------
-- 3. MAIN ITEM TABLE (Supertype)
-- ------------------------------------------------------

-- Items: Contains data common to every physical object in the game.
CREATE TABLE Items (
    Item_ID INT AUTO_INCREMENT PRIMARY KEY,
    Item_Type_ID INT NOT NULL,  -- Reference to the category
    Culture_ID INT NOT NULL,     -- Reference to the origin
    Item_Name VARCHAR(100) NOT NULL,
    Weight DECIMAL(5,2),         -- Weight in game units
    Civilian VARCHAR(10),        -- 'Yes' if usable in town centers
    FOREIGN KEY (Item_Type_ID) REFERENCES Item_Types(Item_Type_ID),
    FOREIGN KEY (Culture_ID) REFERENCES Culture_Types(Culture_Type_ID)
) ENGINE=InnoDB;

-- ------------------------------------------------------
-- 4. SPECIALIZED SUB-TABLES (Subtypes)
-- ------------------------------------------------------
-- Note: Item_ID is both the Primary Key and a Foreign Key 
-- to ensure a 1:1 relationship with the Items table.

-- Melee_Weapons: Stats for swords, axes, maces, and polearms.
CREATE TABLE Melee_Weapons (
    Item_ID INT PRIMARY KEY,
    Tier INT,               -- Crafting/Quality tier (1-6)
    Swing_Speed INT NULL,        -- Attack speed for side strikes
    Swing_Damage INT NULL,       -- Damage value for side strikes
    Thrust_Speed INT NULL,       -- Attack speed for stabs
    Thrust_Damage INT NULL,      -- Damage value for stabs
    Length INT,             -- Weapon reach
    Handling INT,           -- Precision and recovery speed
    Merchandise VARCHAR(15),-- Indicates if it appears in shops
    FOREIGN KEY (Item_ID) REFERENCES Items(Item_ID) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Ranged_Weapons: Stats for bows, crossbows, and thrown weapons.
CREATE TABLE Ranged_Weapons (
    Item_ID INT PRIMARY KEY,
    Tier INT,
    Skill INT NULL,              -- Required skill level (Bow/Crossbow)
    Draw_Speed INT NULL,         -- How fast the weapon readies
    Damage INT,             -- Projectile damage
    Accuracy INT,           -- Shot precision
    Missile_Speed INT,      -- Projectile velocity
    Usable_on_Horseback VARCHAR(10),
    Reload_on_Horseback VARCHAR(10),
    Reload_Speed INT,
    FOREIGN KEY (Item_ID) REFERENCES Items(Item_ID) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Armors: Defensive gear for the head, body, arms, and legs.
CREATE TABLE Armors (
    Item_ID INT PRIMARY KEY,
    Leg_Armor_Rating INT,
    Body_Armor_Rating INT,
    Arm_Armor_Rating INT,
    Head_Armor_Rating INT,
    Armor_Rating INT,       -- Base average rating
    Total_Armor_Rating INT, -- Combined defensive value
    Material VARCHAR(50),   -- (e.g., Cloth, Leather, Mail, Plate)
    Merchandise VARCHAR(10),
    FOREIGN KEY (Item_ID) REFERENCES Items(Item_ID) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Shields: Protective gear used to block melee and ranged attacks.
CREATE TABLE Shields (
    Item_ID INT PRIMARY KEY,
    Durability INT,         -- Shield HP
    Resistance INT,         -- Defense against shield-breaking
    Size INT,               -- Blocking coverage area
    Speed INT,              -- How fast the shield is raised
    Base_Value INT,         -- Economic value
    Merchandise VARCHAR(10),
    FOREIGN KEY (Item_ID) REFERENCES Items(Item_ID) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Mounts: Stats for horses and camels.
CREATE TABLE Mounts (
    Item_ID INT PRIMARY KEY,
    Riding INT,             -- Required Riding skill
    Tier INT,
    Charge INT,             -- Damage dealt when trampling enemies
    Speed INT,              -- Top movement speed
    Maneuver INT,           -- Turning and agility
    HP INT,                 -- Health of the animal
    Mount_Type VARCHAR(50), -- (e.g., War Horse, Pack Animal, Camel)
    Weight_Bonus DECIMAL(5,2), -- Additional carrying capacity
    FOREIGN KEY (Item_ID) REFERENCES Items(Item_ID) ON DELETE CASCADE
) ENGINE=InnoDB;