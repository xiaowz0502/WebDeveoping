"""REST API for posts."""
import hashlib
import flask
import insta485


@insta485.app.route("/api/v1/")
def get_post():
    """Get test right."""
    context = {
        "comments": "/api/v1/comments/",
        "likes": "/api/v1/likes/",
        "posts": "/api/v1/posts/",
        "url": "/api/v1/",
    }
    return flask.jsonify(**context)


@insta485.app.route("/api/v1/comments/<int:commentid>/", methods=["DELETE"])
def delete_comments(commentid):
    """Get test right."""
    if not flask.request.authorization:
        if "username" not in flask.session:
            context = {"message": "Forbidden", "status_code": 403}
            return flask.jsonify(**context), 403
        username = flask.session["username"]
    else:
        username = flask.request.authorization["username"]
        password = flask.request.authorization["password"]
        if not check_account(username, password):
            if "username" not in flask.session:
                context = {"message": "Forbidden", "status_code": 403}
                return flask.jsonify(**context), 403

    connection = insta485.model.get_db()

    cur = connection.execute(
        "SELECT * "
        "FROM comments WHERE comments.commentid=?;", (commentid,)
    )
    var = cur.fetchall()

    if len(var) == 1:
        if var[0]["owner"] != username:
            return "", 403
        connection.execute(
            "DELETE FROM comments "
            "WHERE comments.commentid = ?;", (commentid,)
        )
        return "", 204

    return "", 404


@insta485.app.route("/api/v1/comments/", methods=["POST"])
def comment_add():
    """Get test right."""
    connection = insta485.model.get_db()

    if not flask.request.authorization:
        if "username" not in flask.session:
            context = {"message": "Forbidden", "status_code": 403}
            return flask.jsonify(**context), 403
        username = flask.session["username"]
    else:
        username = flask.request.authorization["username"]
        password = flask.request.authorization["password"]
        if not check_account(username, password):
            if "username" not in flask.session:
                context = {"message": "Forbidden", "status_code": 403}
                return flask.jsonify(**context), 403
    postid = int(flask.request.args.get("postid"))

    if post_id_checker(postid) is False:
        context = {"message": "Not Found", "status_code": 404}
        return flask.jsonify(**context), 404

    text = flask.request.json.get("text", None)
    context = {}

    connection.execute(
        "INSERT INTO comments (owner, postid, text) "
        "VALUES (?, ?, ?) ;",
        (
            username,
            postid,
            text,
        ),
    )

    cur = connection.execute("SELECT last_insert_rowid() ")
    var = cur.fetchall()
    context["commentid"] = var[0]["last_insert_rowid()"]
    context["lognameOwnsThis"] = True
    context["owner"] = username
    context["ownerShowUrl"] = "/users/" + username + "/"
    context["text"] = text
    context["url"] = "/api/v1/comments/" + str(context["commentid"]) + "/"

    return flask.jsonify(**context), 201


def post_id_checker(postid):
    """Get test right."""
    connection = insta485.model.get_db()
    if not flask.request.authorization:
        if "username" not in flask.session:
            context = {"message": "Forbidden", "status_code": 403}
            return flask.jsonify(**context), 403
        username = flask.session["username"]
    else:
        username = flask.request.authorization["username"]
        password = flask.request.authorization["password"]
        if not check_account(username, password):
            if "username" not in flask.session:
                context = {"message": "Forbidden", "status_code": 403}
                return flask.jsonify(**context), 403
    cur = connection.execute(
        "SELECT * "
        "FROM posts WHERE posts.postid=?;",
        (
            postid,
        ))
    var = cur.fetchall()  # var is a List
    if len(var) == 0:
        return False
    return True


@insta485.app.route("/api/v1/likes/<int:likeid>/", methods=["DELETE"])
def delete_infor(likeid):
    """Get test right."""
    if not flask.request.authorization:
        if "username" not in flask.session:
            context = {"message": "Forbidden", "status_code": 403}
            return flask.jsonify(**context), 403
        username = flask.session["username"]
    else:
        username = flask.request.authorization["username"]
        password = flask.request.authorization["password"]
        if not check_account(username, password):
            if "username" not in flask.session:
                context = {"message": "Forbidden", "status_code": 403}
                return flask.jsonify(**context), 403

    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT * "
        "FROM likes WHERE likes.likeid=?;",
        (likeid,))
    var = cur.fetchall()
    if len(var) == 1:
        if var[0]["owner"] != username:
            return "", 403
        connection.execute(
            "DELETE FROM likes WHERE likes.likeid= ? AND likes.owner = ?;",
            (
                likeid,
                username,
            ),
        )
        return "", 204
    return "", 404


