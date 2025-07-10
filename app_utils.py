import streamlit as st
from streamlit_cookies_controller import CookieController

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
