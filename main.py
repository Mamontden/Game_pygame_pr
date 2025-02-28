import pygame
import random
import sys
import sqlite3
from datetime import datetime

pygame.init()
pygame.mixer.init()

explosion_sound = pygame.mixer.Sound("Sounds/explosion.mp3")
explosion_sound.set_volume(0.5)  # Настройка громкости

# Константы
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
    (0, 255, 255),
    (255, 165, 0),
    (0, 0, 255),
    (255, 255, 0),
    (128, 0, 128),
    (255, 0, 0),
    (0, 255, 0)
]

# Фигуры
SHAPES = [
    [[1, 1, 1, 1]],
    [[1, 0], [1, 0], [1, 1]],
    [[0, 1], [0, 1], [1, 1]],
    [[1, 1], [1, 1]],
    [[1, 1, 1], [0, 1, 0]],
    [[1, 1, 0], [0, 1, 1]],
    [[0, 1, 1], [1, 1, 0]]
]


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect("data/tetris_scores.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            score INTEGER NOT NULL,
            level INTEGER NOT NULL,
            date TEXT NOT NULL,
            mode TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# Сохранение результатов в таблицу лидеров
def save_score(player_name, score, level, mode):
    conn = sqlite3.connect("data/tetris_scores.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scores (player_name, score, level, date, mode)
        VALUES (?, ?, ?, ?, ?)
    """, (player_name, score, level, datetime.now().strftime("%d.%m.%Y"), mode))
    conn.commit()
    conn.close()


class Block(pygame.sprite.Sprite):
    def __init__(self, color=None, image=None, x=0, y=0, value=None):
        super().__init__()
        self.base_image = image.copy() if image else pygame.Surface((BLOCK_SIZE - 1, BLOCK_SIZE - 1))
        if color:
            self.base_image.fill(color)
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.value = value
        if self.value is not None:
            self.add_text(str(self.value))

    def add_text(self, text):
        font = pygame.font.Font(None, 24)
        text_surface = font.render(text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.image.get_rect().center)
        self.image = self.base_image.copy()
        self.image.blit(text_surface, text_rect)

    def update_value(self, new_value):
        self.value = new_value
        self.add_text(str(new_value))


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
        self.paused = False
        self.new_piece()

    def draw_border(self, screen):
        pygame.draw.rect(screen, WHITE, (
            GRID_OFFSET_X - 2, GRID_OFFSET_Y - 2, GRID_WIDTH * BLOCK_SIZE + 4, GRID_HEIGHT * BLOCK_SIZE + 4), 2)

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
        score_text = font.render(f"Счет: {self.score}", True, WHITE)
        level_text = font.render(f"Уровень: {self.level}", True, WHITE)
        screen.blit(score_text, (SCREEN_WIDTH - 150, 200))
        screen.blit(level_text, (SCREEN_WIDTH - 150, 250))

    def new_piece(self):
        if not self.next_piece:
            self.next_piece = random.choice(range(len(SHAPES)))

        # Создание фигуры
        self.current_piece = {
            'shape': SHAPES[self.next_piece],
            'color': COLORS[self.next_piece],
            'x': GRID_WIDTH // 2 - len(SHAPES[self.next_piece][0]) // 2,
            'y': 0
        }

        # Проверка размещения фигуры
        if self.check_collision(self.current_piece['shape'], (self.current_piece['x'], self.current_piece['y'])):
            self.game_over = True  # Если фигура не может быть размещена, игра завершается
            return

        # Создание следующей фигуры для показа
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
                    # Если фигура выходит за пределы поля, игра завершается
                    if self.current_piece['y'] + y < 0:
                        self.game_over = True
                        return
                    # Размещаем фигуру на поле
                    self.grid[self.current_piece['y'] + y][self.current_piece['x'] + x] = self.current_piece['color']
                    block = Block(
                        color=self.current_piece['color'],
                        x=GRID_OFFSET_X + (self.current_piece['x'] + x) * BLOCK_SIZE,
                        y=GRID_OFFSET_Y + (self.current_piece['y'] + y) * BLOCK_SIZE
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
            # Удаление заполненых строк и создание взрыва
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
                        explosion_sound.play()  # Воспроизведение звука взрыва

            # Падение оставшихся строк вниз
            for y in reversed(range(GRID_HEIGHT)):
                if y in rows_to_remove:
                    continue  # Пропускаем удаленные строки
                new_y = y + lines_cleared
                if new_y < GRID_HEIGHT:
                    self.grid[new_y] = self.grid[y]
                self.grid[y] = [0] * GRID_WIDTH

            # Обновление спрайтов
            self.all_sprites.empty()
            for y in range(GRID_HEIGHT):
                for x in range(GRID_WIDTH):
                    if self.grid[y][x]:
                        block = Block(
                            color=self.grid[y][x],
                            x=GRID_OFFSET_X + x * BLOCK_SIZE,
                            y=GRID_OFFSET_Y + y * BLOCK_SIZE
                        )
                        self.all_sprites.add(block)

            # Обновление счета и уровня
            self.score += [40, 100, 300, 1200][lines_cleared - 1] * self.level
            self.level = 1 + self.score // 1000
            global fall_speed
            fall_speed = max(100, 1000 - (self.level - 1) * 100)
            # Отладочный вывод сетки
            # print("Сетка после удаления строк:")
            # for row in self.grid:
            #     print(row)

    def draw(self, screen):
        screen.fill(BLACK)
        self.draw_border(screen)

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

        self.all_sprites.draw(screen)
        self.explosions.draw(screen)
        self.draw_next_piece(screen)
        self.draw_score_and_level(screen)


class TetrisMath:
    def __init__(self):
        self.examples = self.load_examples("data/examples.txt")
        self.cube_texture = pygame.image.load("Sprites/cube.png").convert_alpha()
        self.cube_texture = pygame.transform.scale(self.cube_texture, (BLOCK_SIZE, BLOCK_SIZE))
        self.grid = [[{'texture': None, 'value': None} for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.score = 0
        self.level = 1
        self.current_piece = None
        self.game_over = False
        self.all_sprites = pygame.sprite.Group()
        self.explosions = pygame.sprite.Group()
        self.paused = False
        self.piece_count = 0  # Счетчик фигур
        self.new_piece()

    def draw_score_and_level(self, screen):
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Счет: {self.score}", True, WHITE)
        level_text = font.render(f"Уровень: {self.level}", True, WHITE)
        screen.blit(score_text, (SCREEN_WIDTH - 150, 200))
        screen.blit(level_text, (SCREEN_WIDTH - 150, 250))

    def drop(self):
        if not self.move(0, 1):
            self.lock_piece()

    def move(self, dx, dy):
        new_x = self.current_piece['x'] + dx
        new_y = self.current_piece['y'] + dy
        if not self.check_collision(self.current_piece['shape'], (new_x, new_y)):
            self.current_piece['x'] = new_x
            self.current_piece['y'] = new_y
            return True
        return False

    def rotate(self):
        shape = self.current_piece['shape']
        rotated = list(zip(*reversed(shape)))
        if not self.check_collision(rotated, (self.current_piece['x'], self.current_piece['y'])):
            self.current_piece['shape'] = rotated

    def load_examples(self, filename):
        try:
            with open(filename, "r") as file:
                return [line.strip() for line in file]
        except FileNotFoundError:
            return ["2+2", "3*3", "5-1"]

    def lock_piece(self):
        shape = self.current_piece['shape']
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    gy = self.current_piece['y'] + y
                    gx = self.current_piece['x'] + x
                    if gy < 0:
                        self.game_over = True
                        return
                    self.grid[gy][gx] = {
                        'texture': self.cube_texture,
                        'value': self.current_piece['answer']
                    }
                    block = Block(
                        image=self.cube_texture,
                        x=GRID_OFFSET_X + gx * BLOCK_SIZE,
                        y=GRID_OFFSET_Y + gy * BLOCK_SIZE,
                        value=self.current_piece['answer']
                    )
                    self.all_sprites.add(block)

        self.check_merge()
        self.check_explosions()
        self.new_piece()

    def check_explosions(self):
        # Проверка кубиков
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.grid[y][x]['value'] and self.grid[y][x]['value'] >= 1000:
                    # взрыв
                    self.create_explosion(x, y)
                    # Удаление кубика
                    self.grid[y][x] = {'texture': None, 'value': None}
                    # Удаление спрайта
                    for block in self.all_sprites:
                        if block.rect.collidepoint(
                                GRID_OFFSET_X + x * BLOCK_SIZE + BLOCK_SIZE // 2,
                                GRID_OFFSET_Y + y * BLOCK_SIZE + BLOCK_SIZE // 2
                        ):
                            block.kill()
                    # очки
                    self.score += 1000

    def create_explosion(self, x, y):
        explosion = Explosion(
            GRID_OFFSET_X + x * BLOCK_SIZE + BLOCK_SIZE // 2,
            GRID_OFFSET_Y + y * BLOCK_SIZE + BLOCK_SIZE // 2
        )
        self.explosions.add(explosion)
        explosion_sound.play()

    def clear_lines(self):
        lines_cleared = 0
        rows_to_remove = []

        for y in range(GRID_HEIGHT):
            if all(cell['texture'] is not None for cell in self.grid[y]):
                rows_to_remove.append(y)
                lines_cleared += 1

        if rows_to_remove:
            # Только удаление строк без взрывов
            new_grid = [row for i, row in enumerate(self.grid) if i not in rows_to_remove]
            new_grid = [[{'texture': None, 'value': None} for _ in range(GRID_WIDTH)]
                        for _ in range(lines_cleared)] + new_grid
            self.grid = new_grid
            self.all_sprites.empty()
            for y in range(GRID_HEIGHT):
                for x in range(GRID_WIDTH):
                    if self.grid[y][x]['texture']:
                        block = Block(
                            image=self.cube_texture,
                            x=GRID_OFFSET_X + x * BLOCK_SIZE,
                            y=GRID_OFFSET_Y + y * BLOCK_SIZE,
                            value=self.grid[y][x]['value']
                        )
                        self.all_sprites.add(block)

    def check_merge(self):
        merged = False
        for y in range(GRID_HEIGHT - 2, -1, -1):
            for x in range(GRID_WIDTH):
                current = self.grid[y][x]
                if not current['texture']:
                    continue
                below = self.grid[y + 1][x]
                if below['texture'] and current['value'] == below['value']:
                    # Объединение значений
                    new_value = current['value'] + below['value']
                    self.grid[y + 1][x]['value'] = new_value
                    self.grid[y][x] = {'texture': None, 'value': None}

                    # Обновление спрайтов
                    for block in self.all_sprites:
                        if block.rect.collidepoint(
                                GRID_OFFSET_X + x * BLOCK_SIZE + BLOCK_SIZE // 2,
                                GRID_OFFSET_Y + (y + 1) * BLOCK_SIZE + BLOCK_SIZE // 2
                        ):
                            block.update_value(new_value)
                            self.score += new_value
                        if block.rect.collidepoint(
                                GRID_OFFSET_X + x * BLOCK_SIZE + BLOCK_SIZE // 2,
                                GRID_OFFSET_Y + y * BLOCK_SIZE + BLOCK_SIZE // 2
                        ):
                            block.kill()
                    merged = True
        if merged:
            self.check_merge()

    def load_examples(self, filename):
        try:
            with open(filename, "r") as file:
                examples = file.readlines()
            return [ex.strip() for ex in examples]
        except FileNotFoundError:
            print(f"Файл {filename} не найден!")
            return ["2+2", "3*3", "5-1"]

    def new_piece(self):
        self.piece_count += 1  # нужен для отсчета 10 фигур. После этого примеры гарантировано генерируются с результатом
        # из верхнего слоя кубиков
        if self.piece_count >= 10:
            # Собираем значения из верхних 5 рядов
            existing_values = []
            for y in range(min(5, GRID_HEIGHT)):
                for x in range(GRID_WIDTH):
                    if self.grid[y][x]['value'] is not None:
                        existing_values.append(self.grid[y][x]['value'])

            if existing_values:
                target = random.choice(existing_values)
                example = f"{target} + 0"  # Простой пример с гарантированным ответом
                answer = target
            else:
                example = "1 + 1"
                answer = 2
        else:
            # Берем пример из списка
            if not self.examples:
                self.examples = self.load_examples("data/examples.txt")
            example = self.examples.pop(0) if self.examples else "0+0"
            try:
                answer = eval(example)
            except:
                answer = 0

        self.current_piece = {
            'shape': [[1, 1]],
            'texture': self.cube_texture,
            'x': GRID_WIDTH // 2 - 1,  # Центрирование для формы 2x1
            'y': 0,
            'example': example,
            'answer': answer
        }

        if self.check_collision(self.current_piece['shape'], (self.current_piece['x'], self.current_piece['y'])):
            self.game_over = True

    def check_collision(self, shape, offset):
        dx, dy = offset
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    if x + dx < 0 or x + dx >= GRID_WIDTH:
                        return True
                    if y + dy >= GRID_HEIGHT:
                        return True
                    if y + dy >= 0 and self.grid[y + dy][x + dx]['texture']:
                        return True
        return False

    # Пока убрал, но удалять не стал, так при модификации игры может понадобится
    def draw_next_piece(self, screen):
        pass
        # # Отображение примера в вверхнем правом углу
        # font = pygame.font.Font(None, 36)
        # if self.current_piece:
        #     text = font.render(f"Реши: {self.current_piece['example']}", True, WHITE)
        #     screen.blit(text, (20, 20))

    def draw(self, screen):
        screen.fill(BLACK)
        self.draw_border(screen)
        if self.current_piece and not self.game_over:
            piece = self.current_piece
            for y, row in enumerate(piece['shape']):
                for x, cell in enumerate(row):
                    if cell:
                        # Текстура фигуры
                        screen.blit(piece['texture'], (
                            GRID_OFFSET_X + (piece['x'] + x) * BLOCK_SIZE,
                            GRID_OFFSET_Y + (piece['y'] + y) * BLOCK_SIZE
                        ))

        # Отрисовка блоков
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                cell = self.grid[y][x]
                if cell['texture']:
                    # Отрисовка текстуры блока
                    screen.blit(cell['texture'], (
                        GRID_OFFSET_X + x * BLOCK_SIZE,
                        GRID_OFFSET_Y + y * BLOCK_SIZE
                    ))
                    # Отрисовка значения
                    if cell['value'] is not None:
                        font = pygame.font.Font(None, 24)
                        text = font.render(str(cell['value']), True, WHITE)
                        text_rect = text.get_rect(
                            center=(GRID_OFFSET_X + x * BLOCK_SIZE + BLOCK_SIZE // 2,
                                    GRID_OFFSET_Y + y * BLOCK_SIZE + BLOCK_SIZE // 2)
                        )
                        screen.blit(text, text_rect)

        # Отображение текущего примера
        font = pygame.font.Font(None, 36)
        if self.current_piece:
            example_text = font.render(f"Пример: {self.current_piece['example']}", True, WHITE)
            screen.blit(example_text, (20, 20))

    def draw_border(self, screen):
        pygame.draw.rect(screen, WHITE, (
            GRID_OFFSET_X - 2,
            GRID_OFFSET_Y - 2,
            GRID_WIDTH * BLOCK_SIZE + 4,
            GRID_HEIGHT * BLOCK_SIZE + 4
        ), 2)


class GameModeSelection:
    def __init__(self):
        self.font = pygame.font.Font(None, 74)
        self.options = [
            "Классический Тетрис",
            "Тетрис с примерами",
            "Таблица рекордов",
            "Выход"
        ]
        self.selected = 0

    def draw(self, screen):
        screen.fill(BLACK)
        for i, option in enumerate(self.options):
            color = WHITE if i == self.selected else (128, 128, 128)
            text = self.font.render(option, True, color)
            screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2,
                            SCREEN_HEIGHT//2 - 150 + i*75))  # Уменьшаем расстояние

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            if event.key == pygame.K_RETURN:
                return self.selected
        return None

# Ввод имени.

class NameInputScreen:
    def __init__(self):
        self.font = pygame.font.Font(None, 74)
        self.input_text = ""
        self.active = True

    def draw(self, screen):
        screen.fill(BLACK)
        prompt_text = self.font.render("Введите свое имя:", True, WHITE)
        input_text = self.font.render(self.input_text, True, WHITE)
        screen.blit(prompt_text, (SCREEN_WIDTH // 2 - prompt_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(input_text, (SCREEN_WIDTH // 2 - input_text.get_width() // 2, SCREEN_HEIGHT // 2 + 50))

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                self.input_text += event.unicode


class MainMenu:
    def __init__(self):
        self.font = pygame.font.Font(None, 74)
        self.options = ["Начать играть", "Таблица рекордов", "Выход"]
        self.selected = 0

    def draw(self, screen):
        screen.fill(BLACK)
        for i, option in enumerate(self.options):
            color = WHITE if i == self.selected else (128, 128, 128)
            text = self.font.render(option, True, color)
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - 100 + i * 100))

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            if event.key == pygame.K_RETURN:
                return self.selected
        return None


class GameOverScreen:
    def __init__(self, score):
        self.font = pygame.font.Font(None, 74)
        self.options = ["Заново", "Главное меню"]
        self.selected = 0
        self.score = score

    def draw(self, screen):
        screen.fill(BLACK)
        game_over_text = self.font.render("Game Over", True, WHITE)
        score_text = self.font.render(f"Счет: {self.score}", True, WHITE)
        screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 2 - 200))
        screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2 - 100))
        for i, option in enumerate(self.options):
            color = WHITE if i == self.selected else (128, 128, 128)
            text = self.font.render(option, True, color)
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 + i * 100))

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            if event.key == pygame.K_RETURN:
                return self.selected
        return None


# таблица рекордов
class HighScoresScreen:
    def __init__(self):
        self.font = pygame.font.Font(None, 36)
        self.options = ["Главное меню"]
        self.selected = 0

    def draw(self, screen):
        screen.fill(BLACK)
        title_text = self.font.render("Таблица рекордов", True, WHITE)
        screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 50))

        # База данных
        conn = sqlite3.connect("data/tetris_scores.db")
        cursor = conn.cursor()
        cursor.execute("SELECT player_name, score, level, date FROM scores ORDER BY score DESC LIMIT 10")
        scores = cursor.fetchall()
        conn.close()

        # отображение таблицы лидеров
        y_offset = 150
        for i, (player_name, score, level, date) in enumerate(scores):
            score_text = self.font.render(f"{i + 1}. {player_name}: {score} (Уровень {level}) - {date}", True, WHITE)
            screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, y_offset))
            y_offset += 50

        # Отображение опций
        for i, option in enumerate(self.options):
            color = WHITE if i == self.selected else (128, 128, 128)
            text = self.font.render(option, True, color)
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y_offset + 100 + i * 50))

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            if event.key == pygame.K_RETURN:
                return self.selected
        return None


def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Тетрис")
    clock = pygame.time.Clock()

    # Инициализация базы данных
    init_db()

    # Выбор режима игры
    mode_selection = GameModeSelection()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            selected = mode_selection.handle_input(event)
            if selected == 0 or selected == 1:
                if selected == 0:  # Классический Тетрис
                    game = Tetris()
                elif selected == 1:  # Тетрис с примерами
                    game = TetrisMath()

                # Экран ввода имени
                name_input = NameInputScreen()
                while name_input.active:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()
                        name_input.handle_input(event)
                    name_input.draw(screen)
                    pygame.display.flip()

                player_name = name_input.input_text
                if not player_name:
                    player_name = "Балбес"

                # Запуск игры
                fall_time = 0
                global fall_speed
                fall_speed = 1000

                # Переменная для отслеживания состояния клавиши вниз
                fast_fall = False

                # оновной цикл
                while not game.game_over:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()
                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_LEFT:
                                game.move(-1, 0)
                            if event.key == pygame.K_RIGHT:
                                game.move(1, 0)
                            if event.key == pygame.K_DOWN:
                                fast_fall = True  # Ускоренное падение
                            if event.key == pygame.K_UP:
                                game.rotate()
                            if event.key == pygame.K_SPACE:  # Пауза на пробел
                                game.paused = not game.paused
                        if event.type == pygame.KEYUP:
                            if event.key == pygame.K_DOWN:
                                fast_fall = False  # Отключение ускоренного падения

                    if not game.paused:  # Если игра не на паузе
                        delta_time = clock.tick(60)
                        fall_time += delta_time

                        # Ускоренное падение, если клавиша вниз нажата
                        if fast_fall:
                            fall_speed_fast = 100  # Скорость падения при ускорении
                            if fall_time >= fall_speed_fast:
                                game.drop()
                                fall_time = 0
                        else:
                            if fall_time >= fall_speed:
                                game.drop()
                                fall_time = 0

                        game.all_sprites.update()
                        game.explosions.update()

                    game.draw(screen)
                    if game.paused:  # Экран при нажатии паузы
                        font = pygame.font.Font(None, 74)
                        pause_text = font.render("Пауза", True, WHITE)
                        screen.blit(pause_text, (SCREEN_WIDTH // 2 - pause_text.get_width() // 2, SCREEN_HEIGHT // 2))
                    pygame.display.flip()

                # Сохранение результата
                save_score(player_name, game.score, game.level, "classic" if selected == 0 else "math")

                # Экран Game Over
                game_over_screen = GameOverScreen(game.score)
                while True:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()
                        selected = game_over_screen.handle_input(event)
                        if selected is not None:
                            if selected == 0:  # заново
                                break
                            if selected == 1:  # Главное меню
                                break
                    if selected is not None:
                        break
                    game_over_screen.draw(screen)
                    pygame.display.flip()

                if selected == 1:  # Вернуться в меню
                    continue  # Возвращаемся в главное меню
                elif selected == 0:  # Заново
                    continue  # Запускаем новую игру
            elif selected == 2:  # Таблица рекордов
                # Показ таблицы рекордов
                high_scores = HighScoresScreen()
                while True:
                    for e in pygame.event.get():
                        if e.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()
                        result = high_scores.handle_input(e)
                        if result is not None:  # Нажата кнопка "Назад"
                            break

                    high_scores.draw(screen)
                    pygame.display.flip()
                    clock.tick(60)


            elif selected == 3:  # Выход
                pygame.quit()
                sys.exit()
        mode_selection.draw(screen)
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
