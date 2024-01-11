
"""
Insta485 index (main) view.

URLs include:
/
"""
import pathlib
from pathlib import Path
import uuid
import os
import hashlib
import flask
import arrow
import insta485

app = flask.Flask(__name__)


@insta485.app.route('/')
def show_index():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    # flask.session.clear()
    # return "sucess"

    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    # Connect to database
    connection = insta485.model.get_db()
    # Query database
    logname = flask.session["username"]
    context = {}
    context["logname"] = logname

    context["posts"] = []
    cur = connection.execute(
        "SELECT posts.postid "
        "FROM posts "
        "WHERE posts.owner IN ("
        "SELECT DISTINCT following.username2 "
        "FROM following "
        "WHERE following.username1 = ?"
        ") OR posts.owner = ? "
        "ORDER BY posts.created DESC;",
        (logname, logname, ))
    postidsdb = cur.fetchall()

    postids = []
    for postid in postidsdb:
        postids.append(postid['postid'])
    postids.sort(reverse=True)
    for postid in postids:
        postdic = {}
        postdic["postid"] = postid
        cur = connection.execute(
            "SELECT users.filename AS ufname, posts.owner, "
            "posts.filename AS pfname, posts.created "
            "FROM users, posts "
            "WHERE posts.postid = ? AND posts.owner = users.username;",
            (postid, ))
        postinfosdb = cur.fetchall()

        for postinfo in postinfosdb:
            postdic["owner"] = postinfo['owner']
            postdic["owner_img_url"] = postinfo['ufname']
            postdic["img_url"] = postinfo['pfname']
            postdic["timestamp"] = arrow.get(postinfo['created']).humanize()
        cur = connection.execute(
            "SELECT likes.likeid "
            "FROM likes "
            "WHERE likes.postid = ?;", (postid, ))
        likesdb = cur.fetchall()
        postdic["likes"] = len(likesdb)
        cur = connection.execute(
            "SELECT likes.likeid "
            "FROM likes "
            "WHERE likes.postid = ? AND likes.owner = ?;",
            (postid, logname, ))
        likebooldb = cur.fetchall()
        # for likebool in likebooldb:
        #     postdic["likebool"] = likebool['likeid']
        postdic["likebool"] = bool(len(likebooldb))

        cur = connection.execute(
            "SELECT comments.owner, comments.text "
            "FROM comments "
            "WHERE comments.postid = ? "
            "ORDER BY comments.created;", (postid, ))
        postdic["comments"] = []
        commentdb = cur.fetchall()

        for com in commentdb:
            comment = {}
            comment["owner"] = com['owner']
            comment["text"] = com['text']
            postdic["comments"].append(comment)
        context["posts"].append(postdic)
    return flask.render_template(
                                'index.html',
                                lognamecc=logname,
                                postscc=context['posts']
                                )


@insta485.app.route('/accounts/login/')
def login():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" in flask.session:
        return flask.redirect(flask.url_for('show_index'))
    context = {"Login": "Login"}
    return flask.render_template('login.html', context=context)


@insta485.app.route('/accounts/', methods=['POST'])
def accounts():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    target = flask.request.args.get("target")
    if target is None:
        target = flask.url_for('show_index')

    if flask.request.form["operation"] == "login":
        name = flask.request.form['username']
        if name == "":
            return flask.abort(400)
        code = flask.request.form['password']
        return operation_login(name, code)

    if flask.request.form["operation"] == "create":
        fileobj = flask.request.files["file"]
        list1 = [
                flask.request.form["fullname"],
                flask.request.form["username"],
                flask.request.form["email"],
                flask.request.form["password"]]
        return operation_create(target, fileobj, list1)

    if flask.request.form["operation"] == "delete":
        if "username" not in flask.session:
            flask.abort(403)
        logname = flask.session['username']
        return operation_delete(target, logname)

    if flask.request.form["operation"] == "edit_account":
        if "username" not in flask.session:
            flask.abort(403)
        list2 = [flask.session['username'], flask.request.form["fullname"]]
        email_u = flask.request.form["email"]
        fileobj = flask.request.files["file"]
        filename = fileobj.filename
        return operation_edit(target, list2, email_u, fileobj, filename)

    if "username" not in flask.session:
        flask.abort(403)
    logname = flask.session['username']
    old = flask.request.form["password"]
    new1 = flask.request.form["new_password1"]
    new2 = flask.request.form["new_password2"]
    return operation_update(target, logname, old, new1, new2)


