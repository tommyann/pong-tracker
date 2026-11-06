import time
from pynput.keyboard import Controller, Key

keyboard = Controller()

print("Script started", flush=True)

for seconds in range(5, 0, -1):
    print(f"Click Pong — starting in {seconds}", flush=True)
    time.sleep(1)

try:
    print("Pressing DOWN", flush=True)
    keyboard.press(Key.down)
    time.sleep(1)
finally:
    keyboard.release(Key.down)
    print("Released DOWN", flush=True)