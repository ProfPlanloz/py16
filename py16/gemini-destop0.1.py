import py16
import os # Echtes Python-Modul!

dateien = []

def init():
    global dateien
    # Wir lesen beim Start echte Dateien vom Raspberry Pi!
    try:
        dateien = os.listdir('/home/pi')
    except:
        dateien = ["Fehler beim Lesen"]

def update():
    pass # Hier käme später die Scroll-Logik rein

def draw():
    py16.cls(1) # Dunkelblauer Hintergrund
    py16.rectfill(0, 0, 256, 12, 12) # Blaue Kopfzeile
    py16.text("PI FILE BROWSER", 4, 4, 7)
    
    # Zeige die ersten 15 Dateien auf dem Schirm an
    for i, datei in enumerate(dateien[:15]):
        y_pos = 20 + (i * 12)
        py16.text(datei, 10, y_pos, 6) # Hellgrauer Text

if __name__ == "__main__":
    py16.run(update, draw, init)