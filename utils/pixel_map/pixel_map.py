#!/usr/bin/env python3

from time import sleep
from serial import Serial
from sys import argv

# values per one four-digit panel
DIGITS = 4
BITS = 480

# The screen data is in the bitstream memory roughly like so:
# The data is clocked in a wire near the bottom right corner and it circles around the panel.
# +---+---+---+---+
# | 3 | 2 | 1 | 0 |
# | 3 | 2 | 1 | 0 |
# | 4 | 5 | 6 | 7 |
# +---+---+---+---+
# Region 0 is the first sent bits, region 7 is the last.
# "roughly" because some bits are mixed; a5, b0, d1 and e0 are fed in the bottom data but they are
# displayed as segments in the top row.
# See segments.svg for the per-digit arrangement; it also "circles around" the screen.

UPPER_DIGIT_BITS = 80 # 7 rows including the umlaut region
LOWER_DIGIT_BITS = 40 # 4 rows

# size of the consistent(ish) region; the second-last row has physical gaps though.
W = 5
H = 10
# note: rect pixel subsegments not in any particular order.
# note: that hideous top row is encoded here but not included in H to make demo effects easier.
(a, b, c, d, e, f, g, h, i, j, k, l, m, n, o) = range(15)
# a "label" is one of those alphas above
BITS_PER_LABEL = 8
# which columns to light up for each rectangular spot; note that this is in inverted order
pixel_map = [
        # 0, but very much unlike the others, so not included in the rects
        [(j, 0)],
        [(j, 5)],
        [(j, 6)],
        [(j, 7)],
        [(k, 6)],

        # 1
        [(i, 5), (i, 4)],
        [(j, 1)],
        [(k, 2), (k, 0), (j, 4)],
        [(k, 5)],
        [(l, 2), (l, 1)],

        # 2
        [(i, 1), (i, 0)],
        [(i, 7), (i, 2)],
        [(k, 1), (j, 3)],
        [(l, 4), (k, 7)],
        [(l, 7), (l, 5)],

        # 3
        [(h, 6), (h, 4), (h, 5)],
        [(i, 3), (h, 7)],
        [(l, 0), (k, 3), (j, 2)],
        [(l, 6)],
        [(m, 2), (m, 3), (m, 0)],

        # 4
        [(g, 7), (h, 1), (h, 0)],
        [(h, 3), (h, 2)],
        [(l, 3), (k, 4), (i, 6)],
        [(m, 5), (m, 1)],
        [(m, 6), (m, 7), (n, 0)],

        # 5
        [(g, 2), (g, 1), (g, 3), (g, 4), (g, 5)],
        [(g, 0), (g, 6)],
        [(n, 6), (m, 4), (d, 1)],
        [(n, 2), (n, 1)],
        [(n, 3), (n, 4), (n, 5)],

        # 6
        [(f, 4), (f, 6), (f, 5)],
        [(f, 7), (f, 3)],
        [(a, 5), (b, 0), (e, 0)],
        [(o, 3), (n, 7)],
        [(o, 2), (o, 0), (o, 1)],

        # 7
        [(e, 4), (e, 5), (e, 6)],
        [(d, 7), (e, 3)],
        [(b, 7), (c, 1), (d, 0)],
        [(a, 4), (b, 1)],
        [(a, 2), (a, 3), (a, 1)],

        # 8
        [(e, 2), (e, 1)],
        [(d, 4), (d, 5)],
        [(c, 2), (c, 6)],
        [(b, 3), (b, 4)],
        [(a, 7), (a, 6)],

        # 9
        [(d, 6)],
        [],
        [(c, 5)],
        [],
        [(b, 2)],

        # 10
        [(d, 2), (d, 3)],
        [(c, 7)],
        [(c, 3), (c, 4)],
        [(c, 0)],
        [(b, 5), (b, 6)],
]

ser = Serial(argv[1], 115200, exclusive=True, timeout=0)
sleep(2)

def empty():
    return [0] * BITS

def render_segment(screen, digit, segment, color=1):
    # the segments were originally specified inverted so invert it back
    pix_offset = 120 - 1 - (BITS_PER_LABEL * segment[0] + segment[1])

    if pix_offset < UPPER_DIGIT_BITS:
        # "upper row" but note that some segs are mixed
        # digits go right to left; rightmost digit is clocked in first
        digit_offset = (DIGITS - 1 - digit) * UPPER_DIGIT_BITS
    else:
        # make pix offset relative to the start of this digit offset
        pix_offset -= UPPER_DIGIT_BITS
        # "lower row" but note that some segs are mixed
        # digits go left to right; leftmost digit is clocked in first
        digit_offset = DIGITS * UPPER_DIGIT_BITS + digit * LOWER_DIGIT_BITS

    screen[digit_offset + pix_offset] = color

def putpixel(screen, digit, x, y, color=1):
    skip_highrow_y = 1 + y
    for segment in pixel_map[skip_highrow_y * W + x]:
        render_segment(screen, digit, segment, color)

def putsegments(screen, digit, segments):
    for segment in segments:
        render_segment(screen, digit, segment)

def fill(screen):
    for digit in range(DIGITS):
        for pixel in pixel_map:
            for seg in pixel:
                render_segment(screen, digit, seg, 1)

def display(screen):
    print(screen)
    n = ser.write(bytes(screen))
    #print(n)
    ser.flush()
    ser.read(99999)

