import { PropsWithChildren } from "react";
import { useLaunch } from "@tarojs/taro";
import "./app.scss";

function App({ children }: PropsWithChildren) {
  useLaunch(() => {
    // no-op
  });
  return children;
}

export default App;
