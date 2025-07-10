import streamlit as st


def setVal(controller, name, val):
    controller.set(name, val)
    
def get_cookie_controller(controller):
    controller = CookieController()
    try:        
        controller.refresh()
    except Exception:
        pass
    return controller

def getVal(controller, val):
    return controller.get(val)
