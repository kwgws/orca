const CopyWebpackPlugin = require("copy-webpack-plugin");
const HTMLWebpackPlugin = require("html-webpack-plugin");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin");
const TerserPlugin = require("terser-webpack-plugin");
const HtmlMinimizerPlugin = require("html-minimizer-webpack-plugin");
const path = require("path");

const isDev = process.env.NODE_ENV !== "production";

module.exports = {
  mode: isDev ? "development" : "production",
  entry: "./www/src/js/main.js",
  devtool: isDev ? "source-map" : false,
  output: {
    filename: `js/bundle${isDev ? "" : ".[contenthash:8].min"}.js`,
    path: path.resolve(__dirname, "./www/dist"),
    assetModuleFilename: "[name][ext]",
    clean: true,
  },
  ignoreWarnings: [
    { message: /node_modules\/sass-loader\/dist\/cjs\.js/ },
    { message: /node_modules\/bootstrap/ },
  ],
  devServer: {
    static: {
      directory: path.resolve(__dirname, "./www/dist"),
    },
    port: 9000,
    compress: true,
    hot: true,
    watchFiles: ["./www/src/index.html", "./www/src/scss/*.scss", "./www/src/js/*.js"],
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: "babel-loader",
          options: { presets: ["@babel/preset-env"] },
        },
      },
      {
        test: /\.scss$/,
        use: [
          MiniCssExtractPlugin.loader,
          "css-loader",
          {
            loader: "postcss-loader",
            options: { postcssOptions: { plugins: ["autoprefixer"] } },
          },
          "sass-loader",
        ],
      },
      {
        test: /\.html$/,
        use: ["html-loader"],
      },
      {
        test: /\.(png)$/, // copy favicons
        include: path.resolve(__dirname, "./www/src/img/icons"),
        type: "asset/resource",
        generator: { filename: "img/icons/[name][ext]" },
      },
    ],
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: `css/styles${isDev ? "" : ".[contenthash:8].min"}.css`,
    }),
    new HTMLWebpackPlugin({
      template: "./www/src/index.html",
    }),
    new CopyWebpackPlugin({
      patterns: [
        {
          // icons from site manifest need to be copied separately
          from: path.resolve(__dirname, "./www/src/img/icons/android*.png"),
          to: path.resolve(__dirname, "./www/dist/img/icons/[name][ext]"),
        },
      ],
    }),
  ],
  optimization: {
    minimize: !isDev,
    minimizer: isDev
      ? [] // no min in debug
      : [
          new TerserPlugin({
            terserOptions: { compress: { drop_console: true } },
          }),
          new CssMinimizerPlugin(),
          new HtmlMinimizerPlugin(),
        ],
  },
  resolve: {
    extensions: [".js", ".scss"],
  },
};