def operation_login(name, code):
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    connection = insta485.model.get_db()
    cur = connection.execute(
            "SELECT users.username "
            "FROM users WHERE users.username=?;", (name, ))
    var = cur.fetchall()
    if len(var) == 0:
        return flask.abort(403)
    cur = connection.execute(
        "SELECT users.password "
        "FROM users "
        "WHERE users.username = ?;", (name, ))
    var = cur.fetchall()
    old_pass = str(var[0]["password"])
    sha_value = old_pass[7:39]

    algorithm = 'sha512'
    hash_obj = hashlib.new(algorithm)
    password_salted = sha_value+str(code)
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([
                                algorithm,
                                sha_value,
                                password_hash])

    if password_db_string == old_pass:
        flask.session['username'] = name
        return flask.redirect(flask.url_for('show_index'))
    return flask.abort(403)


def operation_create(target, fileobj, list1):
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    filename = fileobj.filename
    connection = insta485.model.get_db()
    cur = connection.execute(
            "SELECT users.username "
            "FROM users WHERE users.username=?;", (list1[1], ))
    password_db_string = cur.fetchall()
    if len(password_db_string) > 0:
        flask.abort(409)
    algorithm = 'sha512'
    salt = uuid.uuid4().hex
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + str(list[3])
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, salt, password_hash])

    if (filename == "" or list1[0] == ""
            or list1[1] == "" or list1[2] == "" or password_db_string == ""):
        flask.abort(400)

    stem = uuid.uuid4().hex
    suffix = pathlib.Path(filename).suffix
    path = f"{stem}{suffix}"
    path = insta485.app.config["UPLOAD_FOLDER"] / path
    fileobj.save(path)

    connection.execute(
        "INSERT INTO users (username, "
        "fullname, email, filename, password ) "
        "VALUES (?, ?, ?, ?, ? );",
        (list1[1], list1[0], list1[2],
            filename, password_db_string, ))
    flask.session['username'] = list1[1]
    return flask.redirect(target)


def operation_delete(target, logname):
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    connection = insta485.model.get_db()
    filenames = []
    cur = connection.execute(
        "SELECT posts.filename "
        "FROM posts "
        "WHERE posts.owner = ?;", (logname, ))
    filenamedb = cur.fetchall()
    for file in filenamedb:
        filenames.append(file["filename"])
    cur = connection.execute(
        "SELECT users.filename "
        "FROM users "
        "WHERE users.username = ?;", (logname, ))
    filenamedb = cur.fetchall()
    for file in filenamedb:
        filenames.append(file["filename"])
    for file in filenames:
        if file != "":
            path = insta485.app.config["UPLOAD_FOLDER"] / file
            os.remove(path)
    cur = connection.execute(
        "DELETE FROM comments WHERE comments.owner = ?;", (logname, ))
    cur = connection.execute(
        "DELETE FROM following WHERE "
        "following.username1 = ? OR following.username2 = ?;",
        (logname, logname, ))
    cur = connection.execute(
        "DELETE FROM posts WHERE posts.owner = ?;",
                            (logname, ))
    cur = connection.execute(
        "DELETE FROM users WHERE users.username = ?;",
                            (logname, ))
    flask.session.clear()
    return flask.redirect(target)