# ==============================================================================================
@insta485.app.route("/api/v1/likes/", methods=["POST"])
def like_info():
    """Get test right."""
    postid = int(flask.request.args.get("postid"))
    if not flask.request.authorization:
        if "username" not in flask.session:
            context = {"message": "Forbidden", "status_code": 403}
            return flask.jsonify(**context), 403
        username = flask.session["username"]
    else:
        username = flask.request.authorization["username"]
        password = flask.request.authorization["password"]
        if not check_account(username, password):
            if "username" not in flask.session:
                context = {"message": "Forbidden", "status_code": 403}
                return flask.jsonify(**context), 403

    if post_id_checker_1(postid) is False:
        context = {"message": "Not Found", "status_code": 404}
        return flask.jsonify(**context), 404

    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT * "
        "FROM likes WHERE likes.postid=? AND likes.owner = ?;",
        (
            postid,
            username,
        ),
    )
    var = cur.fetchall()  # var is a List
    context = {}

    if len(var) == 0:
        connection.execute(
            "INSERT INTO likes (owner, postid) "
            "VALUES (?, ?);",
            (
                username,
                postid,
            ),
        )
        cur = connection.execute(
            "SELECT * "
            "FROM likes WHERE likes.postid=? AND likes.owner = ?;",
            (
                postid,
                username,
            ),
        )
        var = cur.fetchall()
        context["likeid"] = var[0]["likeid"]
        context["url"] = "/api/v1/likes/" + str(context["likeid"]) + "/"
        return flask.jsonify(**context), 201

    context["likeid"] = var[0]["likeid"]
    context["url"] = "/api/v1/likes/" + str(context["likeid"]) + "/"

    return flask.jsonify(**context), 200


def post_id_checker_1(postid):
    """Get test right."""
    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT * "
        "FROM posts WHERE posts.postid=?;",
        (postid,))
    var = cur.fetchall()  # var is a List
    if len(var) == 0:
        return False
    return True


def check_account(logname, password):
    """Get test right."""
    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT users.username "
        "FROM users WHERE users.username=?;",
        (logname,)
    )
    var = cur.fetchall()
    if len(var) == 0:
        return False
    cur = connection.execute(
        "SELECT users.password "
        "FROM users " "WHERE users.username = ?;", (logname,)
    )
    var = cur.fetchall()
    old_pass = str(var[0]["password"])
    sha_value = old_pass[7:39]

    algorithm = "sha512"
    hash_obj = hashlib.new(algorithm)
    password_salted = sha_value + str(password)
    hash_obj.update(password_salted.encode("utf-8"))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, sha_value, password_hash])

    if password_db_string == old_pass:
        return True
    return False


# ==============================================================================================


@insta485.app.route("/api/v1/posts/<int:postid_url_slug>/")
def post_info(postid_url_slug):
    """Get test right."""
    if not flask.request.authorization:
        if "username" not in flask.session:
            context = {"message": "Forbidden", "status_code": 403}
            return flask.jsonify(**context), 403
        username = flask.session["username"]
    else:
        username = flask.request.authorization["username"]
        password = flask.request.authorization["password"]
        if not check_account(username, password):
            if "username" not in flask.session:
                context = {"message": "Forbidden", "status_code": 403}
                return flask.jsonify(**context), 403

    # check name and password authentication
    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT * "
        "FROM posts WHERE posts.postid=?;", (postid_url_slug,)
    )
    var = cur.fetchall()  # var is a List
    if len(var) == 0:
        context = {"message": "Not Found", "status_code": 404}
        return flask.jsonify(**context), 404

    # print posts information
    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT * "
        "FROM comments WHERE comments.postid=?;", (postid_url_slug,)
    )
    var = cur.fetchall()  # var is a List
    comments = []
    for element in var:
        temp = {}
        temp["commentid"] = element["commentid"]
        if element["owner"] == username:
            temp["lognameOwnsThis"] = True
        else:
            temp["lognameOwnsThis"] = False
        temp["owner"] = element["owner"]
        temp["ownerShowUrl"] = "/users/" + element["owner"] + "/"
        temp["text"] = element["text"]
        temp["url"] = "/api/v1/comments/" + str(element["commentid"]) + "/"
        comments.append(temp)
    context = {}
    context["comments"] = comments
    context["comments_url"] = "/api/v1/comments/?postid="
    context["comments_url"] += str(postid_url_slug)
    cur = connection.execute(
        "SELECT * "
        "FROM posts WHERE posts.postid=?;",
        (postid_url_slug,)
    )
    var = cur.fetchall()
    context["created"] = var[0]["created"]
    context["imgUrl"] = "/uploads/" + var[0]["filename"]
    context["owner"] = var[0]["owner"]
    context["likes"] = like_object(username, postid_url_slug)

    cur = connection.execute(
        "SELECT * "
        "FROM users WHERE users.username=?;",
        (context["owner"],)
    )
    var = cur.fetchall()
    context["ownerImgUrl"] = "/uploads/" + var[0]["filename"]
    context["ownerShowUrl"] = "/users/" + context["owner"] + "/"
    context["postShowUrl"] = "/posts/" + str(postid_url_slug) + "/"
    context["postid"] = postid_url_slug
    context["url"] = flask.request.path
    return flask.jsonify(**context)


