"""
TWO-PLAYER PONG for py-16
==========================

Couch multiplayer with two gamepads. First to 7 points wins.
With no gamepads, both players share the keyboard:
  P1: arrow up/down
  P2: W/S keys (arrow left/right also works)
With one gamepad: P1 uses the gamepad, P2 uses W/S.
With two gamepads: each player uses their own.

# @manual
# @description
# Classic two-player Pong. First to 7 points wins.
# Connect two gamepads for couch multiplayer, or share the
# keyboard.
#
# @controls
# P1 keyboard      : Up / Down
# P2 keyboard      : W / S
# Gamepads         : up / down on the D-pad
# Z                : start round / restart after game over
# F12              : Back to BIOS
#
# @credits
# py-16 demo cart
# @end
"""

import py16

# Game state
ball_x  = 128.0
ball_y  = 112.0
ball_vx = 2.0
ball_vy = 1.0

p1_y = 96.0
p2_y = 96.0

p1_score = 0
p2_score = 0

WINNING_SCORE = 7
PADDLE_H      = 32
PADDLE_W      = 4
PADDLE_SPEED  = 2.5
BALL_SIZE     = 4

game_over = False
waiting_for_start = True

def init():
    try:
        py16.set_code_file(__file__)
    except (NameError, Exception):
        pass

def reset_ball():
    global ball_x, ball_y, ball_vx, ball_vy
    ball_x = 128
    ball_y = 112
    ball_vx = 2.0 if ball_vx < 0 else -2.0   # serve toward last loser
    ball_vy = py16.rnd(2) - 1

def update():
    global ball_x, ball_y, ball_vx, ball_vy
    global p1_y, p2_y, p1_score, p2_score
    global game_over, waiting_for_start

    # === Player 1 paddle (left side) ===
    # Use player=1 so this responds only to P1's gamepad,
    # or keyboard if no gamepads are connected.
    if py16.btn('up', player=1) or py16.btn('w', player=1):
        p1_y -= PADDLE_SPEED
    if py16.btn('down', player=1) or py16.btn('s', player=1):
        p1_y += PADDLE_SPEED

    # Keyboard for P1 also accepts arrows (already handled by player=1
    # via _keyboard_eligible when no gamepads), and W/S as backup.
    if py16.num_controllers() == 0:
        # Both players share keyboard. P1 = arrows, P2 = W/S
        # (already done above; here only enforce W/S for P2)
        pass

    # === Player 2 paddle (right side) ===
    # Player 2 uses their gamepad if connected; else keyboard W/S
    if py16.player_connected(2):
        if py16.btn('up', player=2):
            p2_y -= PADDLE_SPEED
        if py16.btn('down', player=2):
            p2_y += PADDLE_SPEED
    else:
        # P2 keyboard fallback: W/S
        if py16.btn('s', player=0) and py16.player_connected(1) is False:
            # if no gamepads: 's' is P1's "down" already, conflict
            # Use a different binding: arrow up/down for P1, W/S for P2.
            # This is the "shared keyboard" mode.
            pass
        # Better keyboard split for shared-keyboard mode:
        if py16.btn('w'):
            p2_y -= PADDLE_SPEED
        if py16.btn('s'):
            p2_y += PADDLE_SPEED

    # Clamp paddles to screen
    p1_y = max(12, min(py16.HEIGHT - 12 - PADDLE_H, p1_y))
    p2_y = max(12, min(py16.HEIGHT - 12 - PADDLE_H, p2_y))

    # === Game flow ===
    if waiting_for_start:
        if py16.btnp('z') or py16.btnp('z', player=2):
            waiting_for_start = False
            reset_ball()
        return

    if game_over:
        if py16.btnp('z') or py16.btnp('z', player=2):
            p1_score = 0
            p2_score = 0
            game_over = False
            reset_ball()
        return

    # === Ball physics ===
    ball_x += ball_vx
    ball_y += ball_vy

    # Top / bottom walls
    if ball_y < 12:
        ball_y = 12
        ball_vy = -ball_vy
        py16.tone(400, 50, py16.WAVE_SQUARE)
    if ball_y > py16.HEIGHT - 12 - BALL_SIZE:
        ball_y = py16.HEIGHT - 12 - BALL_SIZE
        ball_vy = -ball_vy
        py16.tone(400, 50, py16.WAVE_SQUARE)

    # P1 paddle collision (left)
    if (ball_x <= 12 + PADDLE_W
            and p1_y <= ball_y + BALL_SIZE
            and ball_y <= p1_y + PADDLE_H
            and ball_vx < 0):
        ball_vx = -ball_vx * 1.05  # slightly speed up
        # Y-velocity depends on hit position
        rel = (ball_y + BALL_SIZE/2 - (p1_y + PADDLE_H/2)) / (PADDLE_H/2)
        ball_vy = rel * 2.5
        py16.tone(800, 60, py16.WAVE_SQUARE)

    # P2 paddle collision (right)
    if (ball_x >= py16.WIDTH - 12 - PADDLE_W - BALL_SIZE
            and p2_y <= ball_y + BALL_SIZE
            and ball_y <= p2_y + PADDLE_H
            and ball_vx > 0):
        ball_vx = -ball_vx * 1.05
        rel = (ball_y + BALL_SIZE/2 - (p2_y + PADDLE_H/2)) / (PADDLE_H/2)
        ball_vy = rel * 2.5
        py16.tone(800, 60, py16.WAVE_SQUARE)

    # Score
    if ball_x < -BALL_SIZE:
        p2_score += 1
        py16.tone(150, 200, py16.WAVE_NOISE,
                  attack_ms=20, decay_ms=80, release_ms=100)
        if p2_score >= WINNING_SCORE:
            game_over = True
        else:
            reset_ball()
    elif ball_x > py16.WIDTH:
        p1_score += 1
        py16.tone(150, 200, py16.WAVE_NOISE,
                  attack_ms=20, decay_ms=80, release_ms=100)
        if p1_score >= WINNING_SCORE:
            game_over = True
        else:
            reset_ball()

def draw():
    py16.cls(0)

    # Top bar with player info
    py16.rectfill(0, 0, py16.WIDTH, 11, 1)

    # Show connected players
    p1_marker = "P1" + ("*" if py16.player_connected(1) else " ")
    p2_marker = "P2" + ("*" if py16.player_connected(2) else " ")
    py16.text(p1_marker, 4, 3, 11)
    py16.text(p2_marker, py16.WIDTH - 18, 3, 8)

    # Score in the middle
    py16.text(f"{p1_score} - {p2_score}",
              py16.WIDTH // 2 - 10, 3, 7)

    # Center divider line (dashed)
    for y in range(20, py16.HEIGHT, 8):
        py16.rectfill(py16.WIDTH // 2 - 1, y, 2, 4, 5)

    # Paddles
    py16.rectfill(12, int(p1_y), PADDLE_W, PADDLE_H, 11)
    py16.rectfill(py16.WIDTH - 12 - PADDLE_W, int(p2_y),
                  PADDLE_W, PADDLE_H, 8)

    # Ball
    if not waiting_for_start and not game_over:
        py16.rectfill(int(ball_x), int(ball_y), BALL_SIZE, BALL_SIZE, 7)

    # Overlays
    if waiting_for_start:
        _msg_box(["TWO-PLAYER PONG",
                  f"FIRST TO {WINNING_SCORE} WINS",
                  "",
                  "PRESS Z TO START"])
    elif game_over:
        winner = "P1" if p1_score >= WINNING_SCORE else "P2"
        _msg_box([f"{winner} WINS!",
                  f"FINAL: {p1_score} - {p2_score}",
                  "",
                  "PRESS Z FOR REMATCH"])

    # Footer hints
    n = py16.num_controllers()
    if n == 0:
        hint = "P1 ARROWS  P2 W/S"
    elif n == 1:
        hint = "P1 GAMEPAD  P2 W/S"
    else:
        hint = f"{n} GAMEPADS CONNECTED"
    py16.text(hint, 4, py16.HEIGHT - 9, 6)

def _msg_box(lines):
    """Draw a centered message box with the given lines of text."""
    w = max(len(line) for line in lines) * 4 + 16
    h = len(lines) * 10 + 12
    x = (py16.WIDTH - w) // 2
    y = (py16.HEIGHT - h) // 2
    py16.rectfill(x, y, w, h, 0)
    py16.rect(x, y, w, h, 7)
    for i, line in enumerate(lines):
        py16.text(line,
                  x + (w - len(line) * 4) // 2,
                  y + 6 + i * 10,
                  7)

if __name__ == "__main__":
    py16.run(update, draw, init)