def operation_edit(target, list2, email_u, fileobj, filename):
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    connection = insta485.model.get_db()
    logname = list2[0]
    fullname_u = list2[1]
    if (fullname_u == "" or email_u == ""):
        flask.abort(400)
    connection.execute(
        "UPDATE users "
        "SET fullname = ?, email = ? "
        "WHERE username = ? ;",
        (fullname_u, email_u, logname, ))
    if filename != "":
        cur = connection.execute(
            "SELECT users.filename "
            "FROM users WHERE users.username=?;", (logname, ))
        deleted_image = cur.fetchall()[0]["filename"]
        stem = uuid.uuid4().hex
        suffix = pathlib.Path(filename).suffix
        uuid_basename = f"{stem}{suffix}"
        path = insta485.app.config["UPLOAD_FOLDER"] / uuid_basename
        fileobj.save(path)
        connection.execute(
            "UPDATE users "
            "SET filename = ? "
            "WHERE username = ? ;",
            (uuid_basename, logname, ))
        path = insta485.app.config["UPLOAD_FOLDER"] / deleted_image
        os.remove(path)
    return flask.redirect(target)


def operation_update(target, logname, old, new1, new2):
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    connection = insta485.model.get_db()
    if (old == "" or new1 == "" or new2 == ""):
        flask.abort(400)

    cur = connection.execute(
        "SELECT users.password "
        "FROM users "
        "WHERE users.username =?; ", (logname, ))
    old_pass = cur.fetchall()
    old_pass = str(old_pass[0]["password"])
    sha_value = old_pass[7:39]
    algorithm = 'sha512'
    hash_obj = hashlib.new(algorithm)
    password_salted = sha_value + str(old)
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, sha_value, password_hash])
    if password_db_string != old_pass:
        flask.abort(403)

    if new1 != new2:
        flask.abort(401)

    algorithm = 'sha512'
    salt = uuid.uuid4().hex
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + new1
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, salt, password_hash])

    connection.execute(
        "UPDATE users "
        "SET password = ? "
        "WHERE username = ? ;", (password_db_string, logname))
    return flask.redirect(target)


@insta485.app.route('/uploads/<filename>')
def download_file(filename):
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        flask.abort(403)

    path = insta485.app.config["UPLOAD_FOLDER"] / filename
    if not Path.exists(path):
        flask.abort(404)
    return flask.send_from_directory(
                                    insta485.app.config['UPLOAD_FOLDER'],
                                    filename)


@insta485.app.route('/likes/', methods=['POST'])
def likes():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    connection = insta485.model.get_db()

    opval = flask.request.form["operation"]
    postidval = flask.request.form["postid"]

    target = flask.request.args.get("target")

    logname = flask.session['username']

    cur = connection.execute(
        "SELECT likes.likeid "
        "FROM likes "
        "WHERE likes.postid =? AND likes.owner =?;",
        (postidval, logname, ))

    likebooldb = cur.fetchall()
    likebool = bool(len(likebooldb))
    if opval == "like":
        if likebool:
            flask.abort(409)
        connection.execute(
            "INSERT INTO likes (owner, postid) "
            "VALUES (?, ?);",
            (logname, postidval, ))
    elif opval == "unlike":
        if not likebool:
            flask.abort(409)
        connection.execute(
            "DELETE FROM likes WHERE likes.postid= ? AND likes.owner = ?;",
            (postidval, logname, ))

    if target == "":
        target = flask.url_for('show_index')

    return flask.redirect(target)


@insta485.app.route('/comments/', methods=['POST'])
def comments():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    if flask.request.form["operation"] == "create":
        text = flask.request.form["text"]
        if text == "":
            flask.abort(400)
        logname = flask.session['username']
        postidval = flask.request.form["postid"]
        connection = insta485.model.get_db()
        connection.execute(
            "INSERT INTO comments (owner, postid, text) "
            "VALUES (?, ?, ?) ;", (
                logname, postidval, text, ))
        target = flask.request.args.get("target")
        if target is None:
            target = flask.url_for('show_index')
        return flask.redirect(target)

    commentid = flask.request.form["commentid"]
    connection = insta485.model.get_db()
    connection.execute(
        "DELETE FROM comments "
        "WHERE comments.commentid = ?;", (commentid, ))
    target = flask.request.args.get("target")
    if target is None:
        return flask.redirect(flask.url_for('show_index'))
    return flask.redirect(target)


