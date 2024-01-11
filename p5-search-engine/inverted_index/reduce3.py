#!/usr/bin/env python3
"""
Template reducer.

https://github.com/eecs485staff/madoop/blob/main/README_Hadoop_Streaming.md
"""
import math
import sys
import itertools


def reduce_one_group(_, group):
    """Reduce one group."""
    dic_nor = {}
    terms = []

    for line in group:
        value = line.partition("\t")[2]
        word, docid, idfk, freq = value.split(" ")
        # number = dic_nor.get(docid, 0)
        # number  += (int(freq) * int(idfk))**2
        # print("docid:", docid)
        # print("word:", word)
        # print("freq:", freq[:-1])
        # print("idfk:", idfk)
        # print("value in dic:", dic_nor.get(docid, 0))
        # print("idf * freq ^2:", math.pow(float(freq[:-1]) * float(idfk), 2))
        dic_nor[docid] = dic_nor.get(docid, 0) + math.pow(
            float(freq[:-1]) * float(idfk), 2
        )
        # print("final result", dic_nor[docid])
        # print("=============================================================")
        temp = [word, idfk, docid, freq[:-1]]
        terms.append(temp)

    # print(terms)
    # print("final result before sqrt:", dic_nor)
    # for nor in dic_nor.keys():
    #     dic_nor[nor] = math.sqrt(dic_nor[nor])
    if len(terms) == 0:
        return

    prev = 0
    result = f"{terms[prev][0]} {terms[prev][1]}"
    result += f" {terms[prev][2]} {terms[prev][3]} {dic_nor[terms[prev][2]]}"
    for info in terms[1:]:
        if info[0] == terms[prev][0]:
            result += f" {info[2]} {info[3]} {dic_nor[info[2]]}"
        else:
            print(result)
            result = f"{info[0]} {info[1]}"
            result += f" {info[2]} {info[3]} {dic_nor[info[2]]}"
        prev += 1
    print(result)


def keyfunc(line):
    """Return the key from a TAB-delimited key-value pair."""
    return line.partition("\t")[0]


def main():
    """Divide sorted lines into groups that share a key."""
    for key, group in itertools.groupby(sys.stdin, keyfunc):
        reduce_one_group(key, group)


if __name__ == "__main__":
    main()
