import { defineConfig, type UserConfigExport } from "@tarojs/cli";
import devConfig from "./dev";
import prodConfig from "./prod";

export default defineConfig<"vite">(async (merge) => {
  const baseConfig: UserConfigExport<"vite"> = {
    projectName: "paper-agent-mobile",
    date: "2026-11-17",
    designWidth: 750,
    deviceRatio: {
      640: 2.34 / 2,
      750: 1,
      375: 2,
      828: 1.81 / 2,
    },
    sourceRoot: "src",
    outputRoot: "dist",
    plugins: ["@tarojs/plugin-framework-react"],
    defineConstants: {},
    copy: { patterns: [], options: {} },
    framework: "react",
    compiler: "vite",
    mini: {
      postcss: {
        pxtransform: { enable: true, config: {} },
        cssModules: {
          enable: false,
          config: {
            namingPattern: "module",
            generateScopedName: "[name]__[local]___[hash:base64:5]",
          },
        },
      },
    },
    h5: {
      publicPath: "/",
      staticDirectory: "static",
      esnextModules: ["@tarojs"],
      miniCssExtractPluginOption: {
        ignoreOrder: true,
        filename: "css/[name].[hash].css",
        chunkFilename: "css/[name].[chunkhash].css",
      },
      postcss: {
        autoprefixer: { enable: true, config: {} },
        cssModules: {
          enable: false,
          config: {
            namingPattern: "module",
            generateScopedName: "[name]__[local]___[hash:base64:5]",
          },
        },
      },
      // 只代理 /api/v1，避免把源码目录 src/api/* 也转到后端导致白屏
      devServer: {
        host: "0.0.0.0",
        port: 10086,
        proxy: {
          "/api/v1": {
            target: "http://127.0.0.1:8000",
            changeOrigin: true,
          },
        },
      },
    },
  };

  if (process.env.NODE_ENV === "development") {
    return merge({}, baseConfig, devConfig);
  }
  return merge({}, baseConfig, prodConfig);
});
