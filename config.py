"""Global configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fall back to .env.example for documentation defaults
    example_path = Path(__file__).resolve().parent / ".env.example"
    if example_path.exists():
        load_dotenv(example_path)


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = field(default_factory=lambda: os.getenv("DEFAULT_LLM", "openai"))
    model: str = field(default_factory=lambda: os.getenv("DEFAULT_MODEL", "gpt-4o"))
    temperature: float = field(
        default_factory=lambda: float(os.getenv("TEMPERATURE", "0.3"))
    )
    base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", ""))

    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def anthropic_api_key(self) -> str:
        return os.getenv("ANTHROPIC_API_KEY", "")


@dataclass
class SearchConfig:
    """Search provider configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("TAVILY_API_KEY", ""))
    max_results: int = field(
        default_factory=lambda: int(os.getenv("MAX_SEARCH_RESULTS", "20"))
    )
    bing_api_key: str = field(default_factory=lambda: os.getenv("BING_API_KEY", ""))
    google_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    google_cx: str = field(default_factory=lambda: os.getenv("GOOGLE_CX", ""))


@dataclass
class MySQLConfig:
    """MySQL connection configuration."""
    host: str = field(default_factory=lambda: os.getenv("MYSQL_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("MYSQL_PORT", "3306")))
    user: str = field(default_factory=lambda: os.getenv("MYSQL_USER", "root"))
    password: str = field(default_factory=lambda: os.getenv("MYSQL_PASSWORD", ""))
    database: str = field(default_factory=lambda: os.getenv("MYSQL_DATABASE", "ai_lead_generation"))

    @property
    def dsn(self) -> str:
        """Return MySQL connection string."""
        return f"host={self.host} port={self.port} user={self.user} password={self.password} database={self.database}"


@dataclass
class AppConfig:
    """Application-level configuration."""
    demo_mode: bool = field(
        default_factory=lambda: os.getenv("DEMO_MODE", "false").lower() == "true"
    )
    db_type: str = field(default_factory=lambda: os.getenv("DB_TYPE", "auto").lower())


@dataclass
class Config:
    """Aggregate configuration root."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    mysql: MySQLConfig = field(default_factory=MySQLConfig)
    app: AppConfig = field(default_factory=AppConfig)


# Singleton config instance
config = Config()
