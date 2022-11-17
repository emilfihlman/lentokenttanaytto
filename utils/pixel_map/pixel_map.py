#!/usr/bin/env python3

from time import sleep
from serial import Serial
from sys import argv

W = 5
H = 10
DIGITS = 4
BITS = 480
UPPER_DIGIT_BITS = 40
LOWER_DIGIT_BITS = 80
# see segments.svg for this labeling.
# note: rect pixel subsegments not in any particular order.
# also note: that hideous bottom row is encoded here but not included in H to make demo effects easier.
(a, b, c, d, e, f, g, h, i, j, k, l, m, n, o) = range(15)
BITS_PER_LABEL = 8
pixel_map = [
        # 0
        [(b, 5), (b, 6)],
        [(c, 0)],
        [(c, 3), (c, 4)],
        [(c, 7)],
        [(d, 2), (d, 3)],

        # 1
        [(b, 2)],
        [],
        [(c, 5)],
        [],
        [(d, 6)],

        # 2
        [(a, 7), (a, 6)],
        [(b, 3), (b, 4)],
        [(c, 2), (c, 6)],
        [(d, 4), (d, 5)],
        [(e, 2), (e, 1)],

        # 3
        [(a, 2), (a, 3), (a, 1)],
        [(a, 4), (b, 1)],
        [(b, 7), (c, 1), (d, 0)],
        [(d, 7), (e, 3)],
        [(e, 4), (e, 5), (e, 6)],

        # 4
        [(o, 2), (o, 0), (o, 1)],
        [(o, 3), (n, 7)],
        [(a, 5), (b, 0), (e, 0)],
        [(f, 7), (f, 3)],
        [(f, 4), (f, 6), (f, 5)],

        # 5
        [(n, 3), (n, 4), (n, 5)],
        [(n, 2), (n, 1)],
        [(n, 6), (m, 4), (d, 1)],
        [(g, 0), (g, 6)],
        [(g, 2), (g, 1), (g, 3), (g, 4), (g, 5)],

        # 6
        [(m, 6), (m, 7), (n, 0)],
        [(m, 5), (m, 1)],
        [(l, 3), (k, 4), (i, 6)],
        [(h, 3), (h, 2)],
        [(g, 7), (h, 1), (h, 0)],

        # 7
        [(m, 2), (m, 3), (m, 0)],
        [(l, 6)],
        [(l, 0), (k, 3), (j, 2)],
        [(i, 3), (h, 7)],
        [(h, 6), (h, 4), (h, 5)],

        # 8
        [(l, 7), (l, 5)],
        [(l, 4), (k, 7)],
        [(k, 1), (j, 3)],
        [(i, 7), (i, 2)],
        [(i, 1), (i, 0)],

        # 9
        [(l, 2), (l, 1)],
        [(k, 5)],
        [(k, 2), (k, 0), (j, 4)],
        [(j, 1)],
        [(i, 5), (i, 4)],

        # 10, but very much unlike the others
        [(k, 6)],
        [(j, 7)],
        [(j, 6)],
        [(j, 5)],
        [(j, 0)],
]

ser = Serial(argv[1], 115200, exclusive=True, timeout=0)
sleep(2)

def empty():
    return [0] * BITS

def render_segment(screen, digit, segment, color=1):
    pix_offset = BITS_PER_LABEL * segment[0] + segment[1]
    if pix_offset < UPPER_DIGIT_BITS:
        # "upper row" but note that some segs are mixed
        digit_offset = UPPER_DIGIT_BITS * digit
    else:
        # "lower row" but note that some segs are mixed
        digit_offset = BITS - LOWER_DIGIT_BITS * (digit + 1) - UPPER_DIGIT_BITS
    screen[BITS - (digit_offset + pix_offset + 1)] = color

def putpixel(screen, digit, x, y, color=1):
    for segment in pixel_map[y * W + x]:
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

def test():
    screen = empty()
    putpixel(screen, 0, 0, 3)
    assert screen[-5:] == [0, 1, 1, 1, 0]

test()

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
    for d in range(DIGITS):
        for y in range(H):
            screen = empty();
            fillx(screen, d, y)
            display(screen)
            sleep(spf/2)
    for d in range(DIGITS):
        for x in range(W):
            screen = empty();
            filly(screen, d, x)
            display(screen)
            sleep(spf)

def flowdemo():
    spf = 0.05
    screen = empty();
    for y in range(H):
        for d in range(DIGITS):
            fillx(screen, d, y)
        display(screen)
        sleep(spf)
    for y in range(H):
        for d in range(DIGITS):
            fillx(screen, d, y, color=0)
        display(screen)
        sleep(spf)

    screen = empty();
    for d in range(DIGITS):
        for x in range(W):
            filly(screen, d, x)
            display(screen)
            sleep(spf)
    for d in range(DIGITS):
        for x in range(W):
            filly(screen, d, x, color=0)
            display(screen)
            sleep(spf)

def pixelchasedemo():
    spf = 0.001
    screen = empty();
    for y in range(H):
        dir = ((y & 1) * 2 - 1)
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

if __name__ == "__main__":
    render_p()
    while True:
        pixelchasedemo()
        rolldemo()
        flowdemo()
        blinkydemo()
