import math
import random
import pygame
import backend

BASE_WIDTH, BASE_HEIGHT = 550, 800
FPS = 60
ROWS, COLS = 6, 5
MARGIN_X = 32
TOP_OFFSET = 140
TILE_GAP = 10
KEYBOARD_GAP = 6
ANIM_SPEED = 0.22
POP_SCALE = 1.08

WIDTH = BASE_WIDTH
HEIGHT = BASE_HEIGHT
SCALE = 1.0

BG_TOP = (250, 250, 252)
BG_BOTTOM = (244, 246, 248)
GRID_BG = (255, 255, 255)
TILE_EMPTY = (248, 249, 250)
TILE_BORDER = (200, 205, 210)
TILE_TEXT = (20, 24, 30)
ACCENT = (0, 120, 215)

C_ABSENT = (75, 79, 92)
C_PRESENT = (201, 180, 88)
C_CORRECT = (88, 140, 103)

CONFETTI_COLS = [
    (236, 99, 95), (255, 211, 102), (147, 221, 119),
    (123, 178, 255), (195, 155, 211)
]

KB_ROWS = [
    list("QWERTYUIOP"),
    list("ASDFGHJKL"),
    ["ENTER"] + list("ZXCVBNM") + ["DEL"],
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


def handle_key(game, event):
    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        game.submit()
    elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
        game.backspace()
    else:
        ch = event.unicode
        if ch and ch.isalpha() and len(ch) == 1:
            game.add_char(ch)


def tile_size():
    available_w = WIDTH - MARGIN_X * 2 - TILE_GAP * (COLS - 1)
    size = max(16, available_w // COLS)

    for _ in range(6):
        key_h = max(34, int(size * 0.7))
        keyboard_rows = len(KB_ROWS)
        keyboard_reserved = keyboard_rows * key_h + (keyboard_rows - 1) * KEYBOARD_GAP + int(20 * SCALE)
        available_h = HEIGHT - TOP_OFFSET - keyboard_reserved - int(24 * SCALE)
        size_h = max(16, (available_h - (ROWS - 1) * TILE_GAP) // ROWS)
        new_size = min(size, size_h)
        new_size = min(new_size, max(16, available_w // COLS))
        if new_size == size:
            break
        size = new_size

    return max(16, size)


def setup_fonts(scale: float = 1.0):
    global TITLE_FONT, UI_FONT, TILE_FONT, KEY_FONT, SCALE, WIDTH, HEIGHT, MARGIN_X, TOP_OFFSET, TILE_GAP, KEYBOARD_GAP
    SCALE = float(scale)
    WIDTH = int(BASE_WIDTH * SCALE)
    HEIGHT = int(BASE_HEIGHT * SCALE)
    MARGIN_X = int(32 * SCALE)
    TOP_OFFSET = int(140 * SCALE)
    TILE_GAP = int(max(4, 10 * SCALE))
    KEYBOARD_GAP = int(max(4, 6 * SCALE))

    try:
        TITLE_FONT = pygame.font.SysFont("arial", max(12, int(44 * SCALE)), bold=True)
        UI_FONT = pygame.font.SysFont("arial", max(10, int(18 * SCALE)))
        TILE_FONT = pygame.font.SysFont("arial", max(12, int(40 * SCALE)), bold=True)
        KEY_FONT = pygame.font.SysFont("arial", max(10, int(18 * SCALE)), bold=True)
    except Exception:
        TITLE_FONT = pygame.font.SysFont(None, max(12, int(44 * SCALE)), bold=True)
        UI_FONT = pygame.font.SysFont(None, max(10, int(18 * SCALE)))
        TILE_FONT = pygame.font.SysFont(None, max(12, int(40 * SCALE)), bold=True)
        KEY_FONT = pygame.font.SysFont(None, max(10, int(18 * SCALE)), bold=True)


def compute_total_height_for_scale(scale: float) -> int:
    s = float(scale)
    width = int(BASE_WIDTH * s)
    margin_x = int(32 * s)
    top_offset = int(140 * s)
    tile_gap = int(max(4, 10 * s))
    keyboard_gap = int(max(4, 6 * s))

    available_w = width - margin_x * 2 - tile_gap * (COLS - 1)
    tile = max(16, available_w // COLS)

    key_h = max(34, int(tile * 0.7))
    keyboard_rows = len(KB_ROWS)
    keyboard_reserved = keyboard_rows * key_h + (keyboard_rows - 1) * keyboard_gap + int(20 * s)

    grid_height = ROWS * tile + (ROWS - 1) * tile_gap

    bottom_margin = int(24 * s)

    total = top_offset + grid_height + keyboard_reserved + bottom_margin
    return total


def compute_best_scale(max_w: int, max_h: int) -> float:
    max_scale_w = max_w / BASE_WIDTH
    initial = min(1.0, max_scale_w)
    scale = initial
    s = scale
    while s >= 0.5:
        total_h = compute_total_height_for_scale(s)
        total_w = int(BASE_WIDTH * s)
        if total_w <= max_w and total_h <= max_h:
            return s
        s -= 0.01
    return 0.5


class Tile:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.char = ""
        self.state = None
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
        corner = max(8, int(8 * SCALE))
        pygame.draw.rect(temp, face_color, (0, 0, w, h), border_radius=corner)
        pygame.draw.rect(temp, TILE_BORDER, (0, 0, w, h), width=max(2, int(2 * SCALE)), border_radius=corner)

        scale_y = abs(math.cos(flip_phase * math.pi))
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
        grid_h = ROWS * tile_size() + (ROWS - 1) * TILE_GAP
        desired_kb_top = TOP_OFFSET + grid_h + int(20 * SCALE)
        kb_width = WIDTH - MARGIN_X * 2
        key_h = max(28, int(tile_size() * 0.72))
        small_key_w = max(36, int(tile_size() * 0.95))
        large_key_w = max(56, int(tile_size() * 1.25))
        bottom_margin = int(20 * SCALE)
        keyboard_rows = len(KB_ROWS)
        keyboard_reserved = keyboard_rows * key_h + (keyboard_rows - 1) * KEYBOARD_GAP + bottom_margin

        if desired_kb_top + keyboard_reserved + bottom_margin > HEIGHT:
            kb_top = max(int(TOP_OFFSET + grid_h + int(8 * SCALE)), HEIGHT - keyboard_reserved - bottom_margin)
        else:
            kb_top = desired_kb_top
        x = MARGIN_X
        y = kb_top
        layout = []
        for r, row in enumerate(KB_ROWS):
            total_w = 0
            rects = []
            for label in row:
                w = large_key_w if label in ("ENTER", "DEL") else small_key_w
                total_w += w + KEYBOARD_GAP
            total_w -= KEYBOARD_GAP
            avail_row_w = WIDTH - MARGIN_X * 2
            scale_row = 1.0
            if total_w > avail_row_w:
                scale_row = (avail_row_w - (len(row)-1)*KEYBOARD_GAP) / (total_w - (len(row)-1)*KEYBOARD_GAP)
                scale_row = max(0.6, scale_row)

            x = (WIDTH - int(total_w * scale_row)) // 2
            for label in row:
                base_w = large_key_w if label in ("ENTER", "DEL") else small_key_w
                w = max(28, int(base_w * scale_row))
                rect = pygame.Rect(x, y, w, key_h)
                rects.append((label, rect))
                x += w + KEYBOARD_GAP
            y += key_h + KEYBOARD_GAP
            rows.extend(rects)
        return rows

    def draw(self, surface):
        kb_rows = self.layout_rects()
        if not kb_rows:
            return
        for label, rect in kb_rows:
            rrad = max(6, int(6 * SCALE))
            state = None
            if label not in ("ENTER", "DEL"):
                state = self.key_states.get(label, None)
            if state is None:
                base = (240, 241, 243)
                txt_color = TILE_TEXT
                border_col = (200, 205, 210)
            else:
                base = [C_ABSENT, C_PRESENT, C_CORRECT][state]
                txt_color = (255, 255, 255)
                border_col = None

            shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 28), shadow.get_rect(), border_radius=rrad)
            surface.blit(shadow, (rect.x + 1, rect.y + 2))

            pygame.draw.rect(surface, base, rect, border_radius=rrad)
            if border_col:
                pygame.draw.rect(surface, border_col, rect, width=max(1, int(2 * SCALE)), border_radius=rrad)

            txt = KEY_FONT.render(label, True, txt_color)
            surface.blit(txt, txt.get_rect(center=rect.center))


class Game:
    def __init__(self, answer, vocab, screen):
        self.answer = answer
        self.vocab = set(vocab)
        self.screen = screen
        self.grid = []
        size = tile_size()
        grid_width = COLS * size + (COLS - 1) * TILE_GAP
        grid_left = (WIDTH - grid_width) // 2
        self.grid_left = grid_left
        for r in range(ROWS):
            row = []
            for c in range(COLS):
                x = grid_left + c * (size + TILE_GAP)
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
        states = backend.Judge.evaluate(guess, self.answer)
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
        title = TITLE_FONT.render("WORDLE", True, TILE_TEXT)
        title_rect = title.get_rect(center=(WIDTH // 2, 56))
        surface.blit(title, title_rect)

        size = tile_size()
        grid_width = COLS * size + (COLS - 1) * TILE_GAP
        grid_height = ROWS * size + (ROWS - 1) * TILE_GAP
        outer_pad = int(12 * SCALE)
        outer_left = self.grid_left - outer_pad
        outer_top = TOP_OFFSET - outer_pad
        outer_rect = pygame.Rect(outer_left, outer_top, grid_width + outer_pad * 2, grid_height + outer_pad * 2)
        outer_radius = max(12, int(12 * SCALE))

        pygame.draw.rect(surface, TILE_BORDER, outer_rect, border_radius=outer_radius)

        inner_inset = max(6, int(6 * SCALE))
        inner_rect = outer_rect.inflate(-inner_inset * 2, -inner_inset * 2)
        pygame.draw.rect(surface, GRID_BG, inner_rect, border_radius=max(8, int(8 * SCALE)))

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
            pad = max(8, int(12 * SCALE))
            # place toast vertically between title bottom and grid top so it doesn't overlap the title
            grid_top = TOP_OFFSET
            toast_y = title_rect.bottom + (grid_top - title_rect.bottom) // 2
            rect = toast_surf.get_rect(center=(WIDTH // 2, toast_y))
            bg = pygame.Surface((rect.width + pad * 2, rect.height + pad * 2), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, 140), bg.get_rect(), border_radius=max(8, int(8 * SCALE)))
            surface.blit(bg, bg.get_rect(center=rect.center))
            surface.blit(toast_surf, rect)

        self.keyboard.draw(surface)

        for x, y, vx, vy, s, color, life in self.particles:
            pygame.draw.rect(surface, color, pygame.Rect(int(x), int(y), s, s))

        if self.win or self.lose:
            sw, sh = surface.get_size()
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surface.blit(overlay, (0, 0))

            modal_w = 420
            modal_h = 200
            mx = (sw - modal_w) // 2
            my = (sh - modal_h) // 2
            modal = pygame.Rect(mx, my, modal_w, modal_h)
            pygame.draw.rect(surface, (255, 255, 255), modal, border_radius=12)
            pygame.draw.rect(surface, TILE_BORDER, modal, width=2, border_radius=12)

            if self.win:
                title = "Congratulations!"
                sub = f"You guessed {self.answer.upper()}"
                color = C_CORRECT
            else:
                title = "Game Over"
                sub = f"Answer: {self.answer.upper()}"
                color = (180, 40, 40)

            title_s = UI_FONT.render(title, True, color)
            surface.blit(title_s, (modal.centerx - title_s.get_width()//2, my + 20))
            sub_s = UI_FONT.render(sub, True, TILE_TEXT)
            surface.blit(sub_s, (modal.centerx - sub_s.get_width()//2, my + 60))

            btn_w = 140
            btn_h = 44
            pad = 24
            restart = pygame.Rect(modal.left + pad, modal.bottom - pad - btn_h, btn_w, btn_h)
            quitb = pygame.Rect(modal.right - pad - btn_w, modal.bottom - pad - btn_h, btn_w, btn_h)
            pygame.draw.rect(surface, C_CORRECT if self.win else ACCENT, restart, border_radius=8)
            pygame.draw.rect(surface, TILE_BORDER, quitb, border_radius=8)
            rtxt = KEY_FONT.render("PLAY AGAIN", True, (255, 255, 255))
            qtxt = KEY_FONT.render("QUIT", True, TILE_TEXT)
            surface.blit(rtxt, (restart.centerx - rtxt.get_width()//2, restart.centery - rtxt.get_height()//2))
            surface.blit(qtxt, (quitb.centerx - qtxt.get_width()//2, quitb.centery - qtxt.get_height()//2))

            self.restart_rect = restart
            self.quit_rect = quitb
