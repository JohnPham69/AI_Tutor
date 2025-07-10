import streamlit as st
from streamlit_cookies_controller import CookieController
from streamlit_cookies_manager import CookieManager

def get_cookie_controller():
    # Use a single, fixed key for the cookie controller to ensure it's a singleton.
    # This avoids dynamic key generation issues and conflicts with Streamlit's widget state.
    controller_key = "global_cookie_controller"
    if controller_key not in st.session_state:
        # When instantiating the controller, we do NOT pass a 'key' argument.
        # Passing a 'key' to a component can cause Streamlit to register it as a widget,
        # which leads to the error when we then try to assign it to session_state manually.
        st.session_state[controller_key] = CookieController()
    return st.session_state[controller_key]

def get_cookies_manager():
    manage_key = "global_cookie_manager"
    if manage_key not in st.session_state:
        # When instantiating the controller, we do NOT pass a 'key' argument.
        # Passing a 'key' to a component can cause Streamlit to register it as a widget,
        # which leads to the error when we then try to assign it to session_state manually.
        st.session_state[manage_key] = CookieManager()
    # This should be on top of your script
    return st.session_state[manage_key]
