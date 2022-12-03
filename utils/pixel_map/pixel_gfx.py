#!/usr/bin/env python3
import sys
import pygame
import pygame.gfxdraw
import pixel_map
from time import sleep

# FIXME: any off-by-ones?

# emphasis around each segment
hide_borders = False
# whatever is in testglyph(), all segments by default
render_test_glyph = False
# box around each digit for visualization
render_regions = True
# visualize some stack ops instead of drawing lcd data
stack_debug_mode = False

# guess what this is
CANVAS_SIZE = (1920, 1080)
# non-illuminated segment and general screen padding
COLOR_BACK = (127, 127, 127)
# illuminated segment
COLOR_SEG = (255, 255, 255)
# segment surroundings
COLOR_SEG_BORDER = (0, 0, 0)
if hide_borders:
    COLOR_SEG_BORDER = COLOR_SEG
# box around each digit for visualization
COLOR_DIGIT_BORDER = (100, 0, 0)
# digits for each row, determines digit size
if stack_debug_mode:
    PER_ROW = 4
else:
    PER_ROW = 32

# "full" and "half" width and height; rectangles in the normal region.
# normal region goes full half full half full, with varying splits.
fw = 110
hw = fw / 2
h = 90

DIGIT_GAP_W = fw
DIGIT_GAP_H = h

# top row region is special
dots_sz = 80 # height of the row, and width of dot squares
dots_x = 15 # from left of normal region to left of dots
dots_yminus = dots_sz + 75 # from top of dots to top of normal region

# thick lines in between
pad = 6

middlex = fw + pad + hw + pad + fw/2
totw = 3 * fw + 2 * hw + 4 * pad
toth = dots_yminus + 10 * h + 9 * pad

# get the nominal values below to make a 32x8 grid
SCALE = CANVAS_SIZE[0] / (PER_ROW * totw + (PER_ROW-1) * DIGIT_GAP_W)

# again, top row is special
dots_topx = [
    dots_x, dots_x + dots_sz - 1,
    middlex - 55, middlex - 30,
    middlex + 30, middlex + 55,
    totw-1 - dots_x, totw - dots_x - dots_sz,
]
dots_midy = 48
dots_botx = [
    dots_x, dots_x + dots_sz - 1,
    middlex - 106, middlex - 23,
    middlex + 23, middlex + 106,
    totw-1 - dots_x, totw - dots_x - dots_sz,
]

# relative to -dots_yminus
TOP_POLYS = [
    [
        (dots_topx[0], 0),
        (dots_topx[1], 0),
        (dots_topx[1], dots_sz - 1),
        (dots_topx[0], dots_sz - 1),
    ],
    [
        (dots_topx[2], 0),
        (dots_topx[3], 0),
        (middlex, dots_midy),
        (dots_botx[3], dots_sz - 1),
        (dots_botx[2], dots_sz - 1),
    ],
    [
        (dots_topx[3], 0),
        (dots_topx[4], 0),
        (middlex, dots_midy),
    ],
    [
        (dots_topx[4], 0),
        (dots_topx[5], 0),
        (dots_botx[5], dots_sz - 1),
        (dots_botx[4], dots_sz - 1),
        (middlex, dots_midy),
    ],
    [
        (dots_topx[6], 0),
        (dots_topx[7], 0),
        (dots_topx[7], dots_sz - 1),
        (dots_topx[6], dots_sz - 1),
    ],
]

# "canonical order" consistency rules so that these work together:
# - PIXEL_MAP specifies segments from left to right, top to bottom
# - left means the segment faces the left edge of its surrounding box
# - all left things go first, like in g5..g1
# - these stack operations also output things left to right
# - vertices always go clockwise in a polygon
# - a polygon always starts from the top left when it matters
# - triangles are not (yet) split up so they might be inconsistent?

class full:
    """Emit a full size box"""
    def __call__(self, stack):
        poly = [(0, 0), (fw-1, 0), (fw-1, h-1), (0, h-1)]
        return stack + [poly]

class half:
    """Emit a half size box"""
    def __call__(self, stack):
        poly = [(0, 0), (hw-1, 0), (hw-1, h-1), (0, h-1)]
        return stack + [poly]

