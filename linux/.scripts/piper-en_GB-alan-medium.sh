#!/bin/bash
cat "$1" | \
  piper --model en_GB-alan-medium.onnx --output-raw | \
  aplay -r 22050 -f S16_LE -t raw -