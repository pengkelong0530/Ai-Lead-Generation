-- AI Lead Generation Agent - MySQL Schema
-- Run this script to initialize the database:
--   mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS ai_lead_generation
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ai_lead_generation;

-- ============================================================
-- Sessions: track each user interaction session
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_input TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active', 'completed') NOT NULL DEFAULT 'active',
    INDEX idx_sessions_status (status),
    INDEX idx_sessions_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Companies: enterprise information warehouse with dedup by name
-- ============================================================
CREATE TABLE IF NOT EXISTS companies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    industry VARCHAR(100) DEFAULT NULL,
    region VARCHAR(100) DEFAULT NULL,
    website VARCHAR(500) DEFAULT NULL,
    description TEXT DEFAULT NULL,
    employee_count VARCHAR(50) DEFAULT NULL,
    revenue_estimate VARCHAR(100) DEFAULT NULL,
    technology_focus VARCHAR(255) DEFAULT NULL,
    score INT NOT NULL DEFAULT 0 COMMENT 'ICP matching score 0-100',
    source VARCHAR(50) DEFAULT NULL COMMENT 'Search source: Google, Bing, IHK, LinkedIn',
    confidence DECIMAL(5,2) DEFAULT NULL COMMENT 'Data accuracy confidence 0.00-1.00',
    status ENUM('待开发', '跟进中', '已转化', '无效') NOT NULL DEFAULT '待开发',
    session_id VARCHAR(64) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_companies_status (status),
    INDEX idx_companies_region (region),
    INDEX idx_companies_industry (industry),
    INDEX idx_companies_score (score),
    INDEX idx_companies_session (session_id),
    CONSTRAINT fk_companies_session FOREIGN KEY (session_id) REFERENCES sessions(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Contacts: contact information for each company
-- ============================================================
CREATE TABLE IF NOT EXISTS contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    email VARCHAR(255) DEFAULT NULL,
    phone VARCHAR(50) DEFAULT NULL,
    contact_page_url VARCHAR(500) DEFAULT NULL,
    linkedin_url VARCHAR(500) DEFAULT NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_contacts_company (company_id),
    INDEX idx_contacts_verified (verified),
    CONSTRAINT fk_contacts_company FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Email Sequences: multi-step follow-up email tracking
-- ============================================================
CREATE TABLE IF NOT EXISTS email_sequences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    sequence_no INT NOT NULL COMMENT 'Email position in sequence (1, 2, 3...)',
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    scheduled_day INT NOT NULL COMMENT 'Day to send: 1, 3, 7, etc.',
    status ENUM('待发送', '已发送', '已回复', '退回') NOT NULL DEFAULT '待发送',
    sent_at DATETIME DEFAULT NULL,
    opened_at DATETIME DEFAULT NULL,
    replied_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email_company (company_id),
    INDEX idx_email_status (status),
    CONSTRAINT fk_email_company FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Agent Reasoning: transparency log of agent decision-making (Q4)
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_reasoning (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(64) DEFAULT NULL,
    node VARCHAR(50) NOT NULL COMMENT 'Pipeline node name',
    input_text TEXT DEFAULT NULL COMMENT 'Input to this node',
    output_text TEXT DEFAULT NULL COMMENT 'Output from this node',
    confidence DECIMAL(5,2) DEFAULT NULL COMMENT 'Confidence 0.00-1.00',
    reasoning TEXT DEFAULT NULL COMMENT 'Free-text explanation',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_reasoning_session (session_id),
    INDEX idx_reasoning_node (node),
    CONSTRAINT fk_reasoning_session FOREIGN KEY (session_id) REFERENCES sessions(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
