#!/usr/bin/env python3
import sys
import pygame
import pygame.gfxdraw
import pixel_map
from time import sleep

# FIXME: this mess is full of off-by-ones like sz vs sz-1

hide_borders = False
render_test_glyph = False

COLOR_BACK = (127, 127, 127)
COLOR_SEG = (255, 255, 255)
COLOR_SEG_BORDER = (0, 0, 0)
if hide_borders:
    COLOR_SEG_BORDER = COLOR_SEG
COLOR_DIGIT_BORDER = (100, 0, 0)

# "full" and "half" width and height; rectangles in the normal region.
# normal region goes full half full half full, with varying splits.
fw = 110
hw = fw / 2
h = 90

# top row is special
dots_sz = 80 # height of the row, and width of dot squares
dots_x = 15 # from left of normal region to left of dots
dots_yminus = dots_sz + 75 # from top of dots to top of normal region

# thick lines in between
pad = 6

middlex = fw + pad + hw + pad + fw/2
totw = 3 * fw + 2 * hw + 4 * pad
toth = dots_yminus + 10 * h + 9 * pad

SCALE = 0.104

OFFX = 0
OFFY = dots_yminus

# again, top row is special
dots_topx = [
    dots_x, dots_x + dots_sz,
    middlex - 55, middlex - 30,
    middlex + 30, middlex + 55,
    totw-1 - dots_x, totw - dots_x - dots_sz,
]
dots_midy = 48
dots_botx = [
    dots_x, dots_x + dots_sz,
    middlex - 106, middlex - 23,
    middlex + 23, middlex + 106,
    totw-1 - dots_x, totw - dots_x - dots_sz,
]

# relative to -dots_yminus
TOP_POLYS = [
    [
        (dots_topx[0], 0),
        (dots_topx[1], 0),
        (dots_topx[1], dots_sz),
        (dots_topx[0], dots_sz),
    ],
    [
        (dots_topx[2], 0),
        (dots_topx[3], 0),
        (middlex, dots_midy),
        (dots_botx[3], dots_sz),
        (dots_botx[2], dots_sz),
    ],
    [
        (dots_topx[3], 0),
        (dots_topx[4], 0),
        (middlex, dots_midy),
    ],
    [
        (dots_topx[4], 0),
        (dots_topx[5], 0),
        (dots_botx[5], dots_sz),
        (dots_botx[4], dots_sz),
        (middlex, dots_midy),
    ],
    [
        (dots_topx[6], 0),
        (dots_topx[7], 0),
        (dots_topx[7], dots_sz),
        (dots_topx[6], dots_sz),
    ],
]


# "canonical order" consistency rules so that these work together:
# - PIXEL_MAP specifies segments from left to right, top to bottom
# - left means the segment faces the left edge of its surrounding box
# - all left things go first, like in g5..g1
# - these operations also output things left to right
# - vertices always go clockwise in a polygon
# - a polygon always starts from the top left when it matters
# - triangles are not (yet) split up so they might be inconsistent?

class full:
    def __call__(self, stack):
        poly = [(0, 0), (fw-1, 0), (fw-1, h-1), (0, h-1)]
        return stack + [poly]

class half:
    def __call__(self, stack):
        poly = [(0, 0), (hw-1, 0), (hw-1, h-1), (0, h-1)]
        return stack + [poly]

# FIXME all these arcs are approximated by just corners and midpoint,
# looks good enough from afar but poor when zoomed in
class tl_arc:
    # expects a rect in the stack
    # outputs the corner first, then the major part
    def __call__(self, stack):
        # midpoint is 1/3 from the nearest corner, roughly
        rect = stack.pop()
        midcorner = (1/3. * rect[1][0], 1/3. * rect[3][1])
        poly1 = [rect[0], rect[1], midcorner, rect[3]]
        poly2 = [midcorner, rect[1], rect[2], rect[3]]
        return stack + [poly1, poly2]

