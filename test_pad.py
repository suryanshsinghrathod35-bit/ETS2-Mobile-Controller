import time
import math
import vgamepad as vg

pad = vg.VX360Gamepad()
print("Virtual controller created. Open joy.cpl now. Running for 30 seconds...")

start = time.time()
while time.time() - start < 30:
    t = time.time() - start
    pad.left_joystick_float(x_value_float=math.sin(t * 2), y_value_float=0)
    pad.right_trigger_float((math.sin(t * 2) + 1) / 2)
    pad.update()
    time.sleep(0.02)

pad.reset()
pad.update()
print("Done")