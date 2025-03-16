import pygame
import random
import math

# Initialize Pygame and mixer for sound
pygame.mixer.pre_init(44100, -16, 1, 512)  # Pre-initialize mixer with 44.1kHz, 16-bit, mono, small buffer for low latency
pygame.init()  # Initialize Pygame
pygame.display.set_caption("Pong")  # Set the window title

# Game configuration constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60  # Frames per second
BALL_SIZE = 10     # Ball is a 10x10 square
PADDLE_WIDTH = 10
PADDLE_HEIGHT = 100
PADDLE_SPEED = 5   # Player paddle speed (pixels per frame)
AI_SPEED = 4       # AI paddle speed (slightly slower to make it beatable)

# Colors (R, G, B)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Sound generation function (produces a Sound object with a given frequency and duration)
def generate_sound(frequency, duration_ms, volume=0.5):
    """
    Generate a simple sine wave sound at the given frequency (Hz) for the specified duration in milliseconds.
    volume is a float from 0.0 to 1.0 controlling the sound amplitude.
    Returns a pygame.mixer.Sound object that can be played.
    """
    sample_rate = 44100  # Samples per second
    n_samples = int(sample_rate * duration_ms / 1000)  # Total number of samples for desired duration
    waveform = []  # list to hold audio samples
    amplitude = 32767 * volume  # maximum amplitude for 16-bit audio, scaled by volume
    for i in range(n_samples):
        # Compute the sine wave sample value at time i
        sample_value = amplitude * math.sin(2 * math.pi * frequency * (i / sample_rate))
        waveform.append(int(sample_value))
    # Convert the list of samples to a bytes object (16-bit little-endian audio data)
    audio_data = bytes()
    for sample in waveform:
        audio_data += int.to_bytes(sample, length=2, byteorder='little', signed=True)
    # Create a Sound object from the raw audio data
    return pygame.mixer.Sound(buffer=audio_data)

# Generate sound effects (no external files, purely generated)
beep_sound = generate_sound(frequency=1000, duration_ms=100, volume=0.5)  # High-pitched short beep (e.g., paddle hit)
boop_sound = generate_sound(frequency=500, duration_ms=300, volume=0.5)   # Lower-pitched longer boop (e.g., scoring)

# Define classes for game objects
class Paddle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT
        # Create a Rect for easy position management and collision detection
        self.rect = pygame.Rect(x, y, self.width, self.height)
    
    def move(self, dy):
        """Move the paddle vertically by dy, clamping inside the screen boundaries."""
        self.y += dy
        # Keep the paddle within the screen bounds
        if self.y < 0:
            self.y = 0
        if self.y + self.height > SCREEN_HEIGHT:
            self.y = SCREEN_HEIGHT - self.height
        # Update the rectangle position for collision detection
        self.rect.y = self.y
    
    def draw(self, surface):
        """Draw the paddle as a rectangle on the given surface."""
        pygame.draw.rect(surface, WHITE, self.rect)

class Ball:
    def __init__(self, x, y, size):
        self.size = size
        # Position the ball at (x, y)
        self.x = x
        self.y = y
        # Velocity components (dx, dy)
        self.dx = 0
        self.dy = 0
        # Rect for position and collision (size x size)
        self.rect = pygame.Rect(x, y, size, size)
    
    def launch(self):
        """Start the ball moving in a random direction (called at the game start or after a score)."""
        self.x = SCREEN_WIDTH // 2 - self.size // 2  # center the ball horizontally
        self.y = SCREEN_HEIGHT // 2 - self.size // 2  # center the ball vertically
        self.rect.x = self.x
        self.rect.y = self.y
        # Set a random initial direction for the ball
        self.dx = random.choice([-4, 4])    # horizontal speed: either left or right
        self.dy = random.randint(-3, 3)     # vertical speed: small random vertical component
        if self.dy == 0:
            self.dy = 2  # avoid 0 vertical speed to prevent a perfectly horizontal trajectory
    
    def move(self):
        """Update the ball's position based on its current velocity."""
        self.x += self.dx
        self.y += self.dy
        # Update rect position for drawing and collision
        self.rect.x = self.x
        self.rect.y = self.y
    
    def bounce_vertical(self):
        """Reverse the vertical direction of the ball (bounce off top/bottom wall)."""
        self.dy = -self.dy
    
    def bounce_horizontal(self):
        """Reverse the horizontal direction of the ball (bounce off a paddle)."""
        self.dx = -self.dx
    
    def draw(self, surface):
        """Draw the ball (as a square) on the given surface."""
        pygame.draw.rect(surface, WHITE, self.rect)

