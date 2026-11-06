import pygame

pygame.init()

# Window
WIDTH = 800
HEIGHT = 500

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pong")
clock = pygame.time.Clock()

# Paddle: x, y, width, height
paddle_height = 100
paddle_width = 15
paddle_x = 30
paddle_y = (HEIGHT - paddle_height) // 2
paddle_speed = 500 #pixel per second

paddle=pygame.Rect(paddle_x, paddle_y, paddle_width, paddle_height)

# ball
ball_start_position=(300, 250)
ball_initial_vel=(20, 10) #pixels per second
ball_pos = pygame.Vector2(ball_start_position)
ball_radius = 10
ball_vel = pygame.Vector2(ball_initial_vel) #hor, ver, pixels per second

# font
font = pygame.font.Font(None, 36)

running = True
counter = 0
while running:
    # elapsed time since last frame
    dt = clock.tick(60) / 1000 # seconds

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()

    #moving paddle 
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        paddle.y -= round(paddle_speed * dt) #pixels starts from the top left corner!!

    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        paddle.y += round(paddle_speed * dt)

    if keys[pygame.K_ESCAPE]:
        running = False

    #prevents paddle from going out of the window
    paddle.clamp_ip(screen.get_rect())

    #ball movement
    ball_pos += ball_vel * dt

    # bounce ball off top and bottom of window
    if ball_pos.y - ball_radius < 0 or ball_pos.y + ball_radius > HEIGHT:
        ball_vel.y *= -1
        ball_vel.x += ball_vel.x*0.01
        ball_vel.y += ball_vel.y*0.01
    if ball_pos.x + ball_radius > WIDTH:
        ball_vel.x *= -1
        ball_vel.x += ball_vel.x*0.01
        ball_vel.y += ball_vel.y*0.01

    # collision with paddle
    if ball_vel.x < 0 and paddle.collidepoint(ball_pos.x - ball_radius, ball_pos.y):
        ball_vel.x *= -1
        counter += 1
        ball_vel.x += ball_vel.x*0.01
        ball_vel.y += ball_vel.y*0.01
    #miss the ball
    if ball_pos.x < paddle.x:
        ball_pos = pygame.Vector2(ball_start_position)
        ball_vel = pygame.Vector2(ball_initial_vel)
        paddle.y=paddle_y
        paddle.x=paddle_x
        counter = 0

    #draw frame
    screen.fill((20,20,30))
    pygame.draw.circle(screen, (240, 240, 240), ball_pos, ball_radius)
    pygame.draw.rect(screen, (240, 240, 240), paddle)
    
    #score
    score_text = font.render((f"Score: {counter}"), True, (50, 240, 240))
    screen.blit(score_text, (10, 10))
    
    pygame.display.flip()


pygame.quit()
