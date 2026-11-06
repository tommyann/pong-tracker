#intensity of input decreases as error decreases

import mss
import numpy as np
import cv2
import time

from pynput.keyboard import Controller, Key, Listener
from threading import Event

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

def dist(p1,p2):
    return np.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def choose_action(ball_center, paddle_center):
    if ball_center is None or paddle_center is None:
        return "stop"

    ball_y = ball_center[1]
    ball_x = ball_center[0]
    paddle_y = paddle_center[1]
    
    error = ball_y - paddle_y
    tolerance = 10

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
    ball_center, paddle_center, result = detect_objects(game_image, mask)
    if ball_center is None or paddle_center is None:
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
            #time.sleep(0.05) #sleep for 50ms to avoid high CPU usage
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


            #3.5 Live tracker
            # Display every frame, including when detection fails.



            #4. Pick action
            action = choose_action(ball_center, paddle_center)
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
            cv2.imshow("Live tracker", result)
            
            if cv2.waitKey(20) & 0xFF == ord("q"):
                break


            #5. Apply action
            apply_action(keyboard, action)
    finally:    
        listener.stop()
        cv2.destroyAllWindows()