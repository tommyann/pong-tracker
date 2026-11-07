#CHANGES: 1. detect_objects also detects ball radius
#         2. chose action continuously, only chose direction 
#           at set time intervals
dt = 0.1

import mss
import numpy as np
import cv2
import time
from pynput.keyboard import Controller, Key, Listener
from threading import Event
import sys


##########################
# FUNCTIONS
##########################

def detect_objects(game_image, mask):
    #detects paddle, ball, returns contour
    # only works if there are only 2 objects, so user has
    # to make sure there are only 2 in the image
    # also returns ball_radius


    #find contours of white pixel areas
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    #look for all white areas and tell ball from paddle
    result=game_image.copy()

    ball_center = None
    paddle_center = None
    for contour in contours:
        object_x, object_y, object_width, object_height=cv2.boundingRect(contour)
        ratio=object_width/object_height
        # print(f"Position: ({object_x}, {object_y}), "f"size: {object_width} × {object_height}")

        if 0.8<=ratio<=1.2: #ball is round
            label="Ball"
            color=(0,0,255) #red
            ball_center=(object_x+object_width//2, object_y+object_height//2)
            global ball_radius
            ball_radius = object_width//2
        elif ratio<0.7: #paddle is tall and thin
            label="Paddle"
            color = (255,0,0) #blue
            paddle_center = (object_x+object_width//2, object_y+object_height//2)
            global contact_x
            contact_x = paddle_center[0] + object_width//2
        else:
            continue

        #draw for visualization
        cv2.rectangle(result, (object_x,object_y), (object_x+object_width, object_y+object_height), (0, 255, 0), 2)
        cv2.putText(result, label, (object_x,object_y-10), cv2.FONT_HERSHEY_COMPLEX, 0.5, color, 1)
    return(ball_center, paddle_center, result)

def choose_target_y(ball_center, paddle_center, ball_center_old):
    #functions expects roi_height to be define globally
    x,y=ball_center
    x_old,y_old=ball_center_old

    dx=x-x_old
    dy=y-y_old

    #predicts where ball will intercept
    m=dy/dx
    #y_intercept=y+m*(x_paddle-x) --> 
    target_y = y + m*(contact_x-x)
    span = roi_height - 2*ball_radius
    target_y= (target_y-ball_radius) % (2*span)
    target_y = min(target_y, 2*span-target_y) + ball_radius
    print(f"dx={dx:4}, dy={dy:4}, m={m:7.3f}, target={target_y:7.1f}")
    return target_y

def choose_action(ball_center, paddle_center, ball_center_old, time_has_passed, old_target_y):
    #ball_center, paddle_center are current positions
    #ball_center_old, paddle_center_old are positions at the last interval
    #time_has_passed is true if the set time interval has passed, false otherwise
    #old target y is needed because if time_has_passed == False, there would be no target_y value

    if ball_center is None or paddle_center is None:
        return "stop", old_target_y
    if ball_center_old is None:
        return "stop", old_target_y
    if ball_center[0]>=ball_center_old[0]:
        return "stop", old_target_y #ball is moving away from paddle

    paddle_y = paddle_center[1]
    if time_has_passed:
        target_y = choose_target_y(ball_center, paddle_center, ball_center_old)
    else:
        target_y=old_target_y
    error = target_y-paddle_y
    tolerance = 10

    if error > tolerance:
        action = "down"
    elif error <-tolerance:
        action = "up"
    else:
        action = "stop"

    return action, target_y

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
    screen = camera.monitors[0]
    screenshot = camera.grab(screen)

    image = np.array(screenshot)
    print("Image dimensions: ", image.shape)

    #converts image from BGRA to BGR format
    image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    # select ROI (Region of Interest)
    
    while True:
        roi_x,roi_y,roi_width,roi_height = cv2.selectROI("Select game Area", image, fromCenter=False, showCrosshair=True)
        cv2.destroyAllWindows()
        if roi_width > 0 and roi_height > 0:
            break
        else:
            print("No game area selected. Press Enter to retry or 'q' to quit.")
            cv2.waitKey(0)  
    #################
    # PREPARE FOR TRACKING
    #################

    game_area = (roi_x,roi_y,roi_width,roi_height)
    print("Selected game are: ", game_area)
    game_image = image[roi_y:roi_y+roi_height, roi_x:roi_x+roi_width]

    mask = cv2.inRange( #CHANGE THIS IF PADDLE AND BALL ARE NOT WHITE
        game_image,
        (220,220,220),
        (255,255,255),
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

    #enter loop, since paddle and ball have been detected succesfully
    region= {
        "left": screen["left"]+roi_x,
        "top": screen["top"]+roi_y,
        "width": roi_width,
        "height": roi_height,
    }

    ##################
    # INITIATE KEYBOARD AND STOP_REQUESTED
    ##################
    keyboard = Controller()
    stop_requested = Event()

    last_tracking=time.monotonic()
    time_has_passed=True
    target_y=0 #it is never actually used
    try:
        print("Press ESC to stop the program.", flush=True)
        print("starting tracking and bot. Click Pong window to give it focus.", flush=True)
        time.sleep(5)
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
            action, target_y = choose_action(ball_center, paddle_center, ball_center_old, time_has_passed, target_y)
            if time_has_passed:
                time_has_passed=False
                ball_center_old = ball_center
                paddle_center_old = paddle_center
                last_tracking=time.monotonic()
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

            if target_y is not None and paddle_center is not None:
                target = (int(paddle_center[0]), int(target_y))
                cv2.circle(result, target, 8, (0, 255, 255), 2)


            cv2.imshow("Live tracker", result)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


            #5. Apply action
            apply_action(keyboard, action)

            #6. Update old positions only every dt seconds
            if (time.monotonic()-last_tracking) > dt:
                time_has_passed=True
    finally:    
        keyboard.release(Key.up)
        keyboard.release(Key.down)
        listener.stop()
        cv2.destroyAllWindows()