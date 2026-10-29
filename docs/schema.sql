CREATE TABLE item (
    id INTEGER NOT NULL AUTO_INCREMENT,
    title VARCHAR(100) NOT NULL,
    category VARCHAR(30) NOT NULL,
    description TEXT NULL,
    location_found VARCHAR(150) NOT NULL,
    date_found DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    finder_contact VARCHAR(120) NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    INDEX ix_item_status (status),
    INDEX ix_item_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE claim (
    id INTEGER NOT NULL AUTO_INCREMENT,
    item_id INTEGER NOT NULL,
    claimant_name VARCHAR(100) NOT NULL,
    claimant_contact VARCHAR(120) NOT NULL,
    proof_description TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    INDEX ix_claim_item_id (item_id),
    CONSTRAINT fk_claim_item
        FOREIGN KEY (item_id) REFERENCES item (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