# FIXME all these arcs are approximated by just corners and midpoint,
# looks good enough from afar but poor when zoomed in

def acvect1d(a, b):
    """arc-corner vect from a to b"""
    return a + 0.3 * (b - a)

def acvect(mid, end_hori, end_vert):
    """arc-corner vect around a corner at mid"""
    return (acvect1d(mid[0], end_hori[0]), acvect1d(mid[1], end_vert[1]))

class tl_arc:
    """Split a quad into top-left corner and remaining major part"""
    def __call__(self, stack):
        quad = stack.pop()
        midvert = acvect(quad[0], quad[1], quad[3])
        corner = [quad[0], quad[1], midvert, quad[3]]
        major = [midvert, quad[1], quad[2], quad[3]]
        return stack + [corner, major]

class tr_arc:
    """Split a quad into remaining major part and top-right corner"""
    def __call__(self, stack):
        quad = stack.pop()
        midvert = acvect(quad[1], quad[0], quad[2])
        major = [quad[0], midvert, quad[2], quad[3]]
        corner = [quad[0], quad[1], quad[2], midvert]
        return stack + [major, corner]

class bl_arc:
    """Split a quad into bottom-left corner and remaining major part"""
    def __call__(self, stack):
        quad = stack.pop()
        midvert = acvect(quad[3], quad[2], quad[0])
        corner = [quad[0], midvert, quad[2], quad[3]]
        major = [quad[0], quad[1], quad[2], midvert]
        return stack + [corner, major]

class br_arc:
    """Split a quad into remaining major part and bottom-right corner"""
    def __call__(self, stack):
        quad = stack.pop()
        midvert = acvect(quad[2], quad[3], quad[1])
        major = [quad[0], quad[1], midvert, quad[3]]
        corner = [midvert, quad[1], quad[2], quad[3]]
        return stack + [major, corner]

# (there is no left equivalent although the complex g is similar)
class r_arcs:
    """Split a quad into remaining major part and top and bottom right corners"""
    def __call__(self, stack):
        quad = stack.pop()
        topmid = (
                (quad[0][0] + quad[1][0]) / 2,
                quad[0][1]
        )
        botmid = (
                (quad[2][0] + quad[3][0]) / 2,
                quad[2][1]
        )
        midmid = (
                quad[1][0],
                (quad[1][1] + quad[2][1]) / 2
        )
        majorpoly = [quad[0], topmid, midmid, botmid, quad[3]]
        topcorner = [topmid, quad[1], midmid]
        botcorner = [midmid, quad[2], botmid]
        return stack + [majorpoly, topcorner, botcorner]

class slash:
    """Split a box into left and right /-slashed triangles"""
    def __call__(self, stack):
        quad = stack.pop()
        left = [quad[0], quad[1], quad[3]]
        right = [quad[1], quad[2], quad[3]]
        return stack + [left, right]

class bslash:
    """Split a box into left and right \-slashed triangles"""
    def __call__(self, stack):
        quad = stack.pop()
        left = [quad[0], quad[2], quad[3]]
        right = [quad[0], quad[1], quad[2]]
        return stack + [left, right]

class top_slash:
    """Split a top of two /-together boxes into big and small bits"""
    def __call__(self, stack):
        quad = stack.pop()
        midvert = (
                (quad[2][0] + quad[3][0]) / 2,
                quad[2][1]
        )
        big = [quad[0], quad[1], midvert, quad[3]]
        small = [quad[1], quad[2], midvert]
        return stack + [big, small]

class bot_slash:
    """Split a bottom of two /-together boxes into small and big bits"""
    def __call__(self, stack):
        quad = stack.pop()
        midvert = (
                (quad[1][0] + quad[0][0]) / 2,
                quad[0][1]
        )
        small = [quad[0], midvert, quad[3]]
        big = [midvert, quad[1], quad[2], quad[3]]
        return stack + [small, big]

class top_bslash:
    """Split a top of two \-together boxes into small and big bits"""
    def __call__(self, stack):
        quad = stack.pop()
        midvert = (
                (quad[2][0] + quad[3][0]) / 2,
                quad[2][1]
        )
        small = [quad[0], midvert, quad[3]]
        big = [quad[0], quad[1], quad[2], midvert]
        return stack + [small, big]

