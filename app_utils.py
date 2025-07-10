import streamlit as st
from streamlit_cookies_controller import CookieController

def get_cookie_controller():
    try:        
        controller = CookieController()
        controller.refresh()
    except Exception:
        pass
    return controller
