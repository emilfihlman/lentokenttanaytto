#!/usr/bin/env python3

from time import sleep, time
from serial import Serial
from sys import argv

# below values per one four-digit panel
DIGITS = 4

# The screen data is in the bitstream memory roughly like so:
# The data is clocked in a wire near the bottom right corner and it circles around the panel.
# +---+---+---+---+
# | 3 | 2 | 1 | 0 |
# | 4 | 5 | 6 | 7 |
# +---+---+---+---+
# Region 0 is the first sent bits, region 7 is the last.
# "roughly" because some bits are mixed; a5, b0, d1 and e0 are fed in the bottom data but they are
# displayed as segments in the top row.
# See segments.svg for the per-digit arrangement; it too "circles around" the screen.
#
# With multiple chained panels, the first bits reach the last one in the chain, which is the
# rightmost one if data is input to the leftmost one.

UPPER_DIGIT_BITS = 80 # 7 rows including the umlaut region
LOWER_DIGIT_BITS = 40 # 4 rows
TOTAL_DIGIT_BITS = UPPER_DIGIT_BITS + LOWER_DIGIT_BITS # 120
BITS = DIGITS * TOTAL_DIGIT_BITS # 480

# size of the consistent(ish) region; the second-last row has physical gaps though.
W = 5
H = 10
# note: rect pixel subsegments not in any particular order.
# XXX in some particular order, left to right ish or in some render program order to match pixel_gfx
# note: that hideous top row is encoded here but not included in H to make demo effects easier.
(a, b, c, d, e, f, g, h, i, j, k, l, m, n, o) = range(15)
# a "label" is one of those alphas above
BITS_PER_LABEL = 8
# which columns to light up for each rectangular spot; note that this is in inverted order
PIXEL_MAP = [
        # 0, but very much unlike the others, so not included in the rects
        [(j, 0)],
        [(j, 5)],
        [(j, 6)],
        [(j, 7)],
        [(k, 6)],

        # 1
        [(i, 4), (i, 5)],
        [(j, 1)],
        [(j, 4), (k, 0), (k, 2)],
        [(k, 5)],
        [(l, 1), (l, 2)],

        # 2
        [(i, 0), (i, 1)],
        [(i, 2), (i, 7)],
        [(j, 3), (k, 1)],
        [(k, 7), (l, 4)],
        [(l, 5), (l, 7)],

        # 3
        [(h, 5), (h, 4), (h, 6)],
        [(h, 7), (i, 3)],
        [(j, 2), (k, 3), (l, 0)],
        [(l, 6)],
        [(m, 0), (m, 3), (m, 2)],

        # 4
        [(h, 0), (h, 1), (g, 7)],
        [(h, 2), (h, 3)],
        [(i, 6), (k, 4), (l, 3)],
        [(m, 1), (m, 5)],
        [(m, 7), (m, 6), (n, 0)],

        # 5
        [(g, 5), (g, 4), (g, 3), (g, 2), (g, 1)],
        [(g, 6), (g, 0)],
        [(d, 1), (m, 4), (n, 6)],
        [(n, 1), (n, 2)],
        [(n, 4), (n, 3), (n, 5)],

        # 6
        [(f, 5), (f, 6), (f, 4)],
        [(f, 3), (f, 7)],
        [(e, 0), (b, 0), (a, 5)],
        [(n, 7), (o, 3)],
        [(o, 1), (o, 0), (o, 2)],

        # 7
        [(e, 6), (e, 5), (e, 4)],
        [(e, 3), (d, 7)],
        [(d, 0), (c, 1), (b, 7)],
        [(b, 1), (a, 4)],
        [(a, 1), (a, 3), (a, 2)],

        # 8
        [(e, 1), (e, 2)],
        [(d, 5), (d, 4)],
        [(c, 6), (c, 2)],
        [(b, 4), (b, 3)],
        [(a, 6), (a, 7)],

        # 9
        [(d, 6)],
        [],
        [(c, 5)],
        [],
        [(b, 2)],

        # 10
        [(d, 3), (d, 2)],
        [(c, 7)],
        [(c, 4), (c, 3)],
        [(c, 0)],
        [(b, 6), (b, 5)],
]

