#! /bin/bash

sudo xboxdrv --evdev /dev/input/event16 --evdev-absmap ABS_X=x1,ABS_Y=y1,ABS_Z=x2,ABS_RZ=y2,ABS_HAT0X=dpad_x,ABS_HAT0Y=dpad_y --axismap -Y1=Y1,-Y2=Y2 --evdev-keymap BTN_SOUTH=a,BTN_EAST=b,BTN_NORTH=x,BTN_WEST=y,BTN_TL=lb,BTN_TR=rb,BTN_TL2=lt,BTN_TR2=rt,BTN_THUMBL=tl,BTN_THUMBR=tr,BTN_SELECT=back,BTN_START=start --silent