class tr_arc:
    # expects a rect in the stack
    # outputs the major part first, then the corner
    def __call__(self, stack):
        # midpoint is 1/3 from the nearest corner, roughly
        rect = stack.pop()
        midcorner = (
                rect[0][0] + 2/3. * (rect[1][0] - rect[0][0]),
                1/3. * (rect[2][1] - 0*rect[1][1]))
        poly1 = [rect[0], midcorner, rect[2], rect[3]]
        poly2 = [rect[0], rect[1], rect[2], midcorner]
        return stack + [poly1, poly2]

class bl_arc:
    # expects a rect in the stack
    # outputs the corner first, then the major part
    def __call__(self, stack):
        # midpoint is 1/3 from the nearest corner, roughly
        rect = stack.pop()
        midcorner = (
                rect[0][0] + 1/3. * (rect[2][0] - rect[0][0]),
                rect[0][1] + 2/3. * (rect[2][1] - rect[0][1])
        )
        poly1 = [rect[0], midcorner, rect[2], rect[3]]
        poly2 = [rect[0], rect[1], rect[2], midcorner]
        return stack + [poly1, poly2]

class br_arc:
    # expects a rect in the stack
    # outputs the major part first
    def __call__(self, stack):
        # midpoint is 1/3 from the nearest corner, roughly
        rect = stack.pop()
        midcorner = (
                rect[3][0] + 2/3. * (rect[2][0] - rect[3][0]),
                rect[1][1] + 2/3. * (rect[2][1] - rect[1][1])
        )
        major = [rect[0], rect[1], midcorner, rect[3]]
        corner = [midcorner, rect[1], rect[2], rect[3]]
        return stack + [major, corner]

class r_arcs:
    # expects a rect in the stack
    def __call__(self, stack):
        rect = stack.pop()
        topmid = (
                (rect[0][0] + rect[1][0]) / 2,
                rect[0][1]
        )
        botmid = (
                (rect[2][0] + rect[3][0]) / 2,
                rect[2][1]
        )
        midmid = (
                rect[1][0],
                (rect[1][1] + rect[2][1]) / 2
        )
        majorpoly = [rect[0], topmid, midmid, botmid, rect[3]]
        topcorner = [topmid, rect[1], midmid]
        botcorner = [midmid, rect[2], botmid]
        return stack + [majorpoly, topcorner, botcorner]

# top box of two /-slashed boxes
class top_slash:
    # expects a rectangular-ish poly in the stack
    def __call__(self, stack):
        rect = stack.pop()
        # measured from base so that this works with top-arced
        mx = (rect[2][0] + rect[3][0]) / 2
        midcorner = (mx, rect[2][1])
        poly1 = [rect[0], rect[1], midcorner, rect[3]]
        poly2 = [rect[1], rect[2], midcorner]
        return stack + [poly1, poly2]

# bottom box of two /-slashed boxes
class bot_slash:
    # expects a rectangular-ish poly in the stack
    # puts the left-facing triangle part first, then the right-facing big
    def __call__(self, stack):
        rect = stack.pop()
        # measured from top as that's where the line end is
        mx = (rect[1][0] + rect[0][0]) / 2
        midcorner = (mx, rect[0][1])
        poly1 = [rect[0], midcorner, rect[3]]
        poly2 = [(mx, rect[0][1]), rect[1], rect[2], rect[3]]
        return stack + [poly1, poly2]

# top box of two \-lashed boxes
class top_bslash:
    # expects a rectangular-ish poly in the stack
    # puts the left-facing triangle part first, then the right-facing big
    def __call__(self, stack):
        rect = stack.pop()
        # measured from base
        mx = (rect[2][0] + rect[3][0]) / 2
        midcorner = (mx, rect[2][1])
        poly1 = [rect[0], midcorner, rect[3]]
        poly2 = [rect[0], rect[1], rect[2], midcorner]
        return stack + [poly1, poly2]

