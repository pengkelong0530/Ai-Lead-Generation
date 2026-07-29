"""MySQL connection manager with connection pool and CRUD operations."""

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Optional

import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool

from config import config
from models.company import Company, CompanyCreate, CompanyStatus
from models.contact import Contact, ContactCreate
from models.email import EmailSequence, EmailSequenceCreate, EmailStatus
from models.score import AgentReasoning, AgentReasoningRecord


class MySQLManager:
    """Manages MySQL connection pool and all database operations."""

    def __init__(self) -> None:
        self._pool: Optional[MySQLConnectionPool] = None

    # ---- Connection Management ------------------------------------------------

    def connect(self) -> None:
        """Initialize connection pool."""
        if self._pool is not None:
            return
        self._pool = MySQLConnectionPool(
            pool_name="lead_gen_pool",
            pool_size=5,
            pool_reset_session=True,
            host=config.mysql.host,
            port=config.mysql.port,
            user=config.mysql.user,
            password=config.mysql.password,
            database=config.mysql.database,
        )

    def close(self) -> None:
        """Close the connection pool."""
        self._pool = None

    @contextmanager
    def _get_connection(self) -> Generator[Any, None, None]:
        """Get a connection from the pool with context manager."""
        if self._pool is None:
            raise RuntimeError(
                "MySQL pool not initialized. Call connect() first."
            )
        conn = self._pool.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ---- Sessions ------------------------------------------------------------

    def create_session(self, session_id: str, user_input: str) -> None:
        """Create a new session record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (id, user_input, status) VALUES (%s, %s, 'active')",
                (session_id, user_input),
            )

    def complete_session(self, session_id: str) -> None:
        """Mark a session as completed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET status = 'completed' WHERE id = %s",
                (session_id,),
            )

    # ---- Companies -----------------------------------------------------------

    def save_company(self, company: CompanyCreate) -> int:
        """Insert a new company. Returns the new ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO companies
                   (name, industry, region, website, description,
                    employee_count, revenue_estimate, technology_focus,
                    score, source, confidence, status, session_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    company.name,
                    company.industry,
                    company.region,
                    company.website,
                    company.description,
                    company.employee_count,
                    company.revenue_estimate,
                    company.technology_focus,
                    company.score,
                    company.source,
                    company.confidence,
                    company.status.value,
                    company.session_id,
                ),
            )
            return cursor.lastrowid

    def get_company_by_name(self, name: str) -> Optional[Company]:
        """Look up a company by name. Returns None if not found."""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM companies WHERE name = %s", (name,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_company(row)

    def update_company_status(self, company_id: int, status: CompanyStatus) -> None:
        """Update a company's development status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE companies SET status = %s WHERE id = %s",
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
        """List companies with optional filters. Returns (companies, total_count)."""
        conditions = ["1=1"]
        params: list[Any] = []

        if status is not None:
            conditions.append("status = %s")
            params.append(status.value)
        if region is not None:
            conditions.append("region LIKE %s")
            params.append(f"%{region}%")
        if min_score > 0:
            conditions.append("score >= %s")
            params.append(min_score)

        where = " AND ".join(conditions)

        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            # Total count
            cursor.execute(f"SELECT COUNT(*) as cnt FROM companies WHERE {where}", params)
            total = cursor.fetchone()["cnt"]

            # Paginated results
            cursor.execute(
                f"SELECT * FROM companies WHERE {where} ORDER BY score DESC LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
            rows = cursor.fetchall()

        companies = [self._row_to_company(r) for r in rows]
        return companies, total

    def export_to_csv(self, file_path: str) -> None:
        """Export companies table to CSV."""
        import csv

        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM companies ORDER BY score DESC")
            rows = cursor.fetchall()

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
                writer.writerow(row)

    # ---- Contacts ------------------------------------------------------------

    def save_contact(self, contact: ContactCreate) -> int:
        """Insert a new contact. Returns the new ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO contacts
                   (company_id, email, phone, contact_page_url, linkedin_url, verified)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    contact.company_id,
                    contact.email,
                    contact.phone,
                    contact.contact_page_url,
                    contact.linkedin_url,
                    contact.verified,
                ),
            )
            return cursor.lastrowid

    def get_contacts_by_company(self, company_id: int) -> list[Contact]:
        """Get all contacts for a company."""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM contacts WHERE company_id = %s", (company_id,)
            )
            rows = cursor.fetchall()
        return [self._row_to_contact(r) for r in rows]

    # ---- Email Sequences -----------------------------------------------------

    def save_email_sequence(self, email: EmailSequenceCreate) -> int:
        """Insert a new email sequence record. Returns the new ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO email_sequences
                   (company_id, sequence_no, subject, body, scheduled_day, status)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    email.company_id,
                    email.sequence_no,
                    email.subject,
                    email.body,
                    email.scheduled_day,
                    email.status.value,
                ),
            )
            return cursor.lastrowid

    def update_email_status(self, email_id: int, status: EmailStatus) -> None:
        """Update email delivery status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE email_sequences SET status = %s WHERE id = %s",
                (status.value, email_id),
            )

    def get_email_sequences(self, company_id: int) -> list[EmailSequence]:
        """Get all email sequences for a company, ordered by sequence_no."""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM email_sequences WHERE company_id = %s ORDER BY sequence_no",
                (company_id,),
            )
            rows = cursor.fetchall()
        return [self._row_to_email(r) for r in rows]

    # ---- Agent Reasoning (Q4: transparency log) ------------------------------

    def save_reasoning_log(self, record: AgentReasoning) -> int:
        """Record one step of agent reasoning. Returns the new ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO agent_reasoning
                   (session_id, node, input_text, output_text, confidence, reasoning)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    record.session_id,
                    record.node,
                    record.input_text,
                    record.output_text,
                    record.confidence,
                    record.reasoning,
                ),
            )
            return cursor.lastrowid

    def get_reasoning_logs(
        self, session_id: str, limit: int = 100
    ) -> list[AgentReasoningRecord]:
        """Get reasoning logs for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """SELECT * FROM agent_reasoning
                   WHERE session_id = %s ORDER BY created_at LIMIT %s""",
                (session_id, limit),
            )
            rows = cursor.fetchall()
        return [AgentReasoningRecord(**r) for r in rows]

    # ---- Internal helpers ----------------------------------------------------

    # ---- Chat History (for memory) -------------------------------------------

    def add_chat_message(
        self, session_id: str, message_type: str, message_json: str
    ) -> None:
        """Store a chat history message."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO chat_history
                   (session_id, message_type, message_json, created_at)
                   VALUES (%s, %s, %s, %s)""",
                (session_id, message_type, message_json, datetime.utcnow()),
            )

    def get_chat_messages(self, session_id: str) -> list[dict]:
        """Fetch chat messages for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """SELECT message_json FROM chat_history
                   WHERE session_id = %s ORDER BY id ASC""",
                (session_id,),
            )
            return cursor.fetchall()

    def clear_chat_history(self, session_id: str) -> None:
        """Delete all chat messages for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM chat_history WHERE session_id = %s",
                (session_id,),
            )

    # ---- Internal helpers ----------------------------------------------------

    @staticmethod
    def _row_to_company(row: dict) -> Company:
        row["status"] = CompanyStatus(row["status"])
        return Company(**row)

    @staticmethod
    def _row_to_contact(row: dict) -> Contact:
        return Contact(**row)

    @staticmethod
    def _row_to_email(row: dict) -> EmailSequence:
        row["status"] = EmailStatus(row["status"])
        return EmailSequence(**row)