# Initialize the game window and clock
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

# Create game objects: one player paddle (left), one AI paddle (right), and a ball
player_paddle = Paddle(x=20, y=(SCREEN_HEIGHT - PADDLE_HEIGHT) // 2)  # Player paddle starts centered vertically at x=20
ai_paddle = Paddle(x=SCREEN_WIDTH - 20 - PADDLE_WIDTH, y=(SCREEN_HEIGHT - PADDLE_HEIGHT) // 2)  # AI paddle (right side)
ball = Ball(x=0, y=0, size=BALL_SIZE)
ball.launch()  # Launch the ball from the center in a random direction

# Scorekeeping
player_score = 0
ai_score = 0
# Font for rendering the score (using default font)
font = pygame.font.Font(None, 36)  # 36-point font

# Main game loop
running = True
while running:
    # Cap the loop to 60 frames per second
    clock.tick(FPS)
    
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # Player paddle control (keyboard input)
    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        player_paddle.move(-PADDLE_SPEED)  # move up
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        player_paddle.move(PADDLE_SPEED)   # move down
    
    # AI paddle movement (simple AI logic)
    # The AI will move towards the ball when the ball is on the AI's side or moving towards the AI.
    if ball.dx > 0 and ball.x > SCREEN_WIDTH // 2:
        # Ball is moving right and has passed the middle, move AI paddle toward the ball's y
        if ai_paddle.rect.centery < ball.rect.centery:
            ai_paddle.move(AI_SPEED)    # move down
        elif ai_paddle.rect.centery > ball.rect.centery:
            ai_paddle.move(-AI_SPEED)   # move up
    else:
        # (Optional) When ball is not moving towards AI, you can have the AI paddle drift toward center
        if ai_paddle.rect.centery < SCREEN_HEIGHT // 2:
            ai_paddle.move(AI_SPEED)
        elif ai_paddle.rect.centery > SCREEN_HEIGHT // 2:
            ai_paddle.move(-AI_SPEED)
    
    # Move the ball
    ball.move()
    
    # Ball collision with top or bottom wall
    if ball.y <= 0:
        ball.y = 0
        ball.bounce_vertical()
        beep_sound.play()  # play bounce sound
    elif ball.y + BALL_SIZE >= SCREEN_HEIGHT:
        ball.y = SCREEN_HEIGHT - BALL_SIZE
        ball.bounce_vertical()
        beep_sound.play()  # play bounce sound
    
    # Ball collision with paddles
    if ball.rect.colliderect(player_paddle.rect):
        # Ball hit the player's paddle
        ball.x = player_paddle.x + player_paddle.width  # avoid sticking inside paddle
        # Calculate hit position to adjust ball's vertical speed (for more dynamic bounce)
        hit_position = (ball.rect.centery - player_paddle.rect.centery) / (player_paddle.height / 2)
        ball.dy += hit_position * 2  # tweak vertical velocity based on hit position
        ball.bounce_horizontal()
        beep_sound.play()  # play bounce sound
    elif ball.rect.colliderect(ai_paddle.rect):
        # Ball hit the AI's paddle
        ball.x = ai_paddle.x - ball.size
        hit_position = (ball.rect.centery - ai_paddle.rect.centery) / (ai_paddle.height / 2)
        ball.dy += hit_position * 2
        ball.bounce_horizontal()
        beep_sound.play()  # play bounce sound
    
    # Check for scoring (ball goes off left or right side)
    if ball.x < 0:
        # Ball went off the left side – AI scores
        ai_score += 1
        boop_sound.play()       # play score sound
        ball.launch()           # reset ball to center and launch toward a random direction
    elif ball.x > SCREEN_WIDTH:
        # Ball went off the right side – Player scores
        player_score += 1
        boop_sound.play()       # play score sound
        ball.launch()           # reset and relaunch ball
    
    # Drawing everything on the screen
    screen.fill(BLACK)  # Clear screen with black background
    player_paddle.draw(screen)
    ai_paddle.draw(screen)
    ball.draw(screen)
    # Draw the scores on the top of the screen
    score_text = font.render(f"{player_score}   {ai_score}", True, WHITE)
    text_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, 30))
    screen.blit(score_text, text_rect)
    # (Optional) Draw a center dividing line for aesthetics
    # for y in range(0, SCREEN_HEIGHT, 40):
    #     pygame.draw.rect(screen, WHITE, (SCREEN_WIDTH//2 - 2, y, 4, 20))
    
    # Update the display with all drawn content
    pygame.display.flip()

# Quit Pygame gracefully
pygame.quit()
