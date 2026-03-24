"""Health check utilities for system monitoring."""

import subprocess


def check_sheets_health(sheets_client=None, skip_if_none: bool = False) -> tuple[bool, str]:
    """Check Google Sheets API connectivity.

    Returns (ok, message) tuple.
    """
    if sheets_client is None:
        if skip_if_none:
            return True, "Not configured"
        return False, "Sheets client not provided"

    try:
        sheets_client.get_recent_errors(limit=1)
        return True, "OK"
    except Exception as e:
        return False, str(e)


def check_postiz_health(postiz_client=None) -> tuple[bool, str]:
    """Check Postiz API connectivity.

    Returns (ok, message) tuple.
    """
    if postiz_client is None:
        return True, "Not configured"

    try:
        integrations = postiz_client.list_integrations()
        count = len(integrations)
        return True, f"{count} integration{'s' if count != 1 else ''} connected"
    except Exception as e:
        return False, str(e)


def check_oauth_health() -> tuple[bool, str]:
    """Check if Claude CLI is authenticated.

    Uses 'claude auth status' which returns JSON instantly (< 1s),
    unlike 'claude -p' which loads plugins and takes 30s+.
    """
    try:
        result = subprocess.run(
            ["claude", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
        import json as _json

        data = _json.loads(result.stdout)
        if data.get("loggedIn"):
            method = data.get("authMethod", "unknown")
            return True, f"Authenticated via {method}"
        return False, "Not logged in — run 'claude /login' to authenticate"
    except subprocess.TimeoutExpired:
        return False, "Claude CLI timeout — auth check took too long"
    except FileNotFoundError:
        return False, "Claude CLI not installed"
    except Exception as e:
        return False, f"Auth check failed: {e}"


def check_claude_health() -> tuple[bool, str]:
    """Check Claude CLI availability.

    Returns (ok, message) tuple.
    """
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        return False, f"Exit code {result.returncode}"
    except FileNotFoundError:
        return False, "Claude CLI not installed (expected in Docker)"
    except Exception as e:
        return False, str(e)
