#!/bin/bash
#usage is ./program.bash port
set -euo pipefail
echo "PINS CHANGED FROM ORIGINAL, CHECK PINS FIRST, then comment me out" && exit 1
avrdude -p atmega328p -c arduino -P "${1:-/dev/ttyUSB0}" -b 115200 -e -U flash:w:proxy.c.hex
