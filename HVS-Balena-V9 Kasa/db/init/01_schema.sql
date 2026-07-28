-- Esquema de la base de datos de reportes de armado (Hollymatic Vision System).
--
-- Este script lo ejecuta automáticamente la imagen oficial de MySQL al
-- inicializar un volumen de datos VACÍO (se monta en
-- /docker-entrypoint-initdb.d/). NO se vuelve a ejecutar si el volumen
-- db_data ya tiene datos: para reaplicar el esquema hay que borrar el volumen.
--
-- Modelo (normalizado):
--   mandatory_assemblies : catálogo de las 5 piezas obligatorias.
--   attempts             : un registro por cada corrida de turn_on_button.
--   bad_assemblies       : una fila por cada pieza mal armada de un intento.

CREATE TABLE IF NOT EXISTS mandatory_assemblies (
  id     INT AUTO_INCREMENT PRIMARY KEY,
  name   VARCHAR(64) NOT NULL UNIQUE,        -- clave de config_models.MANDATORY_ASSEMBLY
  type   INT NOT NULL,                       -- código numérico de la pieza (1..5)
  enable TINYINT NOT NULL DEFAULT 1          -- 1 = pieza obligatoria actualmente
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS attempts (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  is_bad    TINYINT NOT NULL,                -- 0 = armado correcto / 1 = con falla
  timestamp DATETIME NOT NULL,               -- instante exacto del intento
  date      DATE NOT NULL,                   -- fecha del intento (para reportes por día)
  INDEX idx_attempts_ts (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bad_assemblies (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  attempt_id   INT NOT NULL,                 -- FK -> attempts.id
  type         INT NOT NULL,                 -- FK -> mandatory_assemblies.id
  bad_assembly TINYINT NOT NULL DEFAULT 1,   -- 1 = esta pieza salió mal armada
  CONSTRAINT fk_bad_attempt FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE,
  CONSTRAINT fk_bad_type    FOREIGN KEY (type)       REFERENCES mandatory_assemblies(id),
  INDEX idx_bad_attempt (attempt_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Catálogo de las 5 piezas obligatorias. Los nombres DEBEN coincidir
-- exactamente con las claves de config_models.MANDATORY_ASSEMBLY
-- (app/src/configs/configmodels.py) para que el repositorio mapee name -> id.
INSERT INTO mandatory_assemblies (name, type, enable) VALUES
  ('RAM_ASSEMBLY_AND_DRIVE_BAR', 1, 1),
  ('LOCK_SHAFT_ASSAMBLY',        2, 1),
  ('KOCUP_KOARM_AND_MOLDPLATE',  3, 1),
  ('ECCENTRIC_LEVER',            4, 1),
  ('TUMBLER',                    5, 1)
ON DUPLICATE KEY UPDATE name = VALUES(name);