@insta485.app.route('/accounts/logout/', methods=['POST'])
def logout():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    print("DEBUG Logout:", flask.session['username'])
    flask.session.clear()
    return flask.redirect(flask.url_for('login'))


@insta485.app.route('/accounts/create/', methods=['GET'])
def create():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.render_template('create.html')
    return flask.redirect('/accounts/edit/')


@insta485.app.route('/accounts/delete/', methods=['GET'])
def delete():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    username = flask.session["username"]
    return flask.render_template('delete.html', logname=username)


@insta485.app.route('/accounts/edit/', methods=['GET'])
def edit():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    context = {}
    logname = flask.session["username"]
    context["logname"] = logname
    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT users.filename, users.fullname, users.email "
        "FROM users "
        "WHERE users.username =?;", (logname, ))
    data = cur.fetchall()
    context["image"] = data[0]["filename"]
    context["email"] = data[0]["email"]
    context["fullname"] = data[0]["fullname"]
    return flask.render_template('edit.html', contextcc=context)


@insta485.app.route('/accounts/password/', methods=['GET'])
def password():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    return flask.render_template(
                                'password.html',
                                logname=flask.session["username"])


@insta485.app.route('/posts/<postid_url_slug>/', methods=['GET'])
def post_redirect(postid_url_slug):
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    context = {}
    context["postid"] = postid_url_slug
    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT posts.filename, posts.owner, posts.created "
        "FROM posts "
        "WHERE posts.postid =?;", (postid_url_slug, ))
    data = cur.fetchall()
    context["filename"] = data[0]["filename"]
    context["owner"] = data[0]["owner"]
    context["created"] = arrow.get(data[0]["created"]).humanize()
    cur = connection.execute(
        "SELECT users.filename "
        "FROM users "
        "WHERE users.username =?;", (context["owner"], ))
    data = cur.fetchall()
    context["owner_image"] = data[0]["filename"]
    cur = connection.execute(
        "SELECT likes.owner "
        "FROM likes "
        "WHERE likes.postid =?;", (postid_url_slug, ))
    data = cur.fetchall()
    context["likes"] = len(data)
    cur = connection.execute(
        "SELECT * "
        "FROM comments "
        "WHERE comments.postid =?;", (postid_url_slug, ))
    data = cur.fetchall()
    context["logname"] = flask.session["username"]
    context["comments"] = []
    for var in data:
        count = {}
        count["commentid"] = var["commentid"]
        count["owner"] = var["owner"]
        count["postid"] = var["postid"]
        count["text"] = var["text"]
        count["created"] = arrow.get(var["created"]).humanize()
        if flask.session["username"] == var["owner"]:
            count["own_comment"] = True
        else:
            count["own_comment"] = False

        context["comments"].append(count)

        cur = connection.execute(
            "SELECT likes.likeid "
            "FROM likes "
            "WHERE likes.postid =? AND likes.owner =?;",
            (postid_url_slug, context["logname"], ))

        likebooldb = cur.fetchall()
        likebool = bool(len(likebooldb))
        context["likebool"] = likebool

        if flask.session["username"] == context["owner"]:
            context["post_del"] = True
        else:
            context["post_del"] = False

    return flask.render_template('post.html', contextcc=context)


