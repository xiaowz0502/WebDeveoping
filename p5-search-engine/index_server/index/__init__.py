"""Load various files( stop, index, pagerank."""
import os
import flask
# Load inverted index, stopwords, and pagerank into memory
app = flask.Flask(__name__)
app.config["INDEX_PATH"] = os.getenv("INDEX_PATH", "inverted_index_1.txt")
import index.api  # noqa: E402  pylint: disable=wrong-import-position
index.api.load_index()