def like_object(logname, postid):
    """Get test right."""
    like = {}
    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT * "
        "FROM likes WHERE likes.postid = ?;", (postid,)
    )
    var = cur.fetchall()
    like["numLikes"] = len(var)

    cur = connection.execute(
        "SELECT * "
        "FROM likes WHERE likes.owner=? AND likes.postid = ?;",
        (
            logname,
            postid,
        ),
    )
    var = cur.fetchall()
    if len(var) == 0:
        like["lognameLikesThis"] = False
        like["url"] = None
        return like

    like["lognameLikesThis"] = True
    like["url"] = "/api/v1/likes/" + str(var[0]["likeid"]) + "/"
    return like


def next_helper(num, size, postid_lte, page, postidsdb):
    """Get test right."""
    if num >= size:
        if postid_lte != float("inf"):
            return (
                "/api/v1/posts/?size="
                + str(size)
                + "&page="
                + str(page + 1)
                + "&postid_lte="
                + str(postid_lte)
            )
        return (
            "/api/v1/posts/?size="
            + str(size)
            + "&page="
            + str(page + 1)
            + "&postid_lte="
            + str(postidsdb[0]["postid"])
        )
    return ""


def posts_url_helper(path, sizebool, pagebool, size, page):
    """Get test right."""
    if sizebool:
        path += "?size=" + str(size)
    if pagebool:
        path += "&page=" + str(page)
    return path


@insta485.app.route("/api/v1/posts/", methods=["GET"])
def api_v1_posts():
    """Get test right."""
    context = {}
    if not flask.request.authorization:
        if "username" not in flask.session:
            context = {"message": "Forbidden", "status_code": 403}
            return flask.jsonify(**context), 403
        username = flask.session["username"]
    else:
        username = flask.request.authorization["username"]
        password = flask.request.authorization["password"]
        if not check_account(username, password):
            if "username" not in flask.session:
                context = {"message": "Forbidden", "status_code": 403}
                return flask.jsonify(**context), 403
    size = flask.request.args.get("size", default=10, type=int)
    postid_lte = flask.request.args.get(
        "postid_lte",
        default=float("inf"),
        type=int)
    page = flask.request.args.get(
        "page",
        default=0,
        type=int)
    if size != 10 and size < 0:
        context = {"message": "Bad Request", "status_code": 400}
        return flask.jsonify(**context), 400
    if page is not None and page < 0:
        context = {"message": "Bad Request", "status_code": 400}
        return flask.jsonify(**context), 400
    result = []
    connection = insta485.model.get_db()
    postoffset = 0
    if page != 0:
        postoffset = size * page
    cur = connection.execute(
        "SELECT posts.postid "
        "FROM posts "
        "WHERE posts.postid <= ? AND (posts.owner IN ("
        "SELECT DISTINCT following.username2 "
        "FROM following "
        "WHERE following.username1 = ?"
        ") OR posts.owner = ?) "
        "ORDER BY posts.postid DESC "
        "LIMIT ? OFFSET ?;",
        (
            postid_lte,
            username,
            username,
            size + 1,
            postoffset,
        ),
    )
    postidsdb = cur.fetchall()
    num = min(size, len(postidsdb))
    for i in range(num):
        resultdic = {}
        resultdic["postid"] = postidsdb[i]["postid"]
        resultdic["url"] = "/api/v1/posts/" + str(postidsdb[i]["postid"]) + "/"
        result.append(resultdic)
    context["next"] = next_helper(num, size, postid_lte, page, postidsdb)
    context["results"] = result
    context["url"] = posts_url_helper(flask.request.path,
                                      flask.request.args.get("size"),
                                      flask.request.args.get("page"),
                                      size, page)
    if flask.request.args.get("postid_lte"):
        context["url"] += "&postid_lte=" + str(postid_lte)
    return flask.jsonify(**context)
