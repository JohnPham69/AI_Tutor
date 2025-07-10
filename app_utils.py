from streamlit_cookies_controller import CookieController
import streamlit as st

def get_cookie_controller():
    controller_key = "global_cookie_controller"

    if controller_key not in st.session_state:
        # Only create it once per app session
        controller = CookieController()
        try:
            controller.refresh()
        except Exception:
            pass
        st.session_state[controller_key] = controller

    return st.session_state[controller_key]
