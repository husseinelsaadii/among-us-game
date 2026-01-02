import pygame
import sys
import math
import time
import random
from enum import Enum

pygame.init()

# =========================
# SCREEN (9:16)
# =========================
WIDTH, HEIGHT = 540, 960
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mini Among Us")

clock = pygame.time.Clock()

# =========================
# COLORS
# =========================
WHITE = (255, 255, 255)
RED = (255, 80, 80)
GREEN = (100, 255, 100)
BLUE = (100, 150, 255)
BLACK = (0, 0, 0)
DARK_GRAY = (40, 40, 40)

# =========================
# FONTS
# =========================
font_small = pygame.font.SysFont("arial", 24)
font_medium = pygame.font.SysFont("arial", 32)
font_large = pygame.font.SysFont("arial", 48, bold=True)


# =========================
# GAME STATES
# =========================
class GameState(Enum):
    PLAYING = 1
    GAME_OVER = 2
    PAUSED = 3


# =========================
# LOAD ASSETS WITH ERROR HANDLING
# =========================
def load_image(path, size=None):
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except pygame.error:
        # Create placeholder if image not found
        print(f"Warning: Could not load {path}")
        img = pygame.Surface(size or (64, 64), pygame.SRCALPHA)
        img.fill((255, 0, 0, 128))  # Red placeholder
        return img


# Load assets
try:
    bg = pygame.image.load("assets/background.png").convert()
    bg = pygame.transform.scale(bg, (WIDTH, HEIGHT))
except:
    # Create gradient background
    bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        color_value = int(20 + (y / HEIGHT) * 30)
        pygame.draw.line(bg, (color_value, color_value, color_value), (0, y), (WIDTH, y))

PLAYER_SIZE = 80
ENEMY_SIZE = 80

player_img = load_image("assets/crewmate.png", (PLAYER_SIZE, PLAYER_SIZE))
enemy_img = load_image("assets/imposter.png", (ENEMY_SIZE, ENEMY_SIZE))
shadow_img = load_image("assets/shadow.png", (70, 30))


