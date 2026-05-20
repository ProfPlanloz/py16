import threading
import urllib.request
import json

APP = {"id": "crypto", "name": "CRYPTO TICKER", "w": 140, "h": 85, "resizable": False}

def fetch_crypto(win, symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        req = urllib.request.Request(url, headers={'User-Agent': 'py-16-os'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Preis auslesen und als Kommazahl formatieren
            price = float(data['price'])
            
            # Schoen formatieren (z.B. $65000.50)
            if price > 10:
                formatted_price = f"${price:,.2f}"
            else:
                formatted_price = f"${price:,.4f}" # Mehr Kommastellen fuer guenstige Coins
                
            win["result"] = formatted_price
    except Exception as e:
        win["result"] = "API FEHLER!"
    
    win["loading"] = False

def init(win):
    # Die Anzeigenamen fuer die UI
    win["coins"] = ["BITCOIN", "ETHEREUM", "SOLANA", "DOGECOIN"]
    
    # Die passenden Symbole fuer die Binance API (Coin + USDT = Dollarwert)
    win["symbols"] = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]
    
    win["c_idx"] = 0
    win["result"] = ""
    win["loading"] = False
    
    # Button-Koordinaten
    win["btn_x"] = 6
    win["btn_y"] = 48
    win["btn_w"] = 38
    win["btn_h"] = 13
    win["btn_hover"] = False

def update(win, lx, ly, m_pressed, m_sec_pressed, m_held):
    import py16
    
    if win.get("loading"): return
    
    bx, by, bw, bh = win["btn_x"], win["btn_y"], win["btn_w"], win["btn_h"]
    win["btn_hover"] = (bx <= lx <= bx + bw and by <= ly <= by + bh)

    do_fetch = False
    
    # --- GAMEPAD / TASTATUR ---
    if py16.btnp('right'):
        win["c_idx"] = (win["c_idx"] + 1) % len(win["coins"])
        win["result"] = ""
    if py16.btnp('left'):
        win["c_idx"] = (win["c_idx"] - 1) % len(win["coins"])
        win["result"] = ""
        
    if py16.btnp('z') or py16.btnp('enter'):
        do_fetch = True

    # --- MAUS ---
    if m_pressed:
        if win["btn_hover"]:
            do_fetch = True
        elif 28 <= ly <= 44:
            if lx < 40: 
                win["c_idx"] = (win["c_idx"] - 1) % len(win["coins"])
                win["result"] = ""
            elif lx > 40: 
                win["c_idx"] = (win["c_idx"] + 1) % len(win["coins"])
                win["result"] = ""

    # --- DATEN ABRUFEN ---
    if do_fetch:
        win["loading"] = True
        win["result"] = "FRAGE KURS AB..."
        
        symbol = win["symbols"][win["c_idx"]]
        t = threading.Thread(target=fetch_crypto, args=(win, symbol))
        t.daemon = True
        t.start()

def draw(win, wx, wy, ww, wh, is_active):
    import py16
    
    content_y = wy + 14
    content_h = wh - 14
    
    # Hintergrund (Schwarz fuer den Krypto-Hacker-Look)
    py16.rectfill(wx + 2, content_y, ww - 4, content_h - 2, 0)
    
    text_y = content_y + 8
    py16.text("COIN:", wx + 6, text_y, 7)
    
    current_coin = "< " + win["coins"][win["c_idx"]] + " >"
    
    # Bitcoin = Orange(9), Ethereum = Lila(2), Solana = Gruen(11), Doge = Gelb(10)
    color_map = [9, 2, 11, 10] 
    coin_color = color_map[win["c_idx"] % len(color_map)]
    
    py16.text(current_coin, wx + 6, text_y + 14, coin_color)
    
    # --- BUTTON ZEICHNEN ---
    bx = wx + win["btn_x"]
    by = wy + win["btn_y"]
    bw = win["btn_w"]
    bh = win["btn_h"]
    
    if win.get("loading"):
        btn_color = 5
    else:
        btn_color = 13 if win.get("btn_hover") else 1
        
    py16.rectfill(bx, by, bw, bh, btn_color)
    py16.rect(bx, by, bw, bh, 7 if is_active else 5)
    py16.text("LADEN", bx + 9, by + 4, 7)
    
    # --- ERGEBNIS ZEICHNEN ---
    res_color = 5 if win["loading"] else 11 # Grau beim Laden, Gruen fuers Geld!
    py16.text(win["result"], wx + 6, by + 18, res_color)
