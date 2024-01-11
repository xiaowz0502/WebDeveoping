#!/usr/bin/env python3
"""Map 3."""
import sys


for line in sys.stdin:
    docid, value = line.split("\t")
    # print("docid:", docid)
    # print("value:", value)
    word, freq, idfk = value.split(" ")
    # print("word:", word)
    # print("freq:", freq)
    # print("idfk:", idfk[:-1])
    # print ("/n")
    print(f"{str(int(docid) % 3)}\t{word} {docid} {idfk[:-1]} {freq}")
