
DROP TABLE IF EXISTS lord_skills;
DROP TABLE IF EXISTS lord_traits;
DROP TABLE IF EXISTS lords;

CREATE TABLE lords (
  lord_id       INT AUTO_INCREMENT PRIMARY KEY,
  ext_id        VARCHAR(128) UNIQUE,
  clan_id       INT,
  name          VARCHAR(200) NOT NULL,
  gender        VARCHAR(20),
  age           INT,
  
  culture_id    INT,  
  
  level         INT,
  sp_per_lvl    INT,
  sum_stats     INT,
  traits        TEXT,
  source_url    TEXT,


  FOREIGN KEY (culture_id) REFERENCES Culture_Types(Culture_Type_ID)
      ON DELETE SET NULL
      ON UPDATE CASCADE
) ENGINE=InnoDB;


CREATE TABLE lord_traits (
  lord_id INT NOT NULL,
  trait   VARCHAR(100) NOT NULL,
  PRIMARY KEY (lord_id, trait),
  FOREIGN KEY (lord_id) REFERENCES lords(lord_id) ON DELETE CASCADE
) ENGINE=InnoDB;


CREATE TABLE lord_skills (
  lord_id  INT NOT NULL,
  skill_id INT NOT NULL,
  value    INT,
  PRIMARY KEY (lord_id, skill_id),
  FOREIGN KEY (lord_id) REFERENCES lords(lord_id) ON DELETE CASCADE
) ENGINE=InnoDB;