#!/bin/bash

# Start capturing audio
parec --format=s16le --rate=44100 --channels=2 --latency=100 --server=unix:/run/user/1000/pulse/native > audio.raw &

# Get the PID of the parec process
parec_pid=$!

# Start converting the raw audio to MP3
ffmpeg -f s16le -ar 44100 -ac 2 -i audio.raw output.mp3

# Kill the parec process after conversion
kill $parec_pid
