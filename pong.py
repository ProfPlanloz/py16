"""
PONG for py-16
================

# @manual
# @description
# Classic Pong vs the AI.
# First to 5 points wins.
#
# @controls
# Arrow up / down     : Move paddle
# F12                 : Back to BIOS
#
# @credits
# py-16 demo cart
# @end
"""

import py16

# State
ball_x, ball_y = 128, 112
ball_dx, ball_dy = 2.0, 1.5
player_y = 96
ai_y = 96
score_player = 0
score_ai = 0
flash = 0   # Frames lang weiss aufblitzen bei Scores

PADDLE_H = 32
PADDLE_W = 4

def init():
    try:
        py16.set_code_file(__file__)
    except (NameError, Exception):
        pass

def update():
    global ball_x, ball_y, ball_dx, ball_dy
    global player_y, ai_y, score_player, score_ai, flash

    # Player input
    if py16.btn('up'):    player_y = max(0, player_y - 3)
    if py16.btn('down'):  player_y = min(py16.HEIGHT - PADDLE_H, player_y + 3)

    # AI: simple chase with small delay
    target = ball_y - PADDLE_H // 2
    if ai_y < target - 2:   ai_y += 2
    elif ai_y > target + 2: ai_y -= 2
    ai_y = max(0, min(py16.HEIGHT - PADDLE_H, ai_y))

    # Move ball
    ball_x += ball_dx
    ball_y += ball_dy

    # Top/bottom wall
    if ball_y < 0 or ball_y > py16.HEIGHT - 1:
        ball_dy = -ball_dy
        py16.tone(220, 30, py16.WAVE_SQUARE)

    # Player paddle
    if (ball_x < 6 and ball_dx < 0
            and player_y < ball_y < player_y + PADDLE_H):
        ball_dx = -ball_dx * 1.05    # slight speedup
        # Deflection by hit point
        offset = (ball_y - (player_y + PADDLE_H/2)) / (PADDLE_H/2)
        ball_dy += offset * 0.5
        py16.tone(440, 30, py16.WAVE_SQUARE)

    # AI paddle
    if (ball_x > py16.WIDTH - 6 and ball_dx > 0
            and ai_y < ball_y < ai_y + PADDLE_H):
        ball_dx = -ball_dx * 1.05
        offset = (ball_y - (ai_y + PADDLE_H/2)) / (PADDLE_H/2)
        ball_dy += offset * 0.5
        py16.tone(440, 30, py16.WAVE_SQUARE)

    # Point!
    if ball_x < 0:
        score_ai += 1
        flash = 30
        _reset_ball(direction=1)
        py16.tone(110, 200, py16.WAVE_SAW)
    elif ball_x > py16.WIDTH:
        score_player += 1
        flash = 30
        _reset_ball(direction=-1)
        py16.tone(660, 200, py16.WAVE_TRIANGLE)

    if flash > 0:
        flash -= 1

def _reset_ball(direction=1):
    global ball_x, ball_y, ball_dx, ball_dy
    ball_x, ball_y = py16.WIDTH // 2, py16.HEIGHT // 2
    ball_dx = 2.0 * direction
    ball_dy = py16.rnd(2.0) - 1.0

def draw():
    bg = 7 if flash > 0 and flash % 6 < 3 else 1
    py16.cls(bg)

    # Mid-line of dashes
    for y in range(0, py16.HEIGHT, 8):
        py16.rectfill(py16.WIDTH // 2 - 1, y, 2, 4, 6)

    # Paddles
    py16.rectfill(2, int(player_y), PADDLE_W, PADDLE_H, 11)
    py16.rectfill(py16.WIDTH - 6, int(ai_y), PADDLE_W, PADDLE_H, 8)

    # Ball
    py16.rectfill(int(ball_x), int(ball_y), 4, 4, 7)

    # Score
    py16.text(f"{score_player}", 60, 8, 11)
    py16.text(f"{score_ai}", py16.WIDTH - 70, 8, 8)

    # Winner display
    if score_player >= 5 or score_ai >= 5:
        msg = "YOU WIN!" if score_player > score_ai else "AI WINS!"
        py16.rectfill(60, 100, 136, 24, 0)
        py16.rect(60, 100, 136, 24, 7)
        py16.text(msg, 80, 110, 7)

if __name__ == "__main__":
    py16.run(update, draw, init)