# bottom box of two \-lashed boxes
class bot_bslash:
    # expects a rectangular-ish poly in the stack
    def __call__(self, stack):
        rect = stack.pop()
        # measured from top
        mx = (rect[1][0] + rect[0][0]) / 2
        midcorner = (mx, rect[1][1])
        poly1 = [rect[0], midcorner, rect[2], rect[3]]
        poly2 = [midcorner, rect[1], rect[2]]
        return stack + [poly1, poly2]
        # see e.g. h5, h4, h6

# XXX just for early development
class dup:
    def __call__(self, stack):
        top = stack.pop()
        return stack + [top, top]

class swap:
    def __call__(self, stack):
        top = stack.pop()
        next = stack.pop()
        return stack + [top, next]

class rot:
    """third item to the top"""
    def __call__(self, stack):
        a = stack.pop()
        b = stack.pop()
        c = stack.pop()
        return stack + [b, a, c]

class rotate:
    """first item to the top"""
    def __call__(self, stack):
        oldest = stack[0]
        return stack[1:] + [oldest]

class lotate:
    """topmost item to the bottom"""
    def __call__(self, stack):
        top = stack.pop()
        return [top] + stack

class slash:
    # expects a rectangular-ish poly in the stack
    def __call__(self, stack):
        rect = stack.pop()
        poly1 = [rect[0], rect[1], rect[3]]
        poly2 = [rect[1], rect[2], rect[3]]
        return stack + [poly1, poly2]

class bslash:
    # expects a rectangular-ish poly in the stack
    def __call__(self, stack):
        rect = stack.pop()
        poly1 = [rect[0], rect[2], rect[3]]
        poly2 = [rect[0], rect[1], rect[2]]
        return stack + [poly1, poly2]

class nop:
    """Specify to draw nothing"""
    def __call__(self, stack):
        return stack + [[]]

# stack based language!
# e.g. slash pops a box(ish), slices it, and puts new parts on
# e.g. tl_arc also pops a quad region, slices it and puts new parts on

# these clauses must match the exact segment order in the pixel map
# (see e.g. h5, h4, h6 or g5, g4, g3, g2, g1)
GFX_LANGUAGE = [
    # top row is special, treated elsewhere
    # 0
    [],
    [],
    [],
    [],
    [],

    # 1
    [full, tl_arc],
    [half],
    [full, tl_arc, top_slash],
    [half],
    [full, tr_arc],

    # 2
    [full, top_bslash],
    [half, bslash],
    [full, bot_slash],
    [half, slash],
    [full, top_slash],

    # 3
    [full, bot_bslash, swap, tl_arc, rot],
    [half, slash],
    [full, top_bslash, slash], # triangle on its corner
    [half],
    [full, bot_slash, tr_arc],

    # 4
    [full, top_slash, swap, bl_arc, rot],
    [half, bslash],
    [full, bot_slash, bslash], # triangle on its base
    [half, slash],
    [full, r_arcs],

    # 5
    # this particular curvy square is really much approximated
    # TODO: add an op to put a vertex in a triangle edge?
    # then some dup and hack and drop might help?
    # real clipping would have low !/$ for just this square
    #
    # any of g5, g4, g3 for now light up the entire left bit
    # (that messes up only s and ŝ that have just g2 g4 g5)
    # g1 does nothing, g2 lights up the big bit including g1
    # (also messes up only s and ŝ, all others have g1 with g2)
    # exec: full => full; bot_slash => small, big; swap => big, small;
    #       dup => big, small, small; dup => big, small, small, small;
    #       final == small small small big nop (g5 g4 g3 g2 g1)
    [full, bot_slash, swap, dup, dup, rotate, nop],
    [half, slash],
    [full, top_bslash, slash], # triangle on its corner
    [half, bslash],
    [full, r_arcs],

    # 6
    [full, top_bslash, slash], # triangle on its corner
    [half, bslash],
    [full, bot_slash, bslash], # triangle on its base
    [half, slash],
    [full, top_bslash, slash], # triangle on its corner

    # 7
    [full, bot_slash, bslash], # triangle on its base
    [half, slash],
    [full, top_bslash, slash], # triangle on its corner
    [half, bslash],
    [full, bot_slash, bslash], # triangle on its base

    # 8
    [full, bl_arc],
    [half, bslash],
    [full, bl_arc],
    [half, slash],
    [full, br_arc],

    # 9
    [full],
    [nop],
    [full],
    [nop],
    [full],

    [full, bl_arc],
    [half],
    [full, br_arc],
    [half],
    [full, br_arc],
]

