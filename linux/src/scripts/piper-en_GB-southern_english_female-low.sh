#!/bin/bash
cat "$1" | \
  piper --model en_GB-southern_english_female-low.onnx --output-raw | \
  aplay -r 22050 -f S16_LE -t raw -