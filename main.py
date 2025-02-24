import pygame
import random

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
BLOCK_SIZE = 30
GRID_WIDTH = 10
GRID_HEIGHT = 20
GRID_OFFSET_X = (SCREEN_WIDTH - BLOCK_SIZE * GRID_WIDTH) // 2
GRID_OFFSET_Y = SCREEN_HEIGHT - BLOCK_SIZE * GRID_HEIGHT - 50

# Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
COLORS = [
    (0, 255, 255),  # I
    (255, 165, 0),  # L
    (0, 0, 255),  # J
    (255, 255, 0),  # O
    (128, 0, 128),  # T
    (255, 0, 0),  # Z
    (0, 255, 0)  # S
]

# Фигуры тетрамино
SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[1, 0], [1, 0], [1, 1]],  # L
    [[0, 1], [0, 1], [1, 1]],  # J
    [[1, 1], [1, 1]],  # O
    [[1, 1, 1], [0, 1, 0]],  # T
    [[1, 1, 0], [0, 1, 1]],  # Z
    [[0, 1, 1], [1, 1, 0]]  # S
]

class Block(pygame.sprite.Sprite):
    def __init__(self, color, x, y):
        super().__init__()
        self.image = pygame.Surface((BLOCK_SIZE - 1, BLOCK_SIZE - 1))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))

