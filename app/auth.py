"""Simple password authentication for the Streamlit Content Hub."""

import hmac


def verify_password(entered: str, expected: str) -> bool:
    """Constant-time password comparison to prevent timing attacks."""
    return hmac.compare_digest(entered, expected)


def check_password() -> bool:
    """Show login form and return True if authenticated.

    Uses st.secrets["password"] for the expected password.
    Must be called from within a Streamlit app context.
    """
    import streamlit as st

    if st.session_state.get("authenticated"):
        return True

    st.title("Gita Valley Content Hub")
    st.markdown("Please enter the access password to continue.")

    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if verify_password(password, st.secrets["password"]):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")

    return False
