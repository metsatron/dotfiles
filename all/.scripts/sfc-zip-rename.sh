#!/bin/bash

find . -type f -name "*.sfc" -exec zip -D './{}.zip' '{}' \; 
find . -iname "*sfc.zip" -exec rename -v "s/sfc.zip/zip/;" "{}" \;
find . -iname "*.zip" -exec rename -v "s/ Fastrom/ (FastROM)/;" "{}" \;
find . -iname "*.zip" -exec rename -v "s/ fastrom/ (FastROM)/;" "{}" \;
find . -iname "*.zip" -exec rename -v "s/ FastRom/ (FastROM)/;" "{}" \;
find . -type f -name "*(U)*" -exec rename -v "s/'(U)'/USA/;" "{}" \;
echo "done"