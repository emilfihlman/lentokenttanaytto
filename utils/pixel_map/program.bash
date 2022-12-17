#!/bin/bash
#usage is ./program.bash port
set -euo pipefail
avrdude -p atmega328p -c arduino -P "${1:-/dev/ttyUSB0}" -b 115200 -e -U flash:w:proxy.c.hex