class Explosion(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.frames = [
            pygame.image.load(f"Sprites/explosion_{i}.png") for i in range(1, 14)
        ]
        self.current_frame = 0
        self.image = self.frames[self.current_frame]
        self.rect = self.image.get_rect(center=(x, y))
        self.animation_speed = 100
        self.last_update = pygame.time.get_ticks()

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_update > self.animation_speed:
            self.last_update = now
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                self.kill()
            else:
                self.image = self.frames[self.current_frame]

class Tetris:
    def __init__(self):
        self.grid = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.score = 0
        self.level = 1
        self.current_piece = None
        self.next_piece = None
        self.game_over = False
        self.all_sprites = pygame.sprite.Group()
        self.explosions = pygame.sprite.Group()
        self.new_piece()

    def draw_border(self, screen):
        # Рисуем рамку вокруг игрового поля
        pygame.draw.rect(screen, WHITE, (GRID_OFFSET_X - 2, GRID_OFFSET_Y - 2, GRID_WIDTH * BLOCK_SIZE + 4, GRID_HEIGHT * BLOCK_SIZE + 4), 2)

    def draw_next_piece(self, screen):
        if self.next_piece:
            shape = SHAPES[self.next_piece]
            color = COLORS[self.next_piece]
            for y, row in enumerate(shape):
                for x, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(screen, color, (
                            SCREEN_WIDTH - 150 + x * BLOCK_SIZE,
                            50 + y * BLOCK_SIZE,
                            BLOCK_SIZE - 1,
                            BLOCK_SIZE - 1
                        ))

    def draw_score_and_level(self, screen):
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Текущий счет: {self.score}", True, WHITE)
        level_text = font.render(f"Уровень: {self.level}", True, WHITE)
        screen.blit(score_text, (SCREEN_WIDTH - 150, 200))
        screen.blit(level_text, (SCREEN_WIDTH - 150, 250))

    def new_piece(self):
        if not self.next_piece:
            self.next_piece = random.choice(range(len(SHAPES)))
        self.current_piece = {
            'shape': SHAPES[self.next_piece],
            'color': COLORS[self.next_piece],
            'x': GRID_WIDTH // 2 - len(SHAPES[self.next_piece][0]) // 2,
            'y': 0
        }
        self.next_piece = random.choice(range(len(SHAPES)))

    def check_collision(self, shape, offset):
        dx, dy = offset
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    if x + dx < 0 or x + dx >= GRID_WIDTH or \
                            y + dy >= GRID_HEIGHT or \
                            (y + dy >= 0 and self.grid[y + dy][x + dx]):
                        return True
        return False

    def rotate(self):
        shape = self.current_piece['shape']
        rotated = list(zip(*reversed(shape)))
        if not self.check_collision(rotated, (self.current_piece['x'], self.current_piece['y'])):
            self.current_piece['shape'] = rotated

    def move(self, dx, dy):
        new_x = self.current_piece['x'] + dx
        new_y = self.current_piece['y'] + dy
        if not self.check_collision(self.current_piece['shape'], (new_x, new_y)):
            self.current_piece['x'] = new_x
            self.current_piece['y'] = new_y
            return True
        return False

    def drop(self):
        if not self.move(0, 1):
            self.lock_piece()

    def lock_piece(self):
        shape = self.current_piece['shape']
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    if self.current_piece['y'] + y < 0:
                        self.game_over = True
                        return
                    self.grid[self.current_piece['y'] + y][self.current_piece['x'] + x] = self.current_piece['color']
                    block = Block(
                        self.current_piece['color'],
                        GRID_OFFSET_X + (self.current_piece['x'] + x) * BLOCK_SIZE,
                        GRID_OFFSET_Y + (self.current_piece['y'] + y) * BLOCK_SIZE
                    )
                    self.all_sprites.add(block)
        self.clear_lines()
        self.new_piece()

    def clear_lines(self):
        lines_cleared = 0
        rows_to_remove = []
        for y in range(GRID_HEIGHT):
            if all(self.grid[y]):
                rows_to_remove.append(y)
                lines_cleared += 1

        if rows_to_remove:
            for y in rows_to_remove:
                for x in range(GRID_WIDTH):
                    for block in self.all_sprites:
                        if block.rect.collidepoint(
                                GRID_OFFSET_X + x * BLOCK_SIZE + BLOCK_SIZE // 2,
                                GRID_OFFSET_Y + y * BLOCK_SIZE + BLOCK_SIZE // 2
                        ):
                            block.kill()
                    explosion = Explosion(
                        GRID_OFFSET_X + x * BLOCK_SIZE + BLOCK_SIZE // 2,
                        GRID_OFFSET_Y + y * BLOCK_SIZE + BLOCK_SIZE // 2
                    )
                    self.explosions.add(explosion)

            for y in reversed(range(GRID_HEIGHT)):
                if y < rows_to_remove[-1]:
                    self.grid[y + lines_cleared] = self.grid[y]
                    self.grid[y] = [0] * GRID_WIDTH

            self.all_sprites.empty()
            for y in range(GRID_HEIGHT):
                for x in range(GRID_WIDTH):
                    if self.grid[y][x]:
                        block = Block(
                            self.grid[y][x],
                            GRID_OFFSET_X + x * BLOCK_SIZE,
                            GRID_OFFSET_Y + y * BLOCK_SIZE
                        )
                        self.all_sprites.add(block)

            self.score += [40, 100, 300, 1200][lines_cleared - 1] * self.level
            self.level = 1 + self.score // 1000
            # Обновляем скорость падения в зависимости от уровня
            global fall_speed
            fall_speed = max(100, 1000 - (self.level - 1) * 100)

    def draw(self, screen):
        screen.fill(BLACK)
        self.draw_border(screen)

        # Отрисовка сетки и текущей фигуры
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.grid[y][x]:
                    pygame.draw.rect(screen, self.grid[y][x], (
                        GRID_OFFSET_X + x * BLOCK_SIZE,
                        GRID_OFFSET_Y + y * BLOCK_SIZE,
                        BLOCK_SIZE - 1,
                        BLOCK_SIZE - 1
                    ))

        if self.current_piece:
            shape = self.current_piece['shape']
            for y, row in enumerate(shape):
                for x, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(screen, self.current_piece['color'], (
                            GRID_OFFSET_X + (self.current_piece['x'] + x) * BLOCK_SIZE,
                            GRID_OFFSET_Y + (self.current_piece['y'] + y) * BLOCK_SIZE,
                            BLOCK_SIZE - 1,
                            BLOCK_SIZE - 1
                        ))

        # Отрисовка всех спрайтов
        self.all_sprites.draw(screen)
        self.explosions.draw(screen)

        # Отрисовка следующей фигуры, счета и уровня
        self.draw_next_piece(screen)
        self.draw_score_and_level(screen)

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Tetris")
    clock = pygame.time.Clock()
    game = Tetris()

    global fall_speed
    fall_time = 0
    fall_speed = 1000

    while not game.game_over:
        screen.fill(BLACK)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    game.move(-1, 0)
                if event.key == pygame.K_RIGHT:
                    game.move(1, 0)
                if event.key == pygame.K_DOWN:
                    game.drop()
                if event.key == pygame.K_UP:
                    game.rotate()

        delta_time = clock.tick(60)
        fall_time += delta_time
        if fall_time >= fall_speed:
            game.drop()
            fall_time = 0

        game.all_sprites.update()
        game.explosions.update()

        game.draw(screen)
        pygame.display.flip()

    font = pygame.font.Font(None, 74)
    text = font.render("GAME OVER", True, WHITE)
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - text.get_height() // 2))
    pygame.display.flip()
    pygame.time.wait(3000)
    pygame.quit()

if __name__ == "__main__":
    main()