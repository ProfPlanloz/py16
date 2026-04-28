"""
Entry-Point fuer 'python -m py16' und das 'py16' Kommando.

Verhalten:
  py16              -> startet ohne Cart, geht ins BIOS oder Boot-Cart
  py16 cart.p16     -> startet den angegebenen Cart direkt
  py16 cart.pdf     -> dito
"""

import sys
import os

def main():
    import py16
    args = sys.argv[1:]

    if not args:
        # Kein Cart - BIOS / Auto-Boot
        py16.run()
        return

    cart_path = args[0]
    if not os.path.exists(cart_path):
        print(f"Cart nicht gefunden: {cart_path}")
        sys.exit(1)

    # Cart laden und starten
    py16.load_cart(cart_path)
    # Code aus dem Cart kompilieren und ausfuehren ueber run_cart
    py16.run_cart(cart_path)
    py16.run()  # Hauptschleife (laedt den Cart beim ersten Frame)

if __name__ == "__main__":
    main()
