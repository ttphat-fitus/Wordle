import pygame
import backend
import frontend

def main():
    pygame.init()
    pygame.display.set_caption("Wordle")

    info = pygame.display.Info()
    screen_w, screen_h = info.current_w, info.current_h
    max_w = int(screen_w * 0.8)
    max_h = int(screen_h * 0.8)

    scale = frontend.compute_best_scale(max_w, max_h)

    frontend.setup_fonts(scale)
    SCREEN = pygame.display.set_mode((frontend.WIDTH, frontend.HEIGHT))
    CLOCK = pygame.time.Clock()

    VOCAB = backend.get_vocab()
    TARGET = backend.pick_daily_word(VOCAB)
    try:
        print(f"Word: {TARGET}")
    except Exception:
        pass

    game = frontend.Game(TARGET, VOCAB, SCREEN)

    running = True
    while running:
        dt = CLOCK.tick(frontend.FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if getattr(game, 'win', False) or getattr(game, 'lose', False):
                    if event.key == pygame.K_SPACE:
                        new_vocab = backend.get_vocab(reload=True)
                        new_target = backend.pick_daily_word(new_vocab)
                        try:
                            print(f"Word: {new_target}")
                        except Exception:
                            pass
                        game = frontend.Game(new_target, new_vocab, SCREEN)
                        continue
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                        continue
                    else:
                        continue
                frontend.handle_key(game, event)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if getattr(game, 'win', False) or getattr(game, 'lose', False):
                    if getattr(game, 'restart_rect', None) and game.restart_rect.collidepoint(event.pos):
                        new_vocab = backend.get_vocab(reload=True)
                        new_target = backend.pick_daily_word(new_vocab)
                        try:
                            print(f"Word: {new_target}")
                        except Exception:
                            pass
                        game = frontend.Game(new_target, new_vocab, SCREEN)
                        continue
                    if getattr(game, 'quit_rect', None) and game.quit_rect.collidepoint(event.pos):
                        running = False
                        break

                label = game.keyboard.key_at(event.pos)
                if label:
                    print(f"Clicked label: {label}")
                    if label in ("ENTER", "Enter"):
                        game.submit()
                    elif label in ("⌫", "Delete", "Del", "DEL"):
                        game.backspace()
                    else:
                        ch = label
                        if isinstance(ch, str) and len(ch) == 1:
                            game.add_char(ch)

        game.update(dt)
        game.draw(SCREEN)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
