const path = require("path");

module.exports = {
  entry: "./www/src/js/main.js",

  output: {
    filename: "bundle.js",
    path: path.resolve(__dirname, "www/dist/js"),
  },
  mode: "development",
  devtool: "source-map",
};
