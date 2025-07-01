import streamlit as st
from streamlit_cookies_controller import CookieController

def get_cookie_controller():
    """
    Returns a singleton CookieController instance for the entire app
    by storing it in the session_state. This avoids CachedWidgetWarning.
    """
    if 'cookie_controller' not in st.session_state:
        st.session_state.cookie_controller = CookieController()
    return st.session_state.cookie_controller