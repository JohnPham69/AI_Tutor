import streamlit as st
from streamlit_cookies_controller import CookieController

controller = CookieController()

def setVal(name, val):
    controller.set(name, val)
    
def get_cookie_controller():
    controller = CookieController()
    try:        
        controller.refresh()
    except Exception:
        pass
    return controller

def getVal(val):
    return controller.get(val)
