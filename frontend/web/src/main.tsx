import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import "./styles.css";

const qc = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          token: {
            colorPrimary: "#1f4b3f",
            colorBgLayout: "#f3efe6",
            fontFamily: '"Source Han Sans SC", "Noto Sans SC", "PingFang SC", sans-serif',
            borderRadius: 4,
          },
        }}
      >
        <App />
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