class bot_bslash:
    """Split a bottom of two \-together boxes into big and small bits"""
    def __call__(self, stack):
        quad = stack.pop()
        midvert = (
                (quad[1][0] + quad[0][0]) / 2,
                quad[1][1]
        )
        big = [quad[0], midvert, quad[2], quad[3]]
        small = [midvert, quad[1], quad[2]]
        return stack + [big, small]
        # see e.g. h5, h4, h6

class dup:
    """Duplicate the top polygon of the stack"""
    def __call__(self, stack):
        top = stack.pop()
        return stack + [top, top]

class swap:
    """Swap the top two elements together"""
    def __call__(self, stack):
        top = stack.pop()
        next = stack.pop()
        return stack + [top, next]

class rot3:
    """Bring the third item to the top"""
    def __call__(self, stack):
        a = stack.pop()
        b = stack.pop()
        c = stack.pop()
        return stack + [b, a, c]

class rotall:
    """Bring the bottom item to the top"""
    def __call__(self, stack):
        oldest = stack[0]
        return stack[1:] + [oldest]

class nop:
    """Emit an empty object"""
    def __call__(self, stack):
        return stack + [[]]

# stack based language!
# e.g. slash pops a box(ish), slices it, and puts new parts on
# e.g. tl_arc also pops a quad region, slices it and puts new parts on

