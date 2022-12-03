# pixel/segment processing tools

pixel map: Utility for turning on and off rectangular "pixels" on the panel and for rendering font data. Demos included.

pixel gfx: Utility for segment render emulation with pygame.

## Usage

### Pixel map

1. Wire up appropriate signals to the LCD(s)
2. Upload the sketch to an Arduino Uno
3. ./pixel\_map.py /dev/ttyACM0 ../../rom/lentokenttanaytto\_zel09101.bin 2 # adjust the last number for the panel count

### Pixel gfx

1. ./pixel\_gfx.py ../../rom/lentokenttanaytto\_zel09101.bin # for whole font data
2. ./pixel\_gfx.py ../../rom/lentokenttanaytto\_zel09101.bin Hello world # for arbitrary text
