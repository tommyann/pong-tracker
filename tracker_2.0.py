#this tracker tries to predict the position of the ball

import mss
import numpy as np
import cv2
import time

from pynput.keyboard import Controller, Key, Listener
from threading import Event

ball_radius = 10 #da aggiornare in modo che sia automatico
################
# FUNCTIONS
################

def detect_objects(game_image, mask):
    #detects paddle and ball, returns contours and their bounding boxes

    # Find contours of the white pixels
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    
    #in this loop, we want to tell the ball from the paddle
    result=game_image.copy()
    
    ball_center = None
    paddle_center = None 
    for contour in contours:
        object_x, object_y, object_width, object_height = cv2.boundingRect(contour)
        ratio=object_width / object_height #ball is round, paddle is tall and thin (small ratio)
        # print(
        # f"Position: ({object_x}, {object_y}), "
        # f"size: {object_width} × {object_height}"
        # )

        if 0.8 <= ratio <= 1.2: #ball is roudn
            label = "Ball"
            color = (0, 0, 255)  # Red
            ball_center = (object_x + object_width // 2, object_y + object_height // 2)

        elif ratio < 0.7: #paddle is tall and thin
            label = "Paddle"
            color = (255, 0, 0)  # Blue
            paddle_center = (object_x + object_width //2, object_y + object_height //2)
        
        else:
            continue

        #draw them for visualization
        cv2.rectangle(result, (object_x, object_y), (object_x + object_width, object_y + object_height), (0, 255, 0), 2)
        cv2.putText(result, label, (object_x, object_y - 10), cv2.FONT_HERSHEY_COMPLEX, 0.5, color, 1)
    return(ball_center, paddle_center, result)

def choose_target_y(ball_center, paddle_center, ball_center_old, paddle_center_old):
    x,y=ball_center
    x_old,y_old=ball_center_old
    paddle_x, paddle_y = paddle_center

    dx= x-x_old
    dy = y-y_old

    #predict where the ball will be when it reaches the paddle's x position
    m=dy/dx
    #y_intercept=y+m*(x_paddle-x) --> 
    target_y = y + m*(paddle_x-x)
    target_y= target_y % (2*game_height)
    target_y=min(target_y, 2*game_height-target_y)
    print(
    f"dx={dx:4}, dy={dy:4}, "
    f"m={m:7.3f}, target={target_y:7.1f}"
    )
    return target_y

def choose_action(ball_center, paddle_center, ball_center_old, paddle_center_old):
    if ball_center is None or paddle_center is None or ball_center_old is None or paddle_center_old is None:
        return "stop"
    if ball_center[0]>=ball_center_old[0]:
        return "stop"
    paddle_y=paddle_center[1]
    target_y=choose_target_y(ball_center, paddle_center, ball_center_old, paddle_center_old)
    error = target_y - paddle_y
    tolerance=10

    if error > tolerance:
        return "down"
    elif error < -tolerance:
        return "up"
    else:
        return "stop"


def apply_action(keyboard, action):
    if action == "up":
        keyboard.press(Key.up)
        keyboard.release(Key.down)
    elif action == "down":
        keyboard.press(Key.down)
        keyboard.release(Key.up)
    else:
        keyboard.release(Key.up)
        keyboard.release(Key.down)

def on_press(key):
    if key == Key.esc:
        stop_requested.set()
        return False  # Stop the listener
listener = Listener(on_press=on_press)
listener.start()

#############
# MAIN
#############


with mss.mss() as camera:
    screen = camera.monitors[1]
    screenshot = camera.grab(screen)

    image = np.array(screenshot)

    print("Image dimensions: ", image.shape)
    
    # Convert the image from BGRA to BGR format
    image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    # select game area ROI=Region of Interest
    roi_x,roi_y,roi_width,game_height = cv2.selectROI("Select Game Area", image, fromCenter=False, showCrosshair=True)

    cv2.destroyAllWindows()

    if roi_width == 0 or game_height == 0:
        print("No area selected.")
        raise SystemExit("No game area selected. Exiting the program.")


    ############
    # PREPARE FOR TRACKING
    #############
    game_area = (roi_x, roi_y, roi_width, game_height)
    print("Selected game area: ", game_area)
    game_image = image[roi_y:roi_y+game_height, roi_x:roi_x+roi_width]

    mask = cv2.inRange(
        game_image,
        (220, 220, 220),
        (255, 255, 255),
    )

    cv2.imshow("White pixels", mask)
    print("press enter on the screenshot console if paddle and ball are only figures detected")
    cv2.waitKey(0)        
    cv2.destroyAllWindows()
    #detects paddle and ball for first time, returns their centers and a visualization of the detection
    ball_center_old, paddle_center_old, result = detect_objects(game_image, mask)
    if ball_center_old is None or paddle_center_old is None:
        print("Ball or paddle not detected. Please ensure they are the only white objects in the game area.")
        cv2.imshow("Detection Result", result)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        raise SystemExit("Ball or paddle not detected. Exiting the program.")
    ##########
    # Initiating keyboard
    ##########
    keyboard = Controller()
    stop_requested = Event()



    #enter loop, since paddle and ball have been detected succesfully
    region= {
        "left": screen["left"]+roi_x,
        "top": screen["top"]+roi_y,
        "width": roi_width,
        "height": game_height,
    }

    
    print("entering loop, press 'q' to exit")

    try:
        print("Press ESC to stop the program.", flush=True)
        time.sleep(5)
        print("starting tracking and bot. Click Pong window to give it focus.", flush=True)
        while not stop_requested.is_set():
            #1. capture screen in the ROI
            screenshot = camera.grab(region)
            game_image = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)

            #2. Rebuild mask from new frame
            mask = cv2.inRange(
                game_image,
                (220, 220, 220),
                (255, 255, 255),
            )

            #3. Detect objects in the new frame
            ball_center, paddle_center, result = detect_objects(game_image, mask)
            # if ball_center is None or paddle_center is None:
            #     print("Ball or paddle not detected. Please ensure they are the only white objects in the game area.")
            #     cv2.imshow("Detection Result", result)
            #     cv2.waitKey(0)
            #     cv2.destroyAllWindows()
            #     raise SystemExit("Ball or paddle not detected. Exiting the program.")
            if cv2.waitKey(20) & 0xFF == ord("q"):
                break
            # print(f"Ball center: {ball_center}, Paddle center: {paddle_center}")


            #4. Pick action
            action = choose_action(ball_center, paddle_center, ball_center_old, paddle_center_old)
            #4.5 live tracker with action
            cv2.putText(
                result,
                f"Action: {action}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )


            if (
                ball_center is not None
                and paddle_center is not None
                and ball_center_old is not None
                and ball_center[0] < ball_center_old[0]
            ):
                target_y = choose_target_y(
                    ball_center, paddle_center, ball_center_old, paddle_center_old
                )

                if target_y is not None:
                    target = (int(paddle_center[0]), int(target_y))
                    cv2.circle(result, target, 8, (0, 255, 255), 2)


            cv2.imshow("Live tracker", result)
            if cv2.waitKey(500) & 0xFF == ord("q"):
                break


            #5. Apply action
            apply_action(keyboard, action)

            #6. Update old positions
            ball_center_old = ball_center
            paddle_center_old = paddle_center
    finally:    
        listener.stop()
        cv2.destroyAllWindows()