# @insta485.app.route('/posts/?target=URL', methods=['GET'])
# def posts():
#     return flask.render_template('post.html')
@insta485.app.route('/posts/', methods=['POST'])
def posts():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    operation = flask.request.form["operation"]
    logname = flask.session["username"]

    if operation == 'delete':
        postid = flask.request.form["postid"]
        connection = insta485.model.get_db()
        cur = connection.execute(
            "SELECT posts.owner "
            "FROM posts "
            "WHERE posts.postid =?;", (postid, ))
        data = cur.fetchall()
        data = data[0]["owner"]

        if logname != data:
            flask.abort(403)
        cur = connection.execute(
            "SELECT posts.filename "
            "FROM posts "
            "WHERE posts.postid =?;", (postid, ))
        filename = cur.fetchall()
        filename = filename[0]["filename"]

        cur = connection.execute(
            "DELETE FROM posts WHERE posts.postid = ?;", (postid, ))

        path = insta485.app.config["UPLOAD_FOLDER"] / filename
        os.remove(path)
        target = flask.request.args.get("target")
        if target is None:
            target = "/users/" + logname + "/"
        return flask.redirect(target)

    fileobj = flask.request.files["file"]
    filename = fileobj.filename
    if filename == "":
        flask.abort(400)
    stem = uuid.uuid4().hex
    suffix = pathlib.Path(filename).suffix
    uuid_basename = f"{stem}{suffix}"
    path = insta485.app.config["UPLOAD_FOLDER"]/uuid_basename
    fileobj.save(path)

    connection = insta485.model.get_db()
    cur = connection.execute(
        "INSERT INTO posts (filename, owner ) "
        "VALUES (?, ? );", (
            uuid_basename, logname, ))
    target = flask.request.args.get("target")
    if target is None:
        target = "/users/" + logname + "/"
    return flask.redirect(target)


@insta485.app.route('/explore/', methods=['GET'])
def explore():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    context = {}
    context["logname"] = flask.session["username"]
    context["not_following"] = []

    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT users.username "
        "FROM users ")
    data = cur.fetchall()
    all_users = set()
    for var in data:
        all_users.add(var["username"])

    following1 = set()
    following1.add(context["logname"])

    cur = connection.execute(
        "SELECT following.username2 "
        "FROM following "
        "WHERE following.username1 =?;", (context["logname"], ))
    data = cur.fetchall()
    for var in data:
        following1.add(var["username2"])
    not_following = all_users - following1
    for var in not_following:
        variable = {}
        variable["username"] = var
        cur = connection.execute(
            "SELECT users.filename "
            "FROM users "
            "WHERE users.username =?;", (variable["username"], ))
        data = cur.fetchall()
        variable["filename"] = data[0]["filename"]
        context["not_following"].append(variable)

    return flask.render_template('explore.html', contextcc=context)


@insta485.app.route('/users/<user_url_slug>/followers/', methods=['GET'])
def follower(user_url_slug):
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT users.username "
        "FROM users "
        "WHERE users.username = ?;",
        (user_url_slug, ))
    if len(cur.fetchall()) == 0:
        flask.abort(404)
    logname_u = flask.session["username"]
    followerlist = []
    cur = connection.execute(
        "SELECT following.username1 "
        "FROM following "
        "WHERE following.username2 = ?;",
        (user_url_slug, ))
    followingdb = cur.fetchall()

    for follow in followingdb:
        followingdict = {}
        username = follow["username1"]
        cur = connection.execute(
            "SELECT users.filename "
            "FROM users "
            "WHERE users.username = ?;",
            (username, ))
        followingdict["username"] = username
        followingdict["user_img_url"] = cur.fetchall()[0]["filename"]
        cur = connection.execute(
            "SELECT following.username1 "
            "FROM following "
            "WHERE following.username1 = ? AND following.username2 = ?;",
            (logname_u, username, ))
        followbool = True
        if len(cur.fetchall()) == 0:
            followbool = False
        followingdict["logname_follows_username"] = followbool
        followingdict["page_name"] = user_url_slug
        followerlist.append(followingdict)

    return flask.render_template(
                                'followers.html',
                                logname=logname_u,
                                followers=followerlist)


