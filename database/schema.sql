CREATE DATABASE IF NOT EXISTS face_security_db;
USE face_security_db;

CREATE TABLE IF NOT EXISTS users (
    user_id             INT AUTO_INCREMENT PRIMARY KEY,
    full_name           VARCHAR(100) NOT NULL,
    employee_id         VARCHAR(50) UNIQUE,
    department          VARCHAR(100),
    role                ENUM('admin','staff','student','visitor') DEFAULT 'staff',
    image_path          VARCHAR(255),
    face_encoding_path  VARCHAR(255),
    email               VARCHAR(150) UNIQUE,
    phone               VARCHAR(20),
    status              ENUM('active','inactive','suspended') DEFAULT 'active',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS login_credentials (
    login_id        INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(80) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            ENUM('admin','user') DEFAULT 'user',
    user_id         INT,
    is_active       TINYINT(1) DEFAULT 1,
    failed_attempts INT DEFAULT 0,
    last_login      DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS entry_logs (
    log_id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT,
    name             VARCHAR(100) DEFAULT 'Unknown',
    camera_id        INT DEFAULT 0,
    camera_label     VARCHAR(80),
    entry_date       DATE NOT NULL,
    entry_time       TIME NOT NULL,
    status           ENUM('known','unknown','spoofing_attempt') DEFAULT 'known',
    confidence_score FLOAT,
    snapshot_path    VARCHAR(255),
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id      INT AUTO_INCREMENT PRIMARY KEY,
    alert_type    ENUM('unknown_face','spoofing_attempt','multiple_faces','low_confidence','system_error') DEFAULT 'unknown_face',
    camera_id     INT DEFAULT 0,
    camera_label  VARCHAR(80),
    snapshot_path VARCHAR(255),
    alert_date    DATE NOT NULL,
    alert_time    TIME NOT NULL,
    is_reviewed   TINYINT(1) DEFAULT 0,
    reviewed_by   INT,
    notes         TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reviewed_by) REFERENCES login_credentials(login_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS cameras (
    camera_id    INT AUTO_INCREMENT PRIMARY KEY,
    camera_index INT DEFAULT 0,
    label        VARCHAR(80) DEFAULT 'Camera 0',
    location     VARCHAR(120),
    is_active    TINYINT(1) DEFAULT 1,
    added_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_settings (
    setting_id    INT AUTO_INCREMENT PRIMARY KEY,
    setting_key   VARCHAR(80) NOT NULL UNIQUE,
    setting_value VARCHAR(255) NOT NULL,
    description   TEXT,
    updated_at    DATETIME ON UPDATE CURRENT_TIMESTAMP
);

-- Default admin: password is Admin@123
INSERT IGNORE INTO login_credentials (username, password_hash, role)
VALUES ('admin', '$2b$12$KIXnNPXWzG5j1VQGmk8sPuqiFpT8Lk0cN3.RfZt6BEWDpnS1xHUWC', 'admin');

INSERT IGNORE INTO cameras (camera_index, label, location)
VALUES (0, 'Main Entrance', 'Front Gate');

INSERT IGNORE INTO system_settings (setting_key, setting_value, description) VALUES
('recognition_tolerance', '0.50', 'Face match tolerance'),
('liveness_required',     '1',    'Require liveness check'),
('alert_sound',           '1',    'Sound on unknown face'),
('low_light_enhancement', '1',    'Auto brightness fix'),
('session_timeout_min',   '30',   'Session timeout minutes'),
('max_login_attempts',    '5',    'Max failed logins');