/**
 * Webpack configuration file for building and serving the ORCA Document Query
 * single-page application web client.
 *
 * This configuration supports both development and production modes, optimizing
 * the output based on the environment. It handles SCSS compilation, HTML
 * processing, asset management, and various optimizations.
 *
 * Features:
 * - **Mode**: Automatically switches between development and production modes.
 * - **Entry Point**: Main JavaScript file located at `./www/src/js/main.js`.
 * - **Output**: Bundles JavaScript into `./www/dist` directory.
 * - **DevServer**: Serves content at `localhost:9000`.
 * - **Loaders**:
 *   - Babel: Transpiles JavaScript files for compatibility with older browsers.
 *   - SCSS: Compiles SCSS files to CSS and extracts them to separate files.
 *   - HTML: Processes HTML files to bundle them with the appropriate assets.
 *   - Images: Copies PNG icons from `./www/src/img/icons` to output directory.
 * - **Plugins**:
 *   - `CleanWebpackPlugin`: Cleans the output directory before each build.
 *   - `MiniCssExtractPlugin`: Extracts CSS into separate files.
 *   - `HTMLWebpackPlugin`: Generates an HTML file and injects bundled assets.
 *   - `CopyWebpackPlugin`: Copies extra favicons to output directory.
 * - **Optimization**:
 *   - In production mode, minimizes JavaScript, CSS, and HTML files, and
 *     removes console logs using Terser, CSSMinimizer, and HtmlMinimizer.
 * - **Ignore Warnings**: Silences Bootstrap v5.3 depreciation warnings.
 *
 * Environment Variables:
 * - `NODE_ENV`: Determines the mode ("development" or "production").
 *
 * @module webpack.config.js
 */

const { CleanWebpackPlugin } = require("clean-webpack-plugin");
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
    new CleanWebpackPlugin(),
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
