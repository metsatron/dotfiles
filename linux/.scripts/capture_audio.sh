#!/bin/bash

# Ensure PulseAudio is running
if ! pulseaudio --check; then
    pulseaudio --start
fi

# Load the necessary modules
virtual_output_sink=$(pactl load-module module-null-sink sink_name=virtual_output sink_properties=device.description="Virtual Output")
virtual_output_monitor=$(pactl load-module module-remap-source source_name=virtual_output_monitor master=virtual_output.monitor)

# Set the virtual sink as the default sink
pactl set-default-sink virtual_output

# Move existing sink inputs to the virtual sink
for i in $(pactl list sink-inputs | grep -oP 'Sink Input #\K\d+'); do
    pactl move-sink-input $i virtual_output
done

# Start capturing audio
parec -d virtual_output_monitor --format=s16le --rate=44100 --channels=2 --latency=100 > audio.raw &
parec_pid=$!

# Wait for a short time to ensure parec is running
sleep 2

# Start converting the raw audio to MP3
ffmpeg -f s16le -ar 44100 -ac 2 -i audio.raw output.mp3

# Kill the parec process after conversion
kill $parec_pid

# Unload the modules
pactl unload-module $virtual_output_sink
pactl unload-module $virtual_output_monitor
