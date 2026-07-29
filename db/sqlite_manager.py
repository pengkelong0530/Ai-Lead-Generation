"""SQLite database manager for zero-config deployment.

Implements the same public interface as MySQLManager so both can be
used interchangeably via the DB factory in db/__init__.py.

Auto-creates all tables on first connect. Uses WAL mode for performance.
"""

import csv
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional

from models.company import Company, CompanyCreate, CompanyStatus
from models.contact import Contact, ContactCreate
from models.email import EmailSequence, EmailSequenceCreate, EmailStatus
from models.score import AgentReasoning, AgentReasoningRecord


class SQLiteManager:
    """SQLite backend for the lead generation agent.

    Usage:
        db = SQLiteManager()
        db.connect()
        company_id = db.save_company(...)
        db.close()
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._conn: Optional[sqlite3.Connection] = None
        self._db_path = db_path or os.getenv(
            "SQLITE_PATH",
            str(Path(__file__).resolve().parent.parent / "lead_gen.db"),
        )

    # ---- Connection Management ------------------------------------------------

    def connect(self) -> None:
        """Open SQLite connection and create tables."""
        if self._conn is not None:
            return
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def close(self) -> None:
        """Close the connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextmanager
    def _get_connection(self) -> Generator[Any, None, None]:
        """Get connection with context manager (same interface as MySQLManager)."""
        if self._conn is None:
            raise RuntimeError(
                "SQLite not initialized. Call connect() first."
            )
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def _create_tables(self) -> None:
        """Create all tables if they don't exist."""
        assert self._conn is not None
        cursor = self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_input TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            status TEXT NOT NULL DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            industry TEXT,
            region TEXT,
            website TEXT,
            description TEXT,
            employee_count TEXT,
            revenue_estimate TEXT,
            technology_focus TEXT,
            score INTEGER NOT NULL DEFAULT 0,
            source TEXT,
            confidence REAL,
            status TEXT NOT NULL DEFAULT '待开发',
            session_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            email TEXT,
            phone TEXT,
            contact_page_url TEXT,
            linkedin_url TEXT,
            verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS email_sequences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            sequence_no INTEGER NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            scheduled_day INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT '待发送',
            sent_at TEXT,
            opened_at TEXT,
            replied_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS agent_reasoning (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            node TEXT NOT NULL,
            input_text TEXT,
            output_text TEXT,
            confidence REAL,
            reasoning TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message_type TEXT NOT NULL,
            message_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status);
        CREATE INDEX IF NOT EXISTS idx_companies_region ON companies(region);
        CREATE INDEX IF NOT EXISTS idx_companies_score ON companies(score);
        CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_id);
        CREATE INDEX IF NOT EXISTS idx_email_company ON email_sequences(company_id);
        CREATE INDEX IF NOT EXISTS idx_reasoning_session ON agent_reasoning(session_id);
        CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id);
        """)

    # ---- Sessions ------------------------------------------------------------

    def create_session(self, session_id: str, user_input: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (id, user_input, status) VALUES (?, ?, 'active')",
                (session_id, user_input),
            )

    def complete_session(self, session_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET status = 'completed' WHERE id = ?",
                (session_id,),
            )

    # ---- Companies -----------------------------------------------------------

    def save_company(self, company: CompanyCreate) -> int:
        with self._get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO companies
                   (name, industry, region, website, description,
                    employee_count, revenue_estimate, technology_focus,
                    score, source, confidence, status, session_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    company.name, company.industry, company.region,
                    company.website, company.description,
                    company.employee_count, company.revenue_estimate,
                    company.technology_focus, company.score, company.source,
                    company.confidence, company.status.value, company.session_id,
                ),
            )
            return cur.lastrowid

    def get_company_by_name(self, name: str) -> Optional[Company]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM companies WHERE name = ?", (name,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_company(dict(row))

    def update_company_status(self, company_id: int, status: CompanyStatus) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE companies SET status = ?, updated_at = datetime('now') WHERE id = ?",
                (status.value, company_id),
            )

    def list_companies(
        self,
        status: Optional[CompanyStatus] = None,
        region: Optional[str] = None,
        min_score: int = 0,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Company], int]:
        conditions = ["1=1"]
        params: list[Any] = []
        if status:
            conditions.append("status = ?")
            params.append(status.value)
        if region:
            conditions.append("region LIKE ?")
            params.append(f"%{region}%")
        if min_score > 0:
            conditions.append("score >= ?")
            params.append(min_score)
        where = " AND ".join(conditions)

        with self._get_connection() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) as cnt FROM companies WHERE {where}", params
            ).fetchone()["cnt"]
            rows = conn.execute(
                f"SELECT * FROM companies WHERE {where} ORDER BY score DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
        companies = [self._row_to_company(dict(r)) for r in rows]
        return companies, total

    def export_to_csv(self, file_path: str) -> None:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM companies ORDER BY score DESC"
            ).fetchall()
        if not rows:
            return
        fieldnames = [
            "id", "name", "industry", "region", "website", "description",
            "employee_count", "revenue_estimate", "technology_focus",
            "score", "source", "confidence", "status", "created_at", "updated_at",
        ]
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

    # ---- Contacts ------------------------------------------------------------

    def save_contact(self, contact: ContactCreate) -> int:
        with self._get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO contacts
                   (company_id, email, phone, contact_page_url, linkedin_url, verified)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (contact.company_id, contact.email, contact.phone,
                 contact.contact_page_url, contact.linkedin_url,
                 int(contact.verified)),
            )
            return cur.lastrowid

    def get_contacts_by_company(self, company_id: int) -> list[Contact]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM contacts WHERE company_id = ?", (company_id,)
            ).fetchall()
        return [Contact(**dict(r)) for r in rows]

    # ---- Email Sequences -----------------------------------------------------

    def save_email_sequence(self, email: EmailSequenceCreate) -> int:
        with self._get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO email_sequences
                   (company_id, sequence_no, subject, body, scheduled_day, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (email.company_id, email.sequence_no, email.subject,
                 email.body, email.scheduled_day, email.status.value),
            )
            return cur.lastrowid

    def update_email_status(self, email_id: int, status: EmailStatus) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE email_sequences SET status = ? WHERE id = ?",
                (status.value, email_id),
            )

    def get_email_sequences(self, company_id: int) -> list[EmailSequence]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM email_sequences WHERE company_id = ? ORDER BY sequence_no",
                (company_id,),
            ).fetchall()
        return [self._row_to_email(dict(r)) for r in rows]

    # ---- Agent Reasoning (Q4) -------------------------------------------------

    def save_reasoning_log(self, record: AgentReasoning) -> int:
        with self._get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO agent_reasoning
                   (session_id, node, input_text, output_text, confidence, reasoning)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (record.session_id, record.node, record.input_text,
                 record.output_text, record.confidence, record.reasoning),
            )
            return cur.lastrowid

    def get_reasoning_logs(
        self, session_id: str, limit: int = 100
    ) -> list[AgentReasoningRecord]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM agent_reasoning WHERE session_id = ? ORDER BY created_at LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [AgentReasoningRecord(**dict(r)) for r in rows]

    # ---- Chat History (for memory) -------------------------------------------

    def add_chat_message(
        self, session_id: str, message_type: str, message_json: str
    ) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_history (session_id, message_type, message_json) VALUES (?, ?, ?)",
                (session_id, message_type, message_json),
            )

    def get_chat_messages(self, session_id: str) -> list[dict]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT message_json FROM chat_history WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def clear_chat_history(self, session_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM chat_history WHERE session_id = ?", (session_id,)
            )

    # ---- Internal helpers ----------------------------------------------------

    @staticmethod
    def _row_to_company(row: dict) -> Company:
        row["status"] = CompanyStatus(row["status"])
        return Company(**row)

    @staticmethod
    def _row_to_email(row: dict) -> EmailSequence:
        row["status"] = EmailStatus(row["status"])
        return EmailSequence(**row)
