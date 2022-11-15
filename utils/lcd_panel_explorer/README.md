# LCD Panel Explorer

Utility for exploring shift register layout of the LCD panel.

## Usage
1. Wire up appropriate signals to the LCD
2. Upload the sketch to an Arduino Uno.
3. Connect to the Arduino over serial at 115200 baud over something that doesn't send newlines or carriage returns (e.g. pyserial). The `+` and `-` keys can be used to modify which bit in the chain is set to 1. All other bits are set to 0.