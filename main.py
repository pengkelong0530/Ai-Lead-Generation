"""AI Lead Generation Agent — Entry Point.

Usage:
    # Interactive Streamlit UI (recommended for demo)
    streamlit run main.py

    # One-shot CLI mode
    python main.py --input "我要开发德国刀具行业客户"

    # Demo mode (no API keys required)
    python main.py --demo --input "我要开发德国刀具行业客户"
"""

import argparse
import asyncio
import sys

from config import config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Lead Generation Agent for overseas customer development",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="",
        help="User input for one-shot pipeline mode",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode (mock data, no API calls)",
    )
    parser.add_argument(
        "--streamlit",
        action="store_true",
        help="Launch Streamlit UI (default if no --input given)",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=50,
        help="Minimum ICP score threshold (default: 50)",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database tables and exit",
    )
    return parser.parse_args()


def init_database() -> None:
    """Initialize database (auto-detect MySQL or SQLite)."""
    from db import get_db

    db = get_db()
    db.connect()
    print(f"[DB] Connected ({type(db).__name__})")

    if "MySQL" in type(db).__name__:
        # Run schema.sql for MySQL
        import os
        schema_path = os.path.join(os.path.dirname(__file__), "db", "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            statements = f.read()
        for statement in statements.split(";"):
            stmt = statement.strip()
            if stmt:
                try:
                    with db._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(stmt)
                    print(f"[DB] Executed: {stmt[:60]}...")
                except Exception as e:
                    print(f"[DB] Skipped (may already exist): {e}")

    # Also create chat_history table (SQLite auto-creates; MySQL needs the table)
    try:
        db.add_chat_message("_init_check_", "system", "{}")
        db.clear_chat_history("_init_check_")
        print("[DB] Chat history table ready.")
    except Exception:
        print("[DB] Chat history table may need manual creation in MySQL.")

    print("[DB] Database initialization complete.")
    db.close()


async def run_cli(user_input: str, min_score: int) -> None:
    """Run the full pipeline and print results to console."""
    from agent.supervisor_agent import SupervisorAgent

    print(f"\n🔍 AI Lead Generation Agent")
    print(f"{'=' * 60}")
    print(f"Input: {user_input}")
    print(f"{'=' * 60}\n")

    agent = SupervisorAgent()
    result = await agent.run_pipeline(
        user_input=user_input,
        min_score=min_score,
        auto_confirm=True,
    )

    print(result)


def run_demo(user_input: str) -> None:
    """Run demo mode using mock data."""
    from demo.demo_mode import DemoMode

    print(f"\n🎯 AI Lead Generation Agent — DEMO MODE")
    print(f"{'=' * 60}")
    print(f"Input: {user_input}")
    print(f"{'=' * 60}\n")

    demo = DemoMode(enabled=True)
    report = demo.get_summary_report()
    print(report)

    print("\n📧 Email Preview (Walter AG):")
    print(demo.get_email_preview("Walter AG"))


def run_streamlit() -> None:
    """Launch Streamlit UI."""
    import subprocess
    import sys as _sys

    ui_path = __file__
    cmd = [_sys.executable, "-m", "streamlit", "run", ui_path, "--", "--mode", "ui"]
    print(f"Launching Streamlit UI...")
    subprocess.run(cmd)


async def main() -> None:
    args = parse_args()

    # Handle --init-db separately
    if args.init_db:
        init_database()
        return

    # Handle --demo
    if args.demo:
        demo_input = args.input or "我要开发德国刀具行业客户"
        run_demo(demo_input)
        return

    # Handle --input (one-shot CLI)
    if args.input:
        await run_cli(args.input, args.min_score)
        return

    # Default: check if we should launch Streamlit
    # When run as `streamlit run main.py`, streamlit sets an env var
    import os as _os
    if _os.environ.get("STREAMLIT_RUN") or _os.environ.get("STREAMLIT_RUN_WITH_STREAMLIT"):
        # Streamlit is handling this — import and run the UI module
        from ui.streamlit_app import main as streamlit_main
        streamlit_main()
        return

    # Otherwise print help
    print(
        "AI Lead Generation Agent\n\n"
        "Commands:\n"
        "  streamlit run main.py    Start interactive UI\n"
        "  python main.py -i '...'   One-shot pipeline\n"
        "  python main.py --demo     Demo mode (mock data)\n"
        "  python main.py --init-db  Initialize database\n"
    )


if __name__ == "__main__":
    # Detect if streamlit is running us
    import os as _os
    if _os.environ.get("STREAMLIT_SCRIPT_NAME"):
        # We're in Streamlit process — import and run UI directly
        from ui.streamlit_app import main as streamlit_main
        streamlit_main()
    else:
        asyncio.run(main())
