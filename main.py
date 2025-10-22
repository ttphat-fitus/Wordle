import os
import sys
import math
import random
import json
import pygame
from datetime import datetime, date

WIDTH, HEIGHT = 550, 800
FPS = 60
ROWS, COLS = 6, 5
MARGIN_X = 32
TOP_OFFSET = 140
TILE_GAP = 10
KEYBOARD_GAP = 6
ANIM_SPEED = 0.22 
POP_SCALE = 1.08

pygame.init()
pygame.display.set_caption("Wordle")
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
CLOCK = pygame.time.Clock()


try:
    TITLE_FONT = pygame.font.SysFont("Avenir Next", 44, bold=True)
    UI_FONT = pygame.font.SysFont("Avenir Next", 18)
    TILE_FONT = pygame.font.SysFont("Avenir Next", 40, bold=True)
    KEY_FONT = pygame.font.SysFont("Avenir Next", 18, bold=True)
except Exception:
    TITLE_FONT = pygame.font.SysFont("arial", 44, bold=True)
    UI_FONT = pygame.font.SysFont("arial", 18)
    TILE_FONT = pygame.font.SysFont("arial", 40, bold=True)
    KEY_FONT = pygame.font.SysFont("arial", 18, bold=True)

BG_TOP = (250, 250, 252)      # very light gray
BG_BOTTOM = (244, 246, 248)   # slightly darker
GRID_BG = (255, 255, 255)
TILE_EMPTY = (248, 249, 250)
TILE_BORDER = (200, 205, 210)
TILE_TEXT = (20, 24, 30)
ACCENT = (0, 120, 215)

C_ABSENT = (75, 79, 92)     # gray
C_PRESENT = (201, 180, 88)  # yellow-gold
C_CORRECT = (88, 140, 103)  # green

CONFETTI_COLS = [
    (236, 99, 95), (255, 211, 102), (147, 221, 119),
    (123, 178, 255), (195, 155, 211)
]

KB_ROWS = [
    list("QWERTYUIOP"),
    list("ASDFGHJKL"),
    ["ENTER"] + list("ZXCVBNM") + ["⌫"],
]


def lerp(a, b, t):
    return a + (b - a) * t


def draw_vertical_gradient(surface, top_color, bottom_color):
    h = surface.get_height()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(lerp(top_color[0], bottom_color[0], t))
        g = int(lerp(top_color[1], bottom_color[1], t))
        b = int(lerp(top_color[2], bottom_color[2], t))
        pygame.draw.line(surface, (r, g, b), (0, y), (surface.get_width(), y))


def load_vocab():
    base = os.path.dirname(__file__)
    path = os.path.join(base, 'data', 'vocabulary.json')
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required vocabulary file not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    words = [w.lower() for w in data.keys() if isinstance(w, str) and len(w) == 5 and w.isalpha()]
    if not words:
        raise RuntimeError(f"No valid 5-letter words found in {path}")
    return sorted(set(words))


VOCAB = load_vocab()


def pick_daily_word(vocab):
    return random.choice(vocab)

TARGET = pick_daily_word(VOCAB)

class Judge:
    @staticmethod
    def evaluate(guess: str, answer: str):
        guess = guess.lower()
        answer = answer.lower()
        res = [0] * len(guess)
        remaining = {}
        for i, (g, a) in enumerate(zip(guess, answer)):
            if g == a:
                res[i] = 2
            else:
                remaining[a] = remaining.get(a, 0) + 1
        for i, g in enumerate(guess):
            if res[i] == 0 and remaining.get(g, 0) > 0:
                res[i] = 1
                remaining[g] -= 1
        return res


