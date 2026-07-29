"""Database-backed chat message history for LangChain.

Implements LangChain's BaseChatMessageHistory interface so AgentExecutor
can persist conversation context across sessions (Q5).

Works with both MySQL and SQLite backends via the db factory.
"""

import json
from datetime import datetime
from typing import Any, Optional

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    BaseMessage,
    message_to_dict,
    messages_from_dict,
)


class DBChatMessageHistory(BaseChatMessageHistory):
    """Chat message history backed by the database (MySQL or SQLite).

    Usage:
        history = DBChatMessageHistory(session_id="abc123")
        history.add_user_message("Hello")
        history.add_ai_message("Hi there!")
        print(history.messages)
    """

    def __init__(
        self,
        session_id: str,
        db: Any = None,
    ) -> None:
        self.session_id = session_id
        self._db = db

    @property
    def db(self) -> Any:
        """Lazy-init the DB connection via factory."""
        if self._db is None:
            from db import get_db
            db = get_db()
            db.connect()
            self._db = db
        return self._db

    @property
    def messages(self) -> list[BaseMessage]:
        """Retrieve all messages for this session."""
        rows = self._fetch_messages()
        if not rows:
            return []
        dicts = [json.loads(r["message_json"]) for r in rows]
        return messages_from_dict(dicts)

    def add_message(self, message: BaseMessage) -> None:
        """Store a single message."""
        msg_dict = message_to_dict(message)
        self.db.add_chat_message(
            session_id=self.session_id,
            message_type=message.type,
            message_json=json.dumps(msg_dict, ensure_ascii=False),
        )

    def clear(self) -> None:
        """Clear all messages for this session."""
        self.db.clear_chat_history(self.session_id)

    def _fetch_messages(self) -> list[dict[str, Any]]:
        """Fetch message rows from DB."""
        return self.db.get_chat_messages(self.session_id)
