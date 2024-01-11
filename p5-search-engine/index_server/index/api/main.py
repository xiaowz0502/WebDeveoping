"""Main module for API."""
import pathlib
import re
import flask
import index


curpath = pathlib.Path().absolute()
# if __name__ == '__main__':
#     app.run(host='127.0.0.1', threaded=True)


def load_index():
    """Load inverted index, stopwords, and pagerank into memory."""
    # print("successful")
    # word = index.app.config["INDEX_PATH"]
    # print(word)
    load_words()
    load_stopwords()
    load_pgrank()
    # print("terms: ", terms)
    # print("stopwords: ", stopwords)
    # print("pgrank: ", pgrank)


def load_words():
    """Load inverted index into memory."""
    # print("current parent", curpath)
    # print("原来的path", app.config["INDEX_PATH"])
    fname = index.app.config["INDEX_PATH"]
    path = str(curpath) + "/index_server/index/inverted_index/" + fname
    # print("path: ", path)
    path = pathlib.Path(path)
    # print(path)
    terms = {}
    with open(path, "r", encoding="utf-8") as file:
        while True:
            num = file.readline()
            if not num:
                break
            num = num.split()
            term = num[0]
            idfk = num[1]
            length = len(num)
            terms[term] = {}
            data = terms[term]
            data["idfk"] = idfk
            data["docid"] = {}
            for i in range(2, length, 3):
                list_fre_nor = []
                list_fre_nor.append(num[i + 1])
                list_fre_nor.append(num[i + 2])
                data["docid"][num[i]] = list_fre_nor
    index.app.config["words"] = terms
    # print("terms: ", terms["1690"])


def load_stopwords():
    """Load stopwords into memory."""
    path = str(curpath) + "/index_server/index/" + "stopwords.txt"
    # print("path:", path)
    stopwords = {}
    with open(path, "r", encoding="utf-8") as file_one:
        while True:
            stop_word = file_one.readline()
            if not stop_word:
                break
            stopwords[str(stop_word).replace("\n", "")] = 1
    # print("stopwords: ", stopwords)
    index.app.config["stopwords"] = stopwords


def load_pgrank():
    """Load pagerank into memory."""
    pgrank = {}
    path = str(curpath) + "/index_server/index/" + "pagerank.out"
    # print("path: ", path)
    with open(path, "r", encoding="utf-8") as file_two:
        while True:
            line = file_two.readline()
            if not line:
                break
            docid, rank = line.split(",")
            pgrank[docid] = rank.replace("\n", "")
    # print("pgrank: ", pgrank)
    index.app.config["pgrank"] = pgrank


@index.app.route("/api/v1/", methods=["GET"])
def get_services():
    """Get services."""
    context = {"hits": "/api/v1/hits/", "url": "/api/v1/"}
    return flask.jsonify(**context)


@index.app.route("/api/v1/hits/")
def get_hits():
    """Get hits."""
    query = flask.request.args.get("q")
    weight = flask.request.args.get("w", default=0.5, type=float)
    querydic = cleaning_word(query)
    hits = calculate_score(querydic, weight)
    context = {"hits": hits}
    return flask.jsonify(**context)


def cleaning_word(query):
    """Clean the query."""
    stop_word = index.app.config["stopwords"]
    query = re.sub(r"[^a-zA-Z0-9 ]+", "", str(query)).casefold()
    query = query.split()
    querydic = {}
    for word in query:
        if word not in stop_word.keys():
            querydic[word] = querydic.get(word, 0) + 1
    return querydic


def calculate_score(querydic, weight):
    """Calculate the score."""
    terms = index.app.config["words"]
    pgrank = index.app.config["pgrank"]
    result = []
    ids = []
    for word in querydic.keys():
        if word in terms.keys():
            ids.append(terms[word]["docid"].keys())
        else:
            return result

    if len(ids) == 0:
        return result

    id_set = set(ids[0])
    for iden in ids[1:]:
        id_set = id_set.intersection(set(iden))
    return calculate_help(id_set, querydic, terms, pgrank, weight)


def calculate_help(id_set, querydic, terms, pgrank, weight):
    """Calculate the score."""
    result = []
    for docid in id_set:
        score = {}
        qnorm = 0
        dnorm = 0
        queryvec = []
        docvec = []
        for word in querydic.keys():
            # idfk = float(terms[word]["idfk"])
            queryvec.append(float(terms[word]["idfk"]) * querydic[word])
            qnorm += (float(float(terms[word]["idfk"])) * querydic[word]) ** 2
            docvec.append(
                float(terms[word]["docid"][docid][0])
                * float(terms[word]["idfk"])
            )
            dnorm = terms[word]["docid"][docid][1]
        qnorm = qnorm**0.5
        dnorm = float(dnorm) ** 0.5
        # print("pgrank docid:", float(pgrank[docid]))
        # print("queryvec: ", queryvec)
        # print("docvec: ", docvec)
        dot = 0
        for i in enumerate(queryvec):
            dot += queryvec[i[0]] * docvec[i[0]]
        # print("dot:", dot)
        # print("scoreval:", scoreval)
        score["docid"] = int(docid)
        score["score"] = weight * float(pgrank[docid])
        score["score"] += (1.0 - weight) * (dot / (qnorm * dnorm))
        result.append(score)
    return sorted(result, key=lambda x: x["score"], reverse=True)[0:10]