def run_pure_program(prog):
    stack = []
    for x in prog:
        stack = x()(stack)
    return stack

def emit_polygons(screen, x, y, j, polygons):
    x += OFFX
    y += OFFY
    for (i, poly) in enumerate(polygons):
        if i == j and len(poly) != 0:
            points = [(SCALE*(x + px), SCALE*(y + py)) for (px, py) in poly]
            pygame.gfxdraw.filled_polygon(screen, points, COLOR_SEG)
            pygame.gfxdraw.polygon(screen, points, COLOR_SEG_BORDER)

def run_toprow(screen, posx, posy, x, y, j):
    # j is always 0 here, and TOP_POLYS is special. x varies though
    emit_polygons(screen, posx, -dots_yminus + posy, x, TOP_POLYS)

def run_render_program(screen, posx, posy, x, y, j, prog):
    if y == 0:
        # special top row won't happen here
        raise ValueError("nope")
    else:
        xoffs = [0, fw, fw+hw, fw+hw+fw, fw+hw+fw+hw]
        x = xoffs[x] + x * pad
        y -= 1
        y *= (h + pad)
    polygons = run_pure_program(prog)
    emit_polygons(screen, x + posx, y + posy, j, polygons)

def render(screen, posx, posy, glyphdata):
    pixel_invmap = {}
    for (i, pixel) in enumerate(pixel_map.PIXEL_MAP):
        x = i % 5
        y = i // 5
        for (j, segment_spec) in enumerate(pixel):
            offset_in_digit = pixel_map.BITS_PER_LABEL * segment_spec[0] + segment_spec[1]
            segment = pixel_map.TOTAL_DIGIT_BITS - 1 - offset_in_digit
            pixel_invmap[segment] = (x, y, j)

    # TODO precompute the above and prerender these
    for (i, bit) in enumerate(glyphdata):
        if not bit:
            continue
        (x, y, j) = pixel_invmap[i]

        # just double check
        segment_spec = pixel_map.PIXEL_MAP[5 * y + x][j]
        offset_in_digit = pixel_map.BITS_PER_LABEL * segment_spec[0] + segment_spec[1]
        segment = pixel_map.TOTAL_DIGIT_BITS - 1 - offset_in_digit
        assert segment == i

        if y == 0:
            run_toprow(screen, posx, posy, x, y, j)
        else:
            render_program = GFX_LANGUAGE[y * 5 + x]
            run_render_program(screen, posx, posy, x, y, j, render_program)

