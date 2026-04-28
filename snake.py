"""
SNAKE fuer py-16
=================

# @manual
# @description
# Klassisches Snake. Iss Aepfel, werde laenger,
# stosse nicht gegen Wand oder dich selbst.
#
# @controls
# Pfeile : Richtung aendern
# Z      : Neustart nach Game Over
#
# @credits
# py-16 demo cart
# @end
"""

import py16

CELL = 8
COLS = py16.WIDTH // CELL    # 32
ROWS = (py16.HEIGHT - 16) // CELL  # 26 (16px fuer HUD reserviert)

snake = []
direction = (1, 0)
next_direction = (1, 0)
apple = (10, 10)
score = 0
move_timer = 0
move_interval = 6   # alle 6 Frames bewegen
game_over = False

def init():
    try:
        py16.set_code_file(__file__)
    except (NameError, Exception):
        pass
    _new_game()

def _new_game():
    global snake, direction, next_direction, score, move_timer, game_over, move_interval
    snake = [(5, 13), (4, 13), (3, 13)]
    direction = (1, 0)
    next_direction = (1, 0)
    score = 0
    move_timer = 0
    move_interval = 6
    game_over = False
    _spawn_apple()

def _spawn_apple():
    global apple
    while True:
        x = int(py16.rnd(COLS))
        y = int(py16.rnd(ROWS))
        if (x, y) not in snake:
            apple = (x, y)
            return

def update():
    global direction, next_direction, snake, apple, score
    global move_timer, move_interval, game_over

    if game_over:
        if py16.btnp('z'):
            _new_game()
        return

    # Eingabe (verhindere 180-Grad-Wende)
    if py16.btnp('up')    and direction != (0, 1):  next_direction = (0, -1)
    if py16.btnp('down')  and direction != (0, -1): next_direction = (0, 1)
    if py16.btnp('left')  and direction != (1, 0):  next_direction = (-1, 0)
    if py16.btnp('right') and direction != (-1, 0): next_direction = (1, 0)

    # Bewegungs-Tick
    move_timer += 1
    if move_timer < move_interval:
        return
    move_timer = 0
    direction = next_direction

    head_x, head_y = snake[0]
    new_head = (head_x + direction[0], head_y + direction[1])

    # Wand-Kollision
    if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS):
        game_over = True
        py16.tone(80, 400, py16.WAVE_NOISE)
        return

    # Selbst-Kollision
    if new_head in snake:
        game_over = True
        py16.tone(80, 400, py16.WAVE_NOISE)
        return

    snake.insert(0, new_head)

    # Apfel?
    if new_head == apple:
        score += 1
        py16.tone(660, 50, py16.WAVE_TRIANGLE)
        _spawn_apple()
        # Schneller werden
        if score % 5 == 0 and move_interval > 2:
            move_interval -= 1
    else:
        snake.pop()   # ohne Apfel: Schwanz weg

def draw():
    py16.cls(1)

    # HUD
    py16.rectfill(0, 0, py16.WIDTH, 16, 0)
    py16.text(f"SCORE: {score:03d}", 4, 5, 11)
    py16.text(f"LEN: {len(snake):03d}", py16.WIDTH - 60, 5, 6)

    # Spielfeld-Rahmen
    py16.rect(0, 16, py16.WIDTH, py16.HEIGHT - 16, 5)

    # Apfel
    ax, ay = apple
    py16.circfill(ax * CELL + CELL // 2, 16 + ay * CELL + CELL // 2, 3, 8)

    # Schlange
    for i, (sx, sy) in enumerate(snake):
        col = 11 if i == 0 else 3
        py16.rectfill(sx * CELL + 1, 16 + sy * CELL + 1,
                      CELL - 2, CELL - 2, col)

    # Game Over
    if game_over:
        py16.rectfill(40, 80, 176, 50, 0)
        py16.rect(40, 80, 176, 50, 8)
        py16.text("GAME OVER", 92, 92, 8)
        py16.text(f"FINAL: {score:03d}", 92, 104, 7)
        py16.text("Z - NEUSTART", 88, 116, 6)

if __name__ == "__main__":
    py16.run(update, draw, init)
