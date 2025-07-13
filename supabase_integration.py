import os
import json
import logging
from typing import Any, Dict, Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "apktool_logs")

supabase: Optional[Client] = None


def init_supabase() -> Optional[Client]:
    """Initialize the Supabase client using environment variables."""
    global supabase
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