class Tile:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.char = ""
        self.state = None  # None/0/1/2
        self.flip_t = 0.0
        self.pop_t = 0.0

    def start_flip(self):
        self.flip_t = 1.0 

    def start_pop(self):
        self.pop_t = 1.0

    def update(self, dt):
        if self.flip_t > 0:
            self.flip_t = max(0.0, self.flip_t - dt / ANIM_SPEED)
        if self.pop_t > 0:
            self.pop_t = max(0.0, self.pop_t - dt / (ANIM_SPEED * 1.2))

    def draw(self, surface):
        color = TILE_EMPTY if self.state is None else [C_ABSENT, C_PRESENT, C_CORRECT][self.state]
        flip_phase = (1 - self.flip_t)
        if self.state is not None:
            face_color = color
        else:
            face_color = TILE_EMPTY

        pop_scale = lerp(1.0, POP_SCALE, self.pop_t)

        w, h = self.rect.width, self.rect.height
        temp = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(temp, face_color, (0, 0, w, h), border_radius=10)
        pygame.draw.rect(temp, TILE_BORDER, (0, 0, w, h), width=2, border_radius=10)

        scale_y = abs(math.cos(flip_phase * math.pi))  # 1 -> 0 -> 1
        scaled = pygame.transform.smoothscale(temp, (int(w * pop_scale), max(1, int(h * scale_y * pop_scale))))
        cx, cy = self.rect.center
        rect = scaled.get_rect(center=(cx, cy))
        surface.blit(scaled, rect)

        if self.char:
            ch = self.char.upper()
            text = TILE_FONT.render(ch, True, TILE_TEXT)
            trect = text.get_rect(center=(cx, cy))
            if scale_y < 0.25:
                alpha = int(255 * max(0.0, (scale_y - 0.1) / 0.15))
            else:
                alpha = 255
            text.set_alpha(alpha)
            surface.blit(text, trect)


class Keyboard:
    def __init__(self):
        self.key_states = {} 

    def update_states(self, guess, eval_states):
        for ch, s in zip(guess.upper(), eval_states):
            if ch not in self.key_states:
                self.key_states[ch] = s
            else:
                self.key_states[ch] = max(self.key_states[ch], s)

    def key_at(self, pos):
        layout = self.layout_rects()
        for label, rect in layout:
            if rect.collidepoint(pos):
                return label
        return None

    def layout_rects(self):
        rows = []
        kb_top = TOP_OFFSET + ROWS * (tile_size() + TILE_GAP) + 60
        kb_width = WIDTH - MARGIN_X * 2
        key_h = 48
        x = MARGIN_X
        y = kb_top
        layout = []
        for r, row in enumerate(KB_ROWS):
            total_w = 0
            rects = []
            for label in row:
                w = 52 if label in ("ENTER", "⌫") else 40
                total_w += w + KEYBOARD_GAP
            total_w -= KEYBOARD_GAP
            x = (WIDTH - total_w) // 2
            for label in row:
                w = 52 if label in ("ENTER", "⌫") else 40
                rect = pygame.Rect(x, y, w, key_h)
                rects.append((label, rect))
                x += w + KEYBOARD_GAP
            y += key_h + KEYBOARD_GAP
            rows.extend(rects)
        return rows

    def draw(self, surface):
        for label, rect in self.layout_rects():
            if label == "ENTER" or label == "⌫":
                r = 8
            else:
                r = 8
            state = None
            if label not in ("ENTER", "⌫"):
                state = self.key_states.get(label, None)
            base = TILE_EMPTY if state is None else [C_ABSENT, C_PRESENT, C_CORRECT][state]
            pygame.draw.rect(surface, base, rect, border_radius=r)
            pygame.draw.rect(surface, TILE_BORDER, rect, width=2, border_radius=r)
            txt = KEY_FONT.render(label, True, TILE_TEXT)
            surface.blit(txt, txt.get_rect(center=rect.center))


def tile_size():
    available = WIDTH - MARGIN_X * 2 - TILE_GAP * (COLS - 1)
    return available // COLS



