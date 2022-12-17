#!/bin/bash
set -euo pipefail
echo "PINS CHANGED FROM ORIGINAL, CHECK PINS FIRST, then comment me out" && exit 1
avr-gcc -mmcu=atmega328p -Wall -Werror -Wextra -Os -o proxy.c.elf proxy.c && avr-objcopy -j .text -j .data -O ihex proxy.c.elf proxy.c.hex