# these clauses must match the exact segment order in the pixel map
# (see e.g. h5, h4, h6 or g5, g4, g3, g2, g1)
GFX_PROGRAMS = [
    # top row is special, treated elsewhere
    # 0 is nothing

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
    [full, bot_bslash, swap, tl_arc, rot3],
    [half, slash],
    [full, top_bslash, slash], # triangle on its corner
    [half],
    [full, bot_slash, tr_arc],

    # 4
    [full, top_slash, swap, bl_arc, rot3],
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
    [full, bot_slash, swap, dup, dup, rotall, nop],
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
    """Run a pixel splitting program, return completed stack"""
    stack = []
    for x in prog:
        # could live with just functions for now, but this is future-proof
        stack = x()(stack)
    return stack

def emit_polygon(screen, x, y, j, polygons):
    """Render a segment in an area specified in PIXEL_MAP"""
    poly = polygons[j]
    if len(poly) != 0:
        points = [(SCALE*(x + px), SCALE*(y + py)) for (px, py) in poly]
        pygame.gfxdraw.filled_polygon(screen, points, COLOR_SEG)
        pygame.gfxdraw.polygon(screen, points, COLOR_SEG_BORDER)

def run_toprow(screen, base_x, base_y, x, j):
    """Emit top row segment"""
    # j is always 0 here, and TOP_POLYS is indexed by x, not j
    emit_polygon(screen, base_x, base_y, x, TOP_POLYS)

def run_render_program(screen, base_x, base_y, x, y, j, prog):
    """Emit bottom row segment from a program generating its box"""
    xoffs = [0, fw, fw+hw, fw+hw+fw, fw+hw+fw+hw]
    x = xoffs[x] + x * pad
    y *= h + pad
    polygons = run_pure_program(prog)
    emit_polygon(screen, x + base_x, dots_yminus + y + base_y, j, polygons)

def render(screen, base_x, base_y, glyphdata):
    """Render a glyph to screen at (base_x, base_y)"""
    # note: some are padding bits and are left as None
    pixel_invmap = [None] * pixel_map.TOTAL_DIGIT_BITS
    for (i, pixel) in enumerate(pixel_map.PIXEL_MAP):
        x = i % pixel_map.W
        y = i // pixel_map.W
        for (j, seg_spec) in enumerate(pixel):
            offset_in_digit = pixel_map.BITS_PER_LABEL * seg_spec[0] + seg_spec[1]
            segment = pixel_map.TOTAL_DIGIT_BITS - 1 - offset_in_digit
            pixel_invmap[segment] = (x, y, j)

    # TODO precompute the above and prerender these
    for (i, (bit, inv)) in enumerate(zip(glyphdata, pixel_invmap)):
        if not bit:
            continue
        (x, y, j) = inv

        # just double check
        seg_spec = pixel_map.PIXEL_MAP[pixel_map.W * y + x][j]
        offset_in_digit = pixel_map.BITS_PER_LABEL * seg_spec[0] + seg_spec[1]
        segment = pixel_map.TOTAL_DIGIT_BITS - 1 - offset_in_digit
        assert segment == i

        if y == 0:
            run_toprow(screen, base_x, base_y, x, j)
        else:
            render_program = GFX_PROGRAMS[(y - 1) * pixel_map.W + x]
            run_render_program(screen, base_x, base_y, x, y - 1, j, render_program)

def flatten_once(lst):
    """[[a, b], [c, d]] -> [a, b, c, d]"""
    for a in lst:
        for b in a:
            yield b

def testglyph():
    """Unit test stuff for early development"""
    data = [0] * pixel_map.TOTAL_DIGIT_BITS
    # note: this validation was built up one by one with GFX_PROGRAMS
    (a, b, c, d, e, f, g, h, i, j, k, l, m, n, o) = range(15)
    # or do manual list indices like [(j, 0), (i, 4), (i, 5), ... ]
    light_up = flatten_once(pixel_map.PIXEL_MAP)

    for (a, b) in light_up:
        data[-1 - (8 * a + b)] = 1
    return data

def render_glyph(screen, x, y, font, glyph):
    """Render a glyph code from a font to screen, top left at (x, y)"""
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

def render_array(screen, font, glyphs):
    for (i, glyph) in enumerate(glyphs):
        x = i % PER_ROW * (totw + DIGIT_GAP_W)
        y = i // PER_ROW * (toth + DIGIT_GAP_H)
        if render_regions:
            pygame.gfxdraw.rectangle(screen,
                pygame.Rect(SCALE*x, SCALE*y, SCALE*totw, SCALE*toth),
                COLOR_DIGIT_BORDER)
        render_glyph(screen, x, y, font, glyph)

def stack_debug_demo(screen):
    programs = [
        (hw, 1, [half]),
        (hw, 2, [half, slash]),
        (hw, 2, [half, bslash]),
        (fw, 1, [full]),
        (fw, 2, [full, tl_arc]),
        (fw, 2, [full, tr_arc]),
        (fw, 2, [full, bl_arc]),
        (fw, 2, [full, br_arc]),
        (fw, 2, [full, top_slash]),
        (fw, 2, [full, bot_slash]),
        (fw, 2, [full, top_bslash]),
        (fw, 2, [full, bot_bslash]),
        (fw, 3, [full, r_arcs]),
        (fw, 3, [full, top_bslash, slash]), # triangle on its corner
        (fw, 3, [full, bot_slash, bslash]), # triangle on its base
        (fw, 3, [full, tl_arc, top_slash]),
    ]
    rows_per_column = 8
    padx = fw
    pady = h
    colspacing = 4 * 1.5 * fw
    for i, (w, npixels, prog) in enumerate(programs):
        column = i // rows_per_column
        basex = padx + column * colspacing
        y = pady + (i % rows_per_column) * 1.5 * h
        for j in range(1, 1 << npixels):
            polygons = run_pure_program(prog)
            x = basex + (j - 1) * 1.5 * w
            for b in range(npixels):
                if (j & (1 << b)) != 0:
                    emit_polygon(screen, x, y, b, polygons)
            pygame.gfxdraw.rectangle(screen,
                pygame.Rect(SCALE*x, SCALE*y, SCALE*w, SCALE*h),
                COLOR_DIGIT_BORDER)

def main():
    pygame.init()
    screen = pygame.display.set_mode(CANVAS_SIZE)
    screen.fill(COLOR_BACK)

    if stack_debug_mode:
        stack_debug_demo(screen)
    else:
        font = pixel_map.Font(sys.argv[1])

        if len(sys.argv) >= 3:
            text = map(ord, " ".join(sys.argv[2:]))
        else:
            # draw them all by default
            text = range(256)
        render_array(screen, font, text)

    pygame.display.flip()
    pygame.event.pump()
    pygame.image.save(screen, "render.png")

    while True:
        e = pygame.event.wait()
        if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            break

if __name__ == "__main__":
    main()
