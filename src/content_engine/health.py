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
    """Check if Claude OAuth token is valid by running a simple prompt.

    Returns (ok, message) tuple. On failure, message includes re-auth hint.
    """
    try:
        result = subprocess.run(
            ["claude", "-p", "Say OK", "--bare", "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=30,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return True, "OAuth token valid"

        output = (result.stderr + result.stdout).lower()
        if "not logged in" in output or "login" in output or "not authenticated" in output:
            return False, "OAuth token expired — run 'claude /login' to re-authenticate"

        return False, f"Claude CLI error: {(result.stderr or result.stdout).strip()}"
    except subprocess.TimeoutExpired:
        return False, "Claude CLI timeout — token check took too long"
    except FileNotFoundError:
        return False, "Claude CLI not installed (expected in Docker)"
    except Exception as e:
        return False, str(e)


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
