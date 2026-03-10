"""Simple password authentication for the Streamlit Content Hub."""

import hmac
import time

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minutes
SESSION_TIMEOUT_SECONDS = 3600  # 1 hour


def verify_password(entered: str, expected: str) -> bool:
    """Constant-time password comparison to prevent timing attacks."""
    return hmac.compare_digest(entered, expected)


def check_password() -> bool:
    """Show login form and return True if authenticated.

    Uses st.secrets["password"] for the expected password.
    Must be called from within a Streamlit app context.
    Includes brute-force protection and session expiry.
    """
    import streamlit as st

    # Session expiry check
    if st.session_state.get("authenticated"):
        login_time = st.session_state.get("login_time", 0)
        if time.time() - login_time > SESSION_TIMEOUT_SECONDS:
            st.session_state.authenticated = False
            st.session_state.pop("login_time", None)
            st.info("Session expired. Please log in again.")
        else:
            return True

    st.title("Gita Valley Content Hub")
    st.markdown("Please enter the access password to continue.")

    # Brute-force protection
    attempts = st.session_state.get("login_attempts", 0)
    lockout_until = st.session_state.get("lockout_until", 0)

    if time.time() < lockout_until:
        remaining = int(lockout_until - time.time())
        st.error(f"Too many failed attempts. Try again in {remaining} seconds.")
        return False

    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if verify_password(password, st.secrets["password"]):
            st.session_state.authenticated = True
            st.session_state.login_time = time.time()
            st.session_state.login_attempts = 0
            st.session_state.pop("lockout_until", None)
            st.rerun()
        else:
            attempts += 1
            st.session_state.login_attempts = attempts
            if attempts >= MAX_ATTEMPTS:
                st.session_state.lockout_until = time.time() + LOCKOUT_SECONDS
                st.error(
                    f"Too many failed attempts. Locked out for {LOCKOUT_SECONDS // 60} minutes."
                )
            else:
                remaining = MAX_ATTEMPTS - attempts
                st.error(f"Incorrect password. {remaining} attempt(s) remaining.")

    return False