class Game:
    def __init__(self, answer, vocab):
        self.answer = answer
        self.vocab = set(vocab)
        self.grid = []
        size = tile_size()
        for r in range(ROWS):
            row = []
            for c in range(COLS):
                x = MARGIN_X + c * (size + TILE_GAP)
                y = TOP_OFFSET + r * (size + TILE_GAP)
                row.append(Tile((x, y, size, size)))
            self.grid.append(row)
        self.particles = []
        self.row = 0
        self.col = 0
        self.keyboard = Keyboard()
        self.message = ""
        self.msg_timer = 0.0
        self.win = False
        self.lose = False
        self.shake_t = 0.0

    def add_char(self, ch):
        if self.win or self.lose:
            return
        if self.col < COLS and ch.isalpha():
            self.grid[self.row][self.col].char = ch.upper()
            self.grid[self.row][self.col].start_pop()
            self.col += 1

    def backspace(self):
        if self.win or self.lose:
            return
        if self.col > 0:
            self.col -= 1
            self.grid[self.row][self.col].char = ""

    def submit(self):
        if self.win or self.lose:
            return
        if self.col < COLS:
            self.toast("Not enough letters")
            self.shake()
            return
        guess = "".join(tile.char for tile in self.grid[self.row]).lower()
        if guess not in self.vocab:
            self.toast("Not in word list")
            self.shake()
            return
        states = Judge.evaluate(guess, self.answer)
        for i, tile in enumerate(self.grid[self.row]):
            tile.state = states[i]
            tile.start_flip()
        self.keyboard.update_states(guess, states)
        if all(s == 2 for s in states):
            self.win = True
            self.toast(random.choice(["Genius!", "Magnificent!", "Splendid!", "Great!"]))
            self.spawn_confetti()
        else:
            self.row += 1
            self.col = 0
            if self.row >= ROWS:
                self.lose = True
                self.toast(self.answer.upper())

    def toast(self, msg, duration=1.4):
        self.message = msg
        self.msg_timer = duration

    def shake(self):
        self.shake_t = 1.0

    def spawn_confetti(self):
        cx = WIDTH // 2
        for _ in range(150):
            angle = random.uniform(-math.pi, 0)
            speed = random.uniform(120, 300)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            size = random.randint(3, 6)
            color = random.choice(CONFETTI_COLS)
            life = random.uniform(1.2, 2.0)
            self.particles.append([cx, TOP_OFFSET - 30, vx, vy, size, color, life])

    def update_confetti(self, dt):
        gravity = 400
        new = []
        for p in self.particles:
            x, y, vx, vy, s, color, life = p
            vy += gravity * dt
            x += vx * dt
            y += vy * dt
            life -= dt
            if life > 0 and y < HEIGHT + 20:
                new.append([x, y, vx, vy, s, color, life])
        self.particles = new

    def update(self, dt):
        for row in self.grid:
            for tile in row:
                tile.update(dt)
        if self.msg_timer > 0:
            self.msg_timer -= dt
            if self.msg_timer <= 0:
                self.message = ""
        if self.shake_t > 0:
            self.shake_t = max(0.0, self.shake_t - dt / 0.4)
        self.update_confetti(dt)

    def draw(self, surface):
        draw_vertical_gradient(surface, BG_TOP, BG_BOTTOM)

        # Title
        title = TITLE_FONT.render("WORDLE", True, TILE_TEXT)
        surface.blit(title, title.get_rect(center=(WIDTH // 2, 56)))

        grid_rect = pygame.Rect(MARGIN_X - 8, TOP_OFFSET - 8,
                                (tile_size() + TILE_GAP) * COLS - TILE_GAP + 16,
                                (tile_size() + TILE_GAP) * ROWS - TILE_GAP + 16)
        s = pygame.Surface(grid_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 80), s.get_rect(), border_radius=16)
        surface.blit(s, grid_rect)

        dx = 0
        if self.shake_t > 0:
            dx = math.sin((1 - self.shake_t) * 30) * 8 * self.shake_t
        for r in range(ROWS):
            for c in range(COLS):
                tile = self.grid[r][c]
                saved = tile.rect.copy()
                tile.rect.x = saved.x + int(dx)
                tile.draw(surface)
                tile.rect = saved

        if self.message:
            toast_surf = UI_FONT.render(self.message, True, TILE_TEXT)
            pad = 12
            rect = toast_surf.get_rect(center=(WIDTH // 2, TOP_OFFSET - 50))
            bg = pygame.Surface((rect.width + pad * 2, rect.height + pad * 2), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, 140), bg.get_rect(), border_radius=10)
            SCREEN.blit(bg, bg.get_rect(center=rect.center))
            SCREEN.blit(toast_surf, rect)

        self.keyboard.draw(surface)

        for x, y, vx, vy, s, color, life in self.particles:
            pygame.draw.rect(surface, color, pygame.Rect(int(x), int(y), s, s))



def handle_key(game: Game, event):
    if event.key == pygame.K_RETURN:
        game.submit()
    elif event.key == pygame.K_BACKSPACE:
        game.backspace()
    else:
        ch = event.unicode
        if ch and ch.isalpha() and len(ch) == 1:
            game.add_char(ch)


def main():
    try:
        print(f"Word: {TARGET}")
    except Exception:
        pass
    game = Game(TARGET, VOCAB)

    running = True
    while running:
        dt = CLOCK.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                handle_key(game, event)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                label = game.keyboard.key_at(event.pos)
                if label:
                    if label == "ENTER":
                        game.submit()
                    elif label == "⌫":
                        game.backspace()
                    else:
                        game.add_char(label)

        game.update(dt)
        game.draw(SCREEN)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
