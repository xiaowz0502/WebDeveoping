#!/usr/bin/env python3
"""Map 1."""
import sys
import re
import pathlib

stopdic = {}
path = pathlib.Path("stopwords.txt")
with open(path, "r", encoding="utf-8") as f:
    while True:
        stop_word = f.readline()
        if not stop_word:
            break
        stopdic[str(stop_word).replace("\n", "")] = 1

for line in sys.stdin:
    temp = re.split(r"\",\s*\"", line)
    # doc_id, title, content=
    doc_id = re.sub(r"[^a-zA-Z0-9 ]+", "", temp[0])
    text = f"{temp[1]} {temp[2]}"
    text = re.sub(r"[^a-zA-Z0-9 ]+", "", text).casefold()

    text_list = text.split()
    keys = stopdic.keys()
    for word in text_list:
        if word not in keys:
            print(f"{doc_id} {word}\t1")
