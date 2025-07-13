import os
import json
import logging
from typing import Any, Dict, Optional
from getpass import getpass
from supabase import create_client, Client

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "supabase_config.json")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "apktool_logs")

supabase: Optional[Client] = None


def load_supabase_config() -> None:
    """Load credentials from config file if environment variables are not set."""
    global SUPABASE_URL, SUPABASE_KEY, SUPABASE_TABLE
    if (SUPABASE_URL and SUPABASE_KEY) or not os.path.exists(CONFIG_FILE):
        return
    try:
        with open(CONFIG_FILE, "r") as cfg:
            data = json.load(cfg)
        SUPABASE_URL = data.get("SUPABASE_URL", SUPABASE_URL)
        SUPABASE_KEY = data.get("SUPABASE_KEY", SUPABASE_KEY)
        SUPABASE_TABLE = data.get("SUPABASE_TABLE", SUPABASE_TABLE)
        os.environ.setdefault("SUPABASE_URL", SUPABASE_URL or "")
        os.environ.setdefault("SUPABASE_KEY", SUPABASE_KEY or "")
        os.environ.setdefault("SUPABASE_TABLE", SUPABASE_TABLE)
        logger.info("Loaded Supabase configuration from %s", CONFIG_FILE)
    except Exception as e:
        logger.error("Failed to load Supabase config: %s", e)


def init_supabase() -> Optional[Client]:
    """Initialize the Supabase client using environment variables."""
    global supabase
    load_supabase_config()
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            supabase = None
    else:
        logger.warning("Supabase credentials not configured")
    return supabase


def log_result(tool_name: str, params: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Log the tool invocation result to Supabase if configured."""
    if supabase is None:
        return
    try:
        supabase.table(SUPABASE_TABLE).insert({
            "tool": tool_name,
            "params": json.dumps(params),
            "result": json.dumps(result),
            "success": bool(result.get("success"))
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log result to Supabase: {e}")


def run_setup_wizard() -> None:
    """Interactive wizard to configure Supabase credentials."""
    print("\n=== Supabase Setup Wizard ===")
    url = input(
        "Enter your Supabase project URL (e.g., https://xyz.supabase.co): "
    ).strip()
    while not url.startswith("http"):
        print("Invalid URL. Please include the https:// prefix.")
        url = input("Supabase project URL: ").strip()

    key = getpass("Enter your Supabase API key (hidden): ").strip()
    while not key:
        print("API key cannot be empty.")
        key = getpass("Supabase API key: ").strip()

    table = input("Table for log storage [apktool_logs]: ").strip() or "apktool_logs"

    config = {
        "SUPABASE_URL": url,
        "SUPABASE_KEY": key,
        "SUPABASE_TABLE": table,
    }

    try:
        with open(CONFIG_FILE, "w") as cfg:
            json.dump(config, cfg, indent=2)
        print(f"Configuration saved to {CONFIG_FILE}.")
    except Exception as exc:
        print(f"Failed to save configuration: {exc}")


if __name__ == "__main__":
    run_setup_wizard()



