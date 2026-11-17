import Taro from "@tarojs/taro";

/**
 * API 根路径（含 /api/v1）。
 * - H5 开发：留空，走 Vite 代理 `/api` → localhost:8000
 * - 微信小程序 / 真机：设为可访问的后端，如 http://192.168.x.x:8000/api/v1
 */
export function getApiBase(): string {
  const fromEnv = (process.env.TARO_APP_API_BASE || "").trim();
  if (fromEnv) return fromEnv.replace(/\/$/, "");

  if (process.env.TARO_ENV === "h5") {
    return "/api/v1";
  }

  // 小程序默认指向本机；请在微信开发者工具勾选「不校验合法域名」
  return "http://127.0.0.1:8000/api/v1";
}

export function toast(title: string, icon: "none" | "success" | "error" = "none") {
  Taro.showToast({ title: title.slice(0, 40), icon, duration: 2500 });
}

export const STATUS_LABEL: Record<string, string> = {
  draft: "草稿",
  preparing: "资料准备",
  outline_pending: "大纲待确认",
  writing: "写作中",
  checking: "核验中",
  exportable: "可导出",
};
