"""Configuration for the search server."""
import pathlib
import search
search.app.config["SEARCH_INDEX_SEGMENT_API_URLS"] = [
    "http://localhost:9000/api/v1/hits/",
    "http://localhost:9001/api/v1/hits/",
    "http://localhost:9002/api/v1/hits/",
]
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATABASE_FILENAME = ROOT/'var'/'search.sqlite3'
