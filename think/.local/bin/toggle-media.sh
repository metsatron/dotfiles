#!/bin/bash

# Toggle Jellyfin and FluidSynth
case "$1" in
    "stop")
        sudo systemctl stop jellyfin
        pkill -9 fluidsynth
        echo "Jellyfin and FluidSynth stopped."
        ;;
    "start")
        sudo systemctl start jellyfin
        /usr/bin/fluidsynth -is /usr/share/sounds/sf3/default-GM.sf3 &
        echo "Jellyfin and FluidSynth started."
        ;;
    *)
        echo "Usage: $0 {stop|start}"
        exit 1
        ;;
esac
free -h
