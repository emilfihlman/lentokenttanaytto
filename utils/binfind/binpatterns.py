#!/usr/bin/env python3
from sys import argv

# note: turned out lucky with the font, no need to try padding, lsb, or other such variations

def expand_bits_msb(bytestring):
    for b in bytestring:
        for i in range(8):
            bitval = (0x80 >> i) & b
            yield 1 if bitval != 0 else 0

def try_find(binary, bit_pattern):
    pat_len = len(bit_pattern)
    binary = list(expand_bits_msb(binary))
    for start_offset in range(len(binary)):
        if binary[start_offset:start_offset + pat_len] == bit_pattern:
            print("bits: %s, bytes: %s" % (start_offset, start_offset / 8.0))

def find_part_of_p(filename):
    bit_patterns = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0],
        [0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]
    binary = open(filename, 'rb').read()
    for (i, pat) in enumerate(bit_patterns):
        print("%s as is?" % i)
        try_find(binary, pat)
        print("%s reversed?" % i)
        try_find(binary, pat[::-1])


def main(binfilename):
    find_part_of_p(binfilename)

if __name__ == "__main__":
    main(*argv[1:])
