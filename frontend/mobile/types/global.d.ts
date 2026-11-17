/// <reference types="@tarojs/taro" />

declare module "*.png";
declare module "*.scss";
declare module "*.css";

declare namespace NodeJS {
  interface ProcessEnv {
    TARO_ENV: "weapp" | "h5" | "rn" | string;
    TARO_APP_API_BASE?: string;
    NODE_ENV: "development" | "production";
  }
}
