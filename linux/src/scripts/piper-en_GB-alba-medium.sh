#!/bin/bash
# echo 'Stop using: pkill -SIGKILL axfer'
# echo 'Pause using: pkill -SIGTSTP axfer'
# echo 'Play using: pkill -SIGTSTP axfer'

echo 'Generating audio steam read in the voice of Alba (medium)(en_GB).'
cat "$1" | \
piper --model en_GB-alba-medium.onnx  --output-raw | \
axfer transfer playback -r 22050 -c 1 -f S16_LE -t raw -