"""Configuration for the search server."""
import threading
import heapq
import logging
import requests
import search
import search.config
import flask

# app = flask.Flask(__name__)
test = {}


@search.app.route("/")
def show_index():
    """Display / route."""
    responses = []

    def search_result(url, query, weight):
        tempurl = str(url) + "?q=" + str(query) + "&w=" + str(weight)
        logging.warning(tempurl)
        response = requests.get(tempurl, timeout=5)
        logging.warning(response.json())
        responses.append(response.json()["hits"])

    query = flask.request.args.get("q")
    weight = flask.request.args.get("w")

    if query is None:
        cdic = {}
        cdic["result"] = []
        cdic["query"] = ""
        cdic["weight"] = 0.5
        return flask.render_template("index.html", context=cdic)
    # return f"q: {q}, w: {w}"
    threads = []
    # responses = []
    for url in search.app.config["SEARCH_INDEX_SEGMENT_API_URLS"]:
        thread = threading.Thread(
            target=search_result,
            args=(
                url,
                query,
                weight,
            ),
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()
    temp = []
    for response in responses:
        temp = temp + response
    temp = heapq.nlargest(10, temp, key=lambda x: x["score"])
    cdic = {}
    cdic["results"] = []
    connection = search.model.get_db()
    for tem in temp:
        cur = connection.execute(
            "SELECT * FROM Documents WHERE docid = ?", (tem["docid"],)
        )
        res = cur.fetchall()
        dic = {}
        dic["docid"] = res[0]["docid"]
        dic["title"] = res[0]["title"]
        dic["summary"] = res[0]["summary"]
        dic["url"] = res[0]["url"]
        # dic["score"] = t["score"]
        cdic["results"].append(dic)
    # return context
    cdic["query"] = query
    cdic["weight"] = weight
    # logging.warning(cdic)
    return flask.render_template("index.html", context=cdic)
