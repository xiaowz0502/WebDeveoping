import React from "react";
import PropTypes from "prop-types";
import InfiniteScroll from "react-infinite-scroll-component";
import Post from "./post";

class Loopin extends React.Component {
  constructor(props) {
    super(props);
    this.state = { results: [], nexturl: "" };
    this.nextfetch = this.nextfetch.bind(this);
  }

  componentDidMount() {
    const { url: helper } = this.props;
    fetch(helper, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((data) => {
        this.setState({
          results: data.results,
          nexturl: data.next,
        });
      })
      .catch((error) => console.log(error));
  }

  nextfetch() {
    const { nexturl } = this.state;
    fetch(nexturl, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((data) => {
        this.setState((prevState) => ({
          results: prevState.results.concat(data.results),
          nexturl: data.next,
        }));
      })
      .catch((error) => console.log(error));
  }

  render() {
    const { nexturl, results } = this.state;
    return (
      <InfiniteScroll
        next={this.nextfetch}
        dataLength={results.length}
        hasMore={nexturl !== ""}
        loader={<h4>Loading...</h4>}
      >
        {results.map((x) => (
          <Post url={x.url} key={x.postid} />
        ))}
      </InfiniteScroll>
    );
  }
}

// pullDownToRefresh={true}
// refreshFunction={this.refreshfunc}>

Loopin.propTypes = {
  url: PropTypes.string.isRequired,
};
export default Loopin;
