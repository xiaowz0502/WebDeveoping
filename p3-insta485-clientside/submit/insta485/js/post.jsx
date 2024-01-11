import React from "react";
import PropTypes from "prop-types";
import moment from "moment";

class Post extends React.Component {
  /* Display image and post owner of a single post
   */
  constructor(props) {
    // Initialize mutable state
    super(props);
    this.state = {
      imgUrl: "",
      owner: "",
      ownerShowUrl: "",
      ownerImgUrl: "",
      postShowUrl: "",
      lognameLikesThis: "",
      postid: "",
      created: "",
      comments: [],
      likenum: "",
      value: "",
      likeid: "",
    };
    this.like_helper = this.like_helper.bind(this);
    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.double_click = this.double_click.bind(this);
    this.commentDeleteHelper = this.commentDeleteHelper.bind(this);
  }

  componentDidMount() {
    // This line automatically assigns this.props.url to the const variable url
    const { url } = this.props;
    // Call REST API to get the post's information
    fetch(url, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((data) => {
        // console.log(data)
        let likeidlist = "";
        let likeidval = "";
        if (data.likes.lognameLikesThis) {
          likeidlist = data.likes.url.split("/");
          likeidval = likeidlist[likeidlist.length - 2];
        }
        this.setState({
          comments: data.comments,
          created: moment
            .utc(data.created)
            .local()
            .format("YYYY-MM-DD HH:mm:ss"),
          imgUrl: data.imgUrl,
          owner: data.owner,
          ownerShowUrl: data.ownerShowUrl,
          ownerImgUrl: data.ownerImgUrl,
          postShowUrl: data.postShowUrl,
          lognameLikesThis: data.likes.lognameLikesThis,
          postid: data.postid,
          liketext: data.likes.lognameLikesThis ? "unlike" : "like",
          likenum: data.likes.numLikes,
          likeid: likeidval,
        });
      })
      .catch((error) => console.log(error));
  }

  handleChange(event) {
    this.setState({ value: event.target.value });
  }

  handleSubmit(event) {
    event.preventDefault();
    const { postid: commenturl1 } = this.state;
    // const commenturl1 = "/api/v1/comments/?postid=" + this.state.postid;
    const commenturl = `/api/v1/comments/?postid=${commenturl1}`;
    const { value: datahelper } = this.state;
    const data1 = { text: datahelper };
    fetch(commenturl, {
      method: "POST", // or 'PUT'
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data1),
    })
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((data) => {
        const temp = {};
        temp.commentid = data.commentid;
        temp.lognameOwnsThis = data.lognameOwnsThis;
        temp.owner = data.owner;
        temp.ownerShowUrl = data.ownerShowUrl;
        temp.text = data.text;
        temp.url = data.url;

        this.setState((prevState) => ({
          comments: [...prevState.comments, temp],
        }));
        this.setState({ value: "" });
      })
      .catch((error) => console.log(error));
  }

  commentDeleteHelper(event, commentid) {
    const deleteurl = `/api/v1/comments/${commentid}/`;
    fetch(deleteurl, { method: "DELETE", credentials: "same-origin" }).then(
      (response) => {
        if (!response.ok) throw Error(response.statusText);
      }
    );
    this.setState((prevState) => ({
      comments: prevState.comments.filter(
        (item) => item.commentid !== commentid
      ),
    }));
  }

  like_helper() {
    const { postid: helper } = this.state;
    const { lognameLikesThis: helper2 } = this.state;
    const likeurl = `/api/v1/likes/?postid=${helper}`;
    if (!helper2) {
      fetch(likeurl, { method: "POST", credentials: "same-origin" })
        .then((response) => {
          if (!response.ok) throw Error(response.statusText);
          return response.json();
        })
        .then((data) => {
          this.setState((prevState) => ({
            likenum: prevState.likenum + 1,
            lognameLikesThis: true,
            liketext: "unlike",
            likeid: data.likeid,
          }));
        })
        .catch((error) => console.log(error));
    } else {
      const { likeid: likeidhelper } = this.state;
      const deletelikeurl = `/api/v1/likes/${likeidhelper}/`;
      fetch(deletelikeurl, {
        method: "DELETE",
        credentials: "same-origin",
      }).catch((error) => console.log(error));
      this.setState((prevState) => ({
        likenum: prevState.likenum - 1,
        lognameLikesThis: false,
        liketext: "like",
      }));
    }
  }

  double_click() {
    const { postid: helper } = this.state;
    const { lognameLikesThis: helper3 } = this.state;
    if (!helper3) {
      const likeurl = `/api/v1/likes/?postid=${helper}`;
      fetch(likeurl, { method: "POST", credentials: "same-origin" })
        .then((response) => {
          if (!response.ok) throw Error(response.statusText);
          return response.json();
        })
        .catch((error) => console.log(error));
      this.setState({ lognameLikesThis: true, liketext: "unlike" });
      this.setState((prevState) => ({ likenum: prevState.likenum + 1 }));
    }
  }

  render() {
    // This line automatically assigns this.state.imgUrl to the const variable imgUrl
    // and this.state.owner to the const variable owner
    const {
      imgUrl: ImgUrl,
      owner: Owner,
      ownerShowUrl: OwnerShowUrl,
      ownerImgUrl: OwnerImgUrl,
      postShowUrl: PostShowUrl,
      liketext: Liketext,
      created: Created,
      comments: Comments,
      likenum: Likenum,
      value: Value,
    } = this.state;
    // Render post image and post owner
    let likeword;
    if (Likenum === 1) {
      likeword = "like";
    } else {
      likeword = "likes";
    }

    return (
      <div>
        <p>
          <a href={OwnerShowUrl}>
            <img alt="post1pic" src={OwnerImgUrl} width="30" height="30" />
          </a>
          <a href={OwnerShowUrl}>{Owner}</a>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
          <a href={PostShowUrl}>{moment(Created).fromNow()}</a>
        </p>
        <img
          src={ImgUrl}
          onDoubleClick={this.double_click}
          alt="1"
          width="600"
          height="499"
        />
        <button
          type="button"
          className="like-unlike-button"
          onClick={this.like_helper}
        >
          <p>{Liketext}</p>
        </button>
        <p>
          {Likenum} {likeword}{" "}
        </p>
        <div>
          {Comments.map((x) =>
            x.lognameOwnsThis === true ? (
              <p key={x.commentid}>
                <a href={x.ownerShowUrl}>{x.owner}</a>&nbsp;&nbsp;&nbsp;{x.text}
                &nbsp;&nbsp;&nbsp;
                <button
                  type="button"
                  className="delete-comment-button"
                  onClick={(event) =>
                    this.commentDeleteHelper(event, x.commentid)
                  }
                >
                  <p>Delete comment</p>
                </button>
              </p>
            ) : (
              <p key={x.commentid}>
                <a href={x.ownerShowUrl}>{x.owner}</a>&nbsp;&nbsp;&nbsp;{x.text}
              </p>
            )
          )}
        </div>

        <form className="comment-form" onSubmit={this.handleSubmit}>
          <input type="text" value={Value} onChange={this.handleChange} />
        </form>
      </div>
    );
  }
}

Post.propTypes = {
  url: PropTypes.string.isRequired,
};
export default Post;