def render_segment(screen, digit, digit_segment, color=1):
    npanels = len(screen) // BITS
    panel_offset = (npanels - 1 - (digit // 4)) * BITS
    digit %= 4

    if digit_segment < UPPER_DIGIT_BITS:
        # "upper row" but note that some segs are mixed
        # digits go right to left; rightmost digit is clocked in first
        digit_offset = (DIGITS - 1 - digit) * UPPER_DIGIT_BITS
    else:
        # make pix offset relative to the start of this digit offset
        digit_segment -= UPPER_DIGIT_BITS
        # "lower row" but note that some segs are mixed
        # digits go left to right; leftmost digit is clocked in first
        digit_offset = DIGITS * UPPER_DIGIT_BITS + digit * LOWER_DIGIT_BITS

    screen[panel_offset + digit_offset + digit_segment] = color

def render_pixel_segment(screen, digit, segment_spec, color=1):
    offset_in_digit = BITS_PER_LABEL * segment_spec[0] + segment_spec[1]
    # the segments were originally specified inverted so invert it back
    segment = TOTAL_DIGIT_BITS - 1 - offset_in_digit
    render_segment(screen, digit, segment, color)

# "big endian"
def squeeze_bits_be(bytebits):
    return sum([b << (7 - i) for (i, b) in enumerate(bytebits)])

def bitstring_to_bytestring_be(bitstring):
    assert (len(bitstring) & 7) == 0
    nbytes = len(bitstring) // 8
    for off in range(nbytes):
        yield squeeze_bits_be(bitstring[8 * off:8 * off + 8])

def expand_bits_be(bytestring):
    for b in bytestring:
        for i in range(8):
            bitval = (0x80 >> i) & b
            yield 1 if bitval != 0 else 0

def unit_test_bitstuff():
    assert squeeze_bits_be([0, 0, 0, 0, 0, 0, 0, 1]) == 1
    assert squeeze_bits_be([1, 0, 0, 0, 0, 0, 0, 0]) == 0x80
    assert squeeze_bits_be([0, 0, 0, 0, 1, 1, 1, 1]) == 0xf
    assert list(bitstring_to_bytestring_be([
        0, 0, 0, 0, 0, 0, 0, 1,
        1, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 1, 1, 1, 1,
        ])) == [1, 0x80, 0xf]

unit_test_bitstuff()

class Display:
    def __init__(self, port, panels=1):
        self.port = port
        self.panels = panels

    def num_digits(self):
        return self.panels * DIGITS

    def new_window(self):
        return Window(self.panels)

    def blit(self, window):
        compress = True
        if compress:
            bs = list(bitstring_to_bytestring_be(window.pixels))
            assert window.pixels == list(expand_bits_be(bs))
            nsent = self.port.write(bytes(bs))
            assert nsent == len(window.pixels) // 8
        else:
            nsent = self.port.write(bytes(window.pixels))
            assert nsent == len(window.pixels)
        self.port.flush()

        tot = 0
        while tot < nsent:
            r = self.port.read(9999999)
            tot += len(r)
            sleep(0.0001)

class Window:
    def __init__(self, panels=1):
        self.panels = panels
        self.pixels = [0] * (panels * BITS)

    def num_digits(self):
        return self.panels * DIGITS

    def putpixel(self, digit, x, y, color=1):
        skip_highrow_y = 1 + y
        for segment in PIXEL_MAP[skip_highrow_y * W + x]:
            render_pixel_segment(self.pixels, digit, segment, color)

    def fillx(self, d, y, color=1):
        for x in range(W):
            self.putpixel(d, x, y, color)

    def filly(self, d, x, color=1):
        for y in range(H):
            self.putpixel(d, x, y, color)

    def fill(self):
        for digit in range(self.num_digits()):
            for pixel in PIXEL_MAP:
                for seg in pixel:
                    render_pixel_segment(self.pixels, digit, seg, 1)

    def insert_raw(self, offset, segments):
        for (i, segbit) in enumerate(segments):
            self.pixels[offset + i] = segbit

def unit_test_render():
    window = Window()
    # rightmost digit, segments a1, a2, a3
    window.putpixel(3, 4, 6)
    # segments a4, a3, a2, a1, a0
    assert window.pixels[-5:] == [0, 1, 1, 1, 0]

unit_test_render()

class Font:
    def __init__(self, fw_filename):
        self.glyphdata = Font.load_font(fw_filename)

    def load_font(fw_filename):
        bytestring = open(fw_filename, 'rb').read()
        font_base_addr = 0x400 # 1KB
        glyphs = 256
        font_bytes = bytestring[font_base_addr:][:glyphs * TOTAL_DIGIT_BITS]
        return list(expand_bits_be(font_bytes))

    def get_glyph_data(self, glyph):
        return self.glyphdata[glyph * TOTAL_DIGIT_BITS:][:TOTAL_DIGIT_BITS]

    def render_glyph(self, window, digit, glyph):
        panel_off = (window.panels - 1 - (digit // DIGITS)) * BITS
        panel_digit = digit % DIGITS
        panel_digit_rtl = DIGITS - 1 - panel_digit
        # rightmost digit goes first for top row
        upper_off = panel_digit_rtl * UPPER_DIGIT_BITS
        # leftmost digit goes first for bottom row
        lower_off = DIGITS * UPPER_DIGIT_BITS + panel_digit * LOWER_DIGIT_BITS
        data = self.get_glyph_data(glyph)
        window.insert_raw(panel_off + upper_off, data[:UPPER_DIGIT_BITS])
        window.insert_raw(panel_off + lower_off, data[UPPER_DIGIT_BITS:])

    def render(self, window, text):
        for (digit, ch) in enumerate(text):
            # this happens to be in ascii order! Plus åäö work out of the box.
            self.render_glyph(window, digit, ord(ch))

def rolldemo(display):
    spf = 0.04
    # each digit up to down
    for d in range(display.num_digits()):
        for y in range(H):
            window = display.new_window()
            window.fillx(d, y)
            display.blit(window)
            sleep(spf/2)
    # each digit left to right
    for d in range(display.num_digits()):
        for x in range(W):
            window = display.new_window()
            window.filly(d, x)
            display.blit(window)
            sleep(spf)

def flowdemo(display):
    spf = 0.05
    window = display.new_window()
    # draw and clear top to bottom
    for color in [1, 0]:
        for y in range(H):
            for d in range(window.num_digits()):
                window.fillx(d, y, color)
            display.blit(window)
            sleep(spf)

    window = display.new_window()
    # draw and clear left to right
    for color in [1, 0]:
        for d in range(window.num_digits()):
            for x in range(W):
                window.filly(d, x, color)
                display.blit(window)
                sleep(spf)

def pixelchasedemo(display):
    # experiencing some flicker trouble with a higher rate when using multiple panels, likely due to
    # the proxy latching on every panel.
    spf = 0.03
    window = display.new_window()
    # top to bottom
    for y in range(H):
        # left to right, then right to left
        direction = 1 - ((y & 1) * 2)
        for d in (range(window.num_digits())[::direction]):
            for x in range(W)[::direction]:
                window.putpixel(d, x, y)
                display.blit(window)
                sleep(spf)

def blinkydemo(display):
    spf = 0.10
    for i in range(20):
        window = display.new_window()
        if (i+1) & 1:
            window.fill()
        display.blit(window)
        sleep(spf)

def explore_font(display, font):
    window = display.new_window()
    if display.panels == 1:
        font.render(window, 'Code')
    else:
        font.render(window, 'Longtext')
    display.blit(window)
    sleep(1)

    width = window.num_digits()

    a = time()

    for glyph in range(-width + 1, 256 - width + 1):
        window = display.new_window()
        for digit in range(width):
            if glyph + digit >= 0:
                font.render_glyph(window, digit, glyph + digit)
        display.blit(window)
        #sleep(0.0001)

    b = time()
    d = b - a
    bits = 256 * display.panels * DIGITS * BITS
    print("%.2f kbits in %.2f seconds = %.2f kHz" % (
        bits / 1000.0, d, bits / d / 1000.0))

    sleep(2)

def main():
    serial_filename = argv[1]
    zel09101_fw_filename = argv[2]
    num_panels = int(argv[3])

    ser = Serial(argv[1], 115200, exclusive=True, timeout=0)
    # faster uart seems to be glitchy
    #ser = Serial(argv[1], 230400, exclusive=True, timeout=0)
    sleep(2)
    r = ser.read(9999999)
    # wtf arduino
    #print("flush size", len(r))

    font = Font(zel09101_fw_filename)

    display = Display(ser, num_panels)
    explore_font(display, font)
    while True:
        pixelchasedemo(display)
        rolldemo(display)
        flowdemo(display)
        blinkydemo(display)

if __name__ == "__main__":
    main()
