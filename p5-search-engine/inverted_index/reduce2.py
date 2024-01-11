#!/usr/bin/env python3
"""
Template reducer.

https://github.com/eecs485staff/madoop/blob/main/README_Hadoop_Streaming.md
"""
import pathlib
import sys
import itertools
import math


def reduce_one_group(_, group):
    """Reduce one group."""
    number = 0
    path = pathlib.Path("total_document_count.txt")
    with open(path, "r", encoding="utf-8") as file:
        num = file.readline()
        number = int(num.replace("\n", ""))
    n_k = 0
    lis = []
    for line in group:
        # print(line)
        n_k += 1
        # print (line)
        word, _, value = line.partition("\t")
        # print(value)
        docid, freq = value.split(" ")
        # print("docid:", docid)
        lis.append(f"{docid}\t{word} {freq[:-1]}")

        # print(freq)
        # print(f"{docid}\t{key} {freq}")
    idfk = str(math.log10(float(number / n_k)))
    for l_i in lis:
        print(f"{l_i} {idfk}")


def keyfunc(line):
    """Return the key from a TAB-delimited key-value pair."""
    return line.partition("\t")[0]


def main():
    """Divide sorted lines into groups that share a key."""
    for key, group in itertools.groupby(sys.stdin, keyfunc):
        # print(list(key))
        reduce_one_group(key, group)


if __name__ == "__main__":
    main()
