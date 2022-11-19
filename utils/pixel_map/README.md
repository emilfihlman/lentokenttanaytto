# pixel map and development tool

Utility for turning on and off rectangular "pixels" on the panel. Demos included.

## Usage

1. Wire up appropriate signals to the LCD(s)
2. Upload the sketch to an Arduino Uno
3. ./pixel\_map.py /dev/ttyACM0 ../../rom/lentokenttanaytto\_zel09101.bin 2 # adjust the last number for the panel count

## Bugs

Note that the proxy is panel count agnostic and latches data every 480 bits.
This may cause some glitching with fast frame rate as the panel data chain displays once for each panel in series.
This could be mitigated by teaching the proxy about the exact number of panels, but for now it's kept simple.
