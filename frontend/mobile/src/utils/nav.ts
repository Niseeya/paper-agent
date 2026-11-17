import Taro from "@tarojs/taro";
import { useAuthStore } from "../store/auth";

export function requireAuth(): boolean {
  const { token, hydrated, hydrate } = useAuthStore.getState();
  if (!hydrated) hydrate();
  const t = useAuthStore.getState().token;
  if (!t) {
    Taro.reLaunch({ url: "/pages/login/index" });
    return false;
  }
  return true;
}

export function goProject(id: string, page?: string) {
  const path = page
    ? `/pages/${page}/index?id=${encodeURIComponent(id)}`
    : `/pages/project/index?id=${encodeURIComponent(id)}`;
  Taro.navigateTo({ url: path });
}

export function goHome() {
  Taro.reLaunch({ url: "/pages/home/index" });
}
