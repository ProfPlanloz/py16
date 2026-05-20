# Beispiel-Plugin. Frei kopieren/aendern. Eine Datei = eine App.
APP = {"id": "ticker", "name": "TICKER", "w": 120, "h": 72, "resizable": False}

def init(win):
    win["n"] = 0

def update(win, lx, ly, m_pressed, m_sec_pressed, m_held):
    if m_pressed:
        win["n"] = win.get("n", 0) + 1

def draw(win, wx, wy, ww, wh, is_active):
    import py16
    py16.text("HELLO FROM PLUGIN", wx + 6, wy + 18, 1)
    py16.text("CLICKS: " + str(win.get("n", 0)), wx + 6, wy + 32, 8)
    py16.text("EDIT apps/example.py", wx + 6, wy + 48, 5)