@insta485.app.route('/users/<user_url_slug>/following/', methods=['GET'])
def following(user_url_slug):
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT users.username "
        "FROM users "
        "WHERE users.username = ?;",
        (user_url_slug, ))
    if len(cur.fetchall()) == 0:
        flask.abort(404)

    logname_uu = flask.session["username"]
    followinglist = []
    cur = connection.execute(
        "SELECT following.username2 "
        "FROM following "
        "WHERE following.username1 = ?;",
        (user_url_slug, ))
    followingdb = cur.fetchall()

    for follow in followingdb:
        followingdict = {}
        username = follow["username2"]
        cur = connection.execute(
            "SELECT users.filename "
            "FROM users "
            "WHERE users.username = ?;",
            (username, ))
        followingdict["username"] = username
        followingdict["user_img_url"] = cur.fetchall()[0]["filename"]
        cur = connection.execute(
            "SELECT following.username2 "
            "FROM following "
            "WHERE following.username1 = ? AND following.username2 = ?;",
            (logname_uu, username, ))
        followbool = True
        if len(cur.fetchall()) == 0:
            followbool = False
        followingdict["logname_follows_username"] = followbool
        followingdict["page_name"] = user_url_slug
        followinglist.append(followingdict)
    return flask.render_template(
                                'following.html',
                                logname=logname_uu,
                                following=followinglist)


@insta485.app.route('/following/', methods=['POST'])
def following_redirect():
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    target = flask.request.args.get("target")
    connection = insta485.model.get_db()
    logname = flask.session["username"]
    username = flask.request.form["username"]
    cur = connection.execute(
        "SELECT following.username2 "
        "FROM following "
        "WHERE following.username1 = ? AND following.username2 = ?;",
        (logname, username, ))

    followbool = True
    if len(cur.fetchall()) == 0:
        followbool = False

    if flask.request.form["operation"] == "follow":
        if followbool:
            flask.abort(409)
        cur = connection.execute(
            "INSERT INTO following (username1, username2 ) "
            "VALUES (?, ?);",
            (logname, username, ))
    elif flask.request.form["operation"] == "unfollow":
        if not followbool:
            flask.abort(409)
        cur = connection.execute(
            "DELETE FROM following WHERE following.username1 = ? "
            "AND following.username2 = ?;",
            (logname, username, ))
    if target == "":
        return flask.redirect(flask.url_for('show_index'))
    return flask.redirect(target)


@insta485.app.route('/users/<user_url_slug>/', methods=['GET'])
def users(user_url_slug):
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if "username" not in flask.session:
        return flask.redirect(flask.url_for("login"))

    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT users.username, users.fullname "
        "FROM users "
        "WHERE users.username = ?;",
        (user_url_slug, ))
    userdb = cur.fetchall()
    if len(userdb) == 0:
        flask.abort(404)
    fullname_u = ""
    for user in userdb:
        fullname_u = user["fullname"]
    logname_uuu = flask.session["username"]
    cur = connection.execute(
        "SELECT following.username2 "
        "FROM following "
        "WHERE following.username1 = ? "
        "AND following.username2 = ?;",
        (logname_uuu, user_url_slug, ))
    followbool = True
    if len(cur.fetchall()) == 0:
        followbool = False
    cur = connection.execute(
        "SELECT following.username2 "
        "FROM following "
        "WHERE following.username1 = ?;",
        (user_url_slug, ))
    following_u = len(cur.fetchall())
    cur = connection.execute(
        "SELECT following.username1 "
        "FROM following "
        "WHERE following.username2 = ?;",
        (user_url_slug, ))
    follower_u = len(cur.fetchall())
    cur = connection.execute(
        "SELECT posts.postid, posts.filename "
        "FROM posts "
        "WHERE posts.owner = ?;",
        (user_url_slug, ))
    postdb = cur.fetchall()
    numposts = len(postdb)
    postlist = []
    for post in postdb:
        postdic = {}
        postdic["postid"] = post["postid"]
        postdic["img_url"] = post["filename"]
        postlist.append(postdic)
    return flask.render_template(
                                'users.html', logname=logname_uuu,
                                username=user_url_slug,
                                logname_follows_username=followbool,
                                following=following_u, followers=follower_u,
                                total_posts=numposts, posts=postlist,
                                fullname=fullname_u)