def unit_test():
    screen = empty()
    # segments a1, a2, a3
    putpixel(screen, 3, 4, 6)
    print(screen)
    # segments a4, a3, a2, a1, a0
    assert screen[-5:] == [0, 1, 1, 1, 0]

unit_test()

def onepixel():
    screen = empty()
    putpixel(screen, 0, 0, 0)
    display(screen)
    sleep(0.5)

def fillx(screen, d, y, color=1):
    for x in range(W):
        putpixel(screen, d, x, y, color)

def filly(screen, d, x, color=1):
    for y in range(H):
        putpixel(screen, d, x, y, color)

def rolldemo():
    spf = 0.02
    # each digit up to down
    for d in range(DIGITS):
        for y in range(H):
            screen = empty();
            fillx(screen, d, y)
            display(screen)
            sleep(spf/2)
    # each digit left to right
    for d in range(DIGITS):
        for x in range(W):
            screen = empty();
            filly(screen, d, x)
            display(screen)
            sleep(spf)

def flowdemo():
    spf = 0.05
    screen = empty();
    # draw and clear top to bottom
    for color in [1, 0]:
        for y in range(H):
            for d in range(DIGITS):
                fillx(screen, d, y, color)
            display(screen)
            sleep(spf)

    screen = empty();
    # draw and clear left to right
    for color in [1, 0]:
        for d in range(DIGITS):
            for x in range(W):
                filly(screen, d, x, color)
                display(screen)
                sleep(spf)

def pixelchasedemo():
    spf = 0.001
    screen = empty();
    # top to bottom
    for y in range(H):
        # left to right, then right to left
        dir = 1 - ((y & 1) * 2)
        for d in (range(DIGITS)[::dir]):
            for x in range(W)[::dir]:
                putpixel(screen, d, x, y)
                display(screen)
                sleep(spf)

def blinkydemo():
    spf = 0.10
    for i in range(20):
        screen = empty()
        if i & 1:
            fill(screen)
        display(screen)
        sleep(spf)

def render_p():
    screen = empty()
    putsegments(screen, 0, [
        (e, 2), (e, 1),
        (e, 4), (e, 5), (e, 6),
        (f, 4), (f, 5), (f, 6),
        (g, 2), (g, 4), (g, 5), (g, 1), (g, 3),
        (m, 6), (m, 7),   (m, 5), (m, 1),   (l, 3), (k, 4), (i, 6),   (h, 2), (h, 3),   (g, 7), (h, 1), (h, 0),
        (m, 3), (m, 2), (m, 0),   (h, 6), (h, 4), (h, 5),
        (l, 7), (l, 5),   (i, 1), (i, 0),
        (l, 1),   (k, 5),   (k, 2), (k, 0), (j, 4),   (j, 1),   (i, 5), (i, 4)
    ])
    display(screen)
    print("80", screen[:80])
    print("40", screen[-40:])
    print("rest", screen[80:-40])
    sleep(99999)

def replace(screen, off, pat):
    for (i, p) in enumerate(pat):
        screen[off + i] = p

def render_glyph(screen, font, digit, char_off):
    stride = UPPER_DIGIT_BITS + LOWER_DIGIT_BITS
    digit_rtl = DIGITS - 1 - digit
    # rightmost digit goes first for top row
    upper_off = digit_rtl * UPPER_DIGIT_BITS
    # leftmost digit goes first for bottom row
    lower_off = DIGITS * UPPER_DIGIT_BITS + digit * LOWER_DIGIT_BITS
    replace(screen, upper_off, font[char_off * stride:][:UPPER_DIGIT_BITS])
    replace(screen, lower_off, font[char_off * stride + UPPER_DIGIT_BITS:][:LOWER_DIGIT_BITS])

def expand_bits_msb(bytestring):
    for b in bytestring:
        for i in range(8):
            bitval = (0x80 >> i) & b
            yield 1 if bitval != 0 else 0

def load_font(filename):
    bytestring = open(filename, 'rb').read()
    font_base_addr = 0x400 # 1KB
    glyphs = 256
    glyphsize = UPPER_DIGIT_BITS + LOWER_DIGIT_BITS
    font_bytes = bytestring[font_base_addr:font_base_addr + glyphs * glyphsize]
    return list(expand_bits_msb(font_bytes))

def render_text(screen, font, text):
    for (digit, ch) in enumerate(text):
        # this happens to be in ascii order! Plus åäö work out of the box.
        render_glyph(screen, font, digit, ord(ch))

def explore_font():
    screen = empty()
    font = load_font(argv[2])

    render_text(screen, font, 'Code')
    display(screen)
    sleep(1)

    for glyph in range(-3, 256 - DIGITS + 1):
        screen = empty()
        for digit in range(DIGITS):
            if glyph + digit >= 0:
                render_glyph(screen, font, digit, glyph + digit)
        display(screen)
        if glyph < 20:
            sleep(0.2)
        if glyph < 40:
            sleep(0.1)
        elif glyph < 200:
            sleep(0.0)
        elif glyph < 220:
            sleep(0.1)
        else:
            sleep(0.2)

    sleep(2)

if __name__ == "__main__":
    explore_font()
    while True:
        pixelchasedemo()
        rolldemo()
        flowdemo()
        blinkydemo()
