import Taro from "@tarojs/taro";

/** Tab / 整页切换：H5 改 hash，小程序用 reLaunch */
export function switchPage(path: string) {
  const url = path.startsWith("/") ? path : `/${path}`;
  if (process.env.TARO_ENV === "h5" && typeof window !== "undefined") {
    const hash = `#${url}`;
    if (window.location.hash !== hash) {
      window.location.hash = hash;
    }
    return;
  }
  Taro.reLaunch({ url }).catch(() => {
    Taro.redirectTo({ url }).catch(() => {
      Taro.navigateTo({ url }).catch(() => {
        Taro.showToast({ title: "无法打开该页", icon: "none" });
      });
    });
  });
}
