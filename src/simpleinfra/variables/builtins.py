"""Built-in variables available in every SimpleInfra task.

These are computed at runtime and include timestamps,
dates, and other dynamic values.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone


def get_builtins() -> dict[str, str]:
    """Return all built-in variables."""
    now = datetime.now(timezone.utc)
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timestamp": str(int(time.time())),
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
    }
