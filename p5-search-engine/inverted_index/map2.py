#!/usr/bin/env python3
"""Map 2."""
import sys

for line in sys.stdin:
    key, freq = line.split("\t")
    docid, word = key.split(" ")
    print(f"{word}\t{docid} {freq}", end="")
