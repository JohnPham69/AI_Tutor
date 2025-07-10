import streamlit as st
from streamlit_cookies_controller import CookieController

def get_cookie_controller():
    controller = CookieController()
    try:        
        controller.refresh()
    except Exception:
        pass
    return controller

def getVal(controller, val):
    return controller.get(val)
