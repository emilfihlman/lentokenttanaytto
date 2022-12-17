#!/bin/bash
avr-gcc -mmcu=atmega328p -Wall -Werror -Wextra -Os -o proxy.c.elf proxy.c && avr-objcopy -j .text -j .data -O ihex proxy.c.elf proxy.c.hex
