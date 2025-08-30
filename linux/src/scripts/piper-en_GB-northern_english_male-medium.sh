#!/bin/bash
cat "$1" | \
  piper --model en_GB-northern_english_male-medium.onnx --output-raw | \
  aplay -r 22050 -f S16_LE -t raw -