def testglyph():
    data = [0] * 120
    (a, b, c, d, e, f, g, h, i, j, k, l, m, n, o) = range(15)
    # note: this validation was built up one by one with GFX_LANGUAGE
    light_up = [
        # row 0, the special one
        (j, 0),
        (j, 5),
        (j, 6),
        (j, 7),
        (k, 6),

        # row 1
        (i, 4),
        (i, 5),

        (j, 1),

        (j, 4),
        (k, 0),
        (k, 2),

        (k, 5),

        (l, 1),
        (l, 2),

        # row 2
        (i, 0),
        (i, 1),

        (i, 2),
        (i, 7),

        (j, 3),
        (k, 1),

        (k, 7),
        (l, 4),

        (l, 5),
        (l, 7),

        # row 3
        (h, 5),
        (h, 4),
        (h, 6),

        (h, 7),
        (i, 3),

        (j, 2),
        (k, 3),
        (l, 0),

        (l, 6),

        (m, 0),
        (m, 3),
        (m, 2),

        # row 4
        (h, 0),
        (h, 1),
        (g, 7),

        (h, 2),
        (h, 3),

        (i, 6),
        (k, 4),
        (l, 3),

        (m, 1),
        (m, 5),

        (m, 7),
        (m, 6),
        (n, 0),

        # row 5
        (g, 5),
        (g, 4),
        (g, 3),
        (g, 2),
        (g, 1),

        (g, 6),
        (g, 0),

        (d, 1),
        (m, 4),
        (n, 6),

        (n, 1),
        (n, 2),

        (n, 4),
        (n, 3),
        (n, 5),

        # row 6
        (f, 5),
        (f, 6),
        (f, 4),

        (f, 3),
        (f, 7),

        (e, 0),
        (b, 0),
        (a, 5),

        (n, 7),
        (o, 3),

        (o, 1),
        (o, 0),
        (o, 2),

        # row 7
        (e, 6),
        (e, 5),
        (e, 4),

        (e, 3),
        (d, 7),

        (d, 0),
        (c, 1),
        (b, 7),

        (b, 1),
        (a, 4),

        (a, 1),
        (a, 3),
        (a, 2),

        # row 8
        (e, 1),
        (e, 2),

        (d, 5),
        (d, 4),

        (c, 6),
        (c, 2),

        (b, 4),
        (b, 3),

        (a, 6),
        (a, 7),

        # row 9
        (d, 6),

        (c, 5),

        (b, 2),

        # row 10
        (d, 3),
        (d, 2),

        (c, 7),

        (c, 4),
        (c, 3),

        (c, 0),

        (b, 6),
        (b, 5),
    ]

    for (a, b) in light_up:
        data[-1 - (8 * a + b)] = 1
    return data

def render_glyph(screen, x, y, font, glyph):
    # special g variation histogram:
    #   2    g2    g4 g5 = bottom left arc (s, ŝ)
    #   4 g1 g2          = angled up right (§, 4, %., §)
    #  12 g1 g2 g3 g4    = top left arc (two symbols, a, ä etc)
    # 111 g1 g2 g3 g4 g5 = all set
    # 127                = nothing set
    # note: g3 == g1 && g2 && g4
    glyphdata = font.get_glyph_data(glyph)
    (a, b, c, d, e, f, g, h, i, j, k, l, m, n, o) = range(15)
    g1 = 120 - 1 - (8*g+1)
    g2 = 120 - 1 - (8*g+2)
    g3 = 120 - 1 - (8*g+3)
    g4 = 120 - 1 - (8*g+4)
    g5 = 120 - 1 - (8*g+5)
    g1 = glyphdata[g1] == 1
    g2 = glyphdata[g2] == 1
    g3 = glyphdata[g3] == 1
    g4 = glyphdata[g4] == 1
    g5 = glyphdata[g5] == 1
    #if g1 and g2 and g3 and g4 and not g5:
    #    print("AAAAA",glyph,chr(glyph),glyph//32,glyph%32)
    g1 = 'g1' if g1 else '  '
    g2 = 'g2' if g2 else '  '
    g3 = 'g3' if g3 else '  '
    g4 = 'g4' if g4 else '  '
    g5 = 'g5' if g5 else '  '
    #print(g1,g2,g3,g4,g5)
    if not render_test_glyph:
        render(screen, x, y, glyphdata)
    else:
        data = testglyph()
        render(screen, x, y, data)

def main():
    font = pixel_map.Font(sys.argv[1])
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080))
    fill = 127
    screen.fill((fill, fill, fill))

    per_row = 32
    xgap = fw
    ygap = h
    for glyph in range(256):
        x = glyph % per_row * (totw + xgap)
        y = glyph // per_row * (toth + ygap)
        pygame.gfxdraw.rectangle(screen,
            pygame.Rect(SCALE*x, SCALE*y, SCALE*totw, SCALE*toth),
            COLOR_DIGIT_BORDER)
        render_glyph(screen, x, y, font, glyph)

    pygame.display.flip()
    pygame.event.pump()
    pygame.image.save(screen, "render.png")

    while True:
        e = pygame.event.wait()
        if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            break

if __name__ == "__main__":
    main()
