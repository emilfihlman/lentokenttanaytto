#!/usr/bin/env python3
import sys
import pygame
import pygame.gfxdraw
import pixel_map

# "full" and "half" width and height; rectangles in the normal region.
# normal region goes full half full half full, with varying splits.
fw = 110
hw = fw / 2
h = 90

dotw = 80

# thick lines in between
pad = 6

# always clockwise

class full:
    def __call__(self, stack):
        poly = [(0, 0), (fw-1, 0), (fw-1, h-1), (0, h-1)]
        return stack + [poly]

class half:
    def __call__(self, stack):
        poly = [(0, 0), (hw-1, 0), (hw-1, h-1), (0, h-1)]
        return stack + [poly]

# FIXME arc approximated by just corners and midpoint
class tl_arc:
    pass
    # expects a rect in the stack
    def __call__(self, stack):
        # midpoint is 1/3 from the nearest corner, roughly
        rect = stack.pop()
        print(rect)
        midcorner = (1/3. * rect[1][0], 1/3. * rect[3][1])
        poly1 = [rect[0], rect[1], midcorner, rect[3]]
        poly2 = [midcorner, rect[1], rect[2], rect[3]]
        return stack + [poly1, poly2]

# FIXME arc approximated by just corners and midpoint
class tr_arc:
    # expects a rect in the stack
    def __call__(self, stack):
        # midpoint is 1/3 from the nearest corner, roughly
        rect = stack.pop()
        midcorner = (2/3. * rect[1][0], 1/3. * rect[2][1])
        poly1 = [rect[0], midcorner, rect[2], rect[3]]
        poly2 = [rect[0], rect[1], rect[2], midcorner]
        return stack + [poly1, poly2]

class top_slash:
    # expects a rectangular-ish poly in the stack
    def __call__(self, stack):
        rect = stack.pop()
        # measured from base so that this works with top-arced (TODO: max or something?)
        mx = (rect[2][0] + rect[3][0]) / 2
        midcorner = (mx, rect[2][1])
        poly1 = [rect[0], rect[1], midcorner, rect[3]]
        poly2 = [rect[1], rect[2], midcorner]
        return stack + [poly1, poly2]

class bot_slash:
    # expects a rectangular-ish poly in the stack
    def __call__(self, stack):
        rect = stack.pop()
        # measured from top as that's where the line end is
        mx = (rect[1][0] + rect[0][0]) / 2
        midcorner = (mx, rect[0][1])
        poly1 = [rect[0], midcorner, rect[3]]
        poly2 = [midcorner, rect[1], rect[2], rect[3]]
        return stack + [poly1, poly2]

class top_bslash:
    # expects a rectangular-ish poly in the stack
    def __call__(self, stack):
        rect = stack.pop()
        # measured from base
        mx = (rect[2][0] + rect[3][0]) / 2
        midcorner = (mx, rect[2][1])
        poly1 = [rect[0], rect[1], rect[2], midcorner]
        poly2 = [rect[0], midcorner, rect[3]]
        return stack + [poly1, poly2]

class bot_bslash:
    pass

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
        poly1 = [rect[0], rect[1], rect[2]]
        poly2 = [rect[0], rect[2], rect[3]]
        return stack + [poly1, poly2]

# stack based language!

# topslash pops a box, slices it, and puts right and left parts on
# tl_arc pops a something region, slices it and puts right and left parts on
GFX_LANGUAGE = [
    # FIXME top row
    [],
    [],
    [],
    [],
    [],

    [full, tl_arc],
    [half],
    [full, tl_arc, top_slash],
    [half],
    [full, tr_arc],

    [full, top_bslash],
    [half, bslash],
    [full, bot_slash],
    [half, slash],
    [full, top_slash],
]

def run_pure_program(prog):
    stack = []
    for x in prog:
        stack = x()(stack)
    return stack

def run_render_program(screen, x, y, j, prog):
    print(x,y,prog)
    xoffs = [0, fw, fw+hw, fw+hw+fw, fw+hw+fw+hw]
    x = xoffs[x] + x * pad
    y *= (h + pad)
    polygons = run_pure_program(prog)
    for (i, poly) in enumerate(polygons):
        if i == j:
            points = [(x + px, y + py) for (px, py) in poly]
            print("poly: %s" % poly)
            pygame.gfxdraw.filled_polygon(screen, points, (255, 255, 255))
            pygame.gfxdraw.polygon(screen, points, (255, 0, 255))

def render(screen, glyphdata):
    pixel_invmap = {}
    for (i, pixel) in enumerate(pixel_map.PIXEL_MAP):
        x = i % 5
        y = i // 5
        for (j, segment_spec) in enumerate(pixel):
            offset_in_digit = pixel_map.BITS_PER_LABEL * segment_spec[0] + segment_spec[1]
            segment = pixel_map.TOTAL_DIGIT_BITS - 1 - offset_in_digit
            pixel_invmap[segment] = (x, y, j)

    # TODO prerender these
    for (i, bit) in enumerate(glyphdata):
        if bit:
            (x, y, j) = pixel_invmap[i]
            print("found",x,y,j)

            segment_spec = pixel_map.PIXEL_MAP[5 * y + x][j]
            offset_in_digit = pixel_map.BITS_PER_LABEL * segment_spec[0] + segment_spec[1]
            segment = pixel_map.TOTAL_DIGIT_BITS - 1 - offset_in_digit
            assert segment == i

            try:
                render_program = GFX_LANGUAGE[y * 5 + x]
            except IndexError:
                # later
                continue
            run_render_program(screen, x, y, j, render_program)

def main():
    font = pixel_map.Font(sys.argv[1])
    text = sys.argv[2]
    glyphdata = font.get_glyph_data(ord(text[0]))
    pygame.init()
    screen = pygame.display.set_mode((1000, 1000))
    render(screen, glyphdata)
    if False:
        data = [0] * 120
        (a, b, c, d, e, f, g, h, i, j, k, l, m, n, o) = range(15)

        # row 1
        data[-1-(8 * i + 4)] = 1
        data[-1-(8 * i + 5)] = 1

        data[-1-(8 * j + 1)] = 1

        data[-1-(8 * j + 4)] = 1
        data[-1-(8 * k + 0)] = 1
        data[-1-(8 * k + 2)] = 1

        data[-1-(8 * k + 5)] = 1

        data[-1-(8 * l + 1)] = 1
        data[-1-(8 * l + 2)] = 1

        # row 2
        data[-1-(8 * i + 0)] = 1
        data[-1-(8 * i + 1)] = 1

        data[-1-(8 * i + 2)] = 1
        data[-1-(8 * i + 7)] = 1

        data[-1-(8 * j + 3)] = 1
        data[-1-(8 * k + 1)] = 1

        data[-1-(8 * k + 7)] = 1
        data[-1-(8 * l + 4)] = 1

        data[-1-(8 * l + 5)] = 1
        data[-1-(8 * l + 7)] = 1
        render(screen, data)
    pygame.display.flip()
    pygame.image.save(screen, "render.png")
    while True:
        e = pygame.event.wait()
        if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            break

if __name__ == "__main__":
    main()
