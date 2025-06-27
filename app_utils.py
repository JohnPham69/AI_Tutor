import streamlit as st
from streamlit_cookies_controller import CookieController

@st.cache_resource
def get_cookie_controller():
    """
    Returns a singleton CookieController instance for the entire app.
    @st.cache_resource ensures this function runs only once per session
    and the same controller is returned on subsequent calls across all pages.
    """
    return CookieController()