# =========================
# GAME OBJECTS
# =========================
class Player:
    def __init__(self):
        self.rect = player_img.get_rect(center=(WIDTH // 2, HEIGHT - 200))
        self.speed = 6
        self.velocity = pygame.Vector2(0, 0)

    def move(self, keys):
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1

        # Normalize diagonal movement
        if dx != 0 or dy != 0:
            length = math.hypot(dx, dy)
            dx /= length
            dy /= length

        self.velocity = pygame.Vector2(dx * self.speed, dy * self.speed)

        # Update position
        self.rect.x += self.velocity.x
        self.rect.y += self.velocity.y

        # Keep player on screen
        self.rect.clamp_ip(screen.get_rect())

    def draw(self, surface):
        # Draw shadow
        if shadow_img:
            surface.blit(shadow_img, (self.rect.centerx - 35, self.rect.bottom - 10))
        # Draw player
        surface.blit(player_img, self.rect)

    def reset(self):
        self.rect.center = (WIDTH // 2, HEIGHT - 200)


class Enemy:
    def __init__(self):
        self.rect = enemy_img.get_rect(center=(WIDTH // 2, 150))
        self.base_speed = 2.2
        self.speed = self.base_speed
        self.patrol_points = [
            (WIDTH // 4, 150),
            (3 * WIDTH // 4, 150),
            (WIDTH // 2, 300),
            (WIDTH // 4, 300),
            (3 * WIDTH // 4, 300)
        ]
        self.current_patrol = 0
        self.patrol_timer = 0
        self.patrol_duration = 3  # seconds
        self.is_patrolling = True

    def update(self, player_pos, dt):
        player_x, player_y = player_pos

        # Switch between patrolling and chasing
        dx = player_x - self.rect.centerx
        dy = player_y - self.rect.centery
        distance_to_player = math.hypot(dx, dy)

        # If player is close, chase them
        if distance_to_player < 300:
            self.is_patrolling = False
            self.patrol_timer = 0
        else:
            self.patrol_timer += dt
            if self.patrol_timer >= self.patrol_duration:
                self.is_patrolling = True
                self.current_patrol = (self.current_patrol + 1) % len(self.patrol_points)
                self.patrol_timer = 0

        # Movement logic
        if self.is_patrolling:
            # Move to patrol point
            target = self.patrol_points[self.current_patrol]
            tx = target[0] - self.rect.centerx
            ty = target[1] - self.rect.centery
            dist = math.hypot(tx, ty)

            if dist > 1:
                self.rect.x += self.speed * tx / dist
                self.rect.y += self.speed * ty / dist
        else:
            # Chase player
            if distance_to_player > 1:
                self.rect.x += self.speed * dx / distance_to_player
                self.rect.y += self.speed * dy / distance_to_player

        # Keep enemy on screen
        self.rect.clamp_ip(screen.get_rect())

        # Adjust speed based on distance to player (faster when closer)
        if not self.is_patrolling:
            self.speed = self.base_speed + (1.5 - distance_to_player / 200) * 0.5
            self.speed = max(self.base_speed, min(self.speed, 4.0))
        else:
            self.speed = self.base_speed

    def draw(self, surface):
        # Draw shadow
        if shadow_img:
            surface.blit(shadow_img, (self.rect.centerx - 35, self.rect.bottom - 10))
        # Draw enemy
        surface.blit(enemy_img, self.rect)

    def reset(self):
        self.rect.center = (WIDTH // 2, 150)
        self.speed = self.base_speed
        self.current_patrol = 0
        self.patrol_timer = 0
        self.is_patrolling = True


# =========================
# INITIALIZE GAME
# =========================
def init_game():
    global player, enemy, start_time, game_state, elapsed_time, high_score

    player = Player()
    enemy = Enemy()
    start_time = time.time()
    game_state = GameState.PLAYING
    elapsed_time = 0

    # Load high score
    try:
        with open("highscore.txt", "r") as f:
            high_score = float(f.read())
    except:
        high_score = 0.0


def save_high_score(score):
    global high_score
    if score > high_score:
        high_score = score
        try:
            with open("highscore.txt", "w") as f:
                f.write(str(score))
        except:
            pass


# Initialize game
init_game()

# =========================
# GAME LOOP
# =========================
while True:
    dt = clock.tick(60) / 1000.0  # Delta time in seconds

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if game_state == GameState.PLAYING:
                    game_state = GameState.PAUSED
                elif game_state == GameState.PAUSED:
                    game_state = GameState.PLAYING

            if game_state == GameState.GAME_OVER and event.key == pygame.K_r:
                init_game()

            if game_state == GameState.PLAYING and event.key == pygame.K_p:
                game_state = GameState.PAUSED
            elif game_state == GameState.PAUSED and event.key == pygame.K_p:
                game_state = GameState.PLAYING

    # Get keyboard state
    keys = pygame.key.get_pressed()

    # Game logic based on state
    if game_state == GameState.PLAYING:
        # Update player
        player.move(keys)

        # Update enemy
        enemy.update(player.rect.center, dt)

        # Check collision
        if player.rect.colliderect(enemy.rect):
            game_state = GameState.GAME_OVER
            elapsed_time = time.time() - start_time
            save_high_score(elapsed_time)

    elif game_state == GameState.PAUSED:
        # Pause logic (just display pause screen)
        pass

    # =========================
    # DRAWING
    # =========================
    # Draw background
    screen.blit(bg, (0, 0))

    # Draw game objects
    player.draw(screen)
    enemy.draw(screen)

    # Draw timer
    if game_state == GameState.PLAYING:
        elapsed = time.time() - start_time
    else:
        elapsed = elapsed_time

    timer_text = font_medium.render(f"TIME: {elapsed:.1f}s", True, WHITE)
    screen.blit(timer_text, (20, 20))

    # Draw high score
    high_score_text = font_small.render(f"BEST: {high_score:.1f}s", True, GREEN)
    screen.blit(high_score_text, (WIDTH - high_score_text.get_width() - 20, 20))

    # Draw controls hint
    controls_text = font_small.render("WASD/Arrows: Move | P: Pause | ESC: Menu", True, (200, 200, 200))
    screen.blit(controls_text, (WIDTH // 2 - controls_text.get_width() // 2, HEIGHT - 40))

    # Game state specific drawing
    if game_state == GameState.GAME_OVER:
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Game over text
        over_text = font_large.render("GAME OVER", True, RED)
        time_text = font_medium.render(f"Survived: {elapsed_time:.1f}s", True, WHITE)
        best_text = font_medium.render(f"Best: {high_score:.1f}s", True, GREEN if elapsed_time >= high_score else WHITE)
        retry_text = font_medium.render("Press R to Restart", True, BLUE)

        screen.blit(over_text, (WIDTH // 2 - over_text.get_width() // 2, HEIGHT // 2 - 100))
        screen.blit(time_text, (WIDTH // 2 - time_text.get_width() // 2, HEIGHT // 2 - 30))
        screen.blit(best_text, (WIDTH // 2 - best_text.get_width() // 2, HEIGHT // 2 + 10))
        screen.blit(retry_text, (WIDTH // 2 - retry_text.get_width() // 2, HEIGHT // 2 + 70))

    elif game_state == GameState.PAUSED:
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Pause text
        pause_text = font_large.render("PAUSED", True, BLUE)
        continue_text = font_medium.render("Press P or ESC to Continue", True, WHITE)

        screen.blit(pause_text, (WIDTH // 2 - pause_text.get_width() // 2, HEIGHT // 2 - 50))
        screen.blit(continue_text, (WIDTH // 2 - continue_text.get_width() // 2, HEIGHT // 2 + 20))

    # Update display
    pygame.display.flip()