import Taro from "@tarojs/taro";
import { useAuthStore } from "../store/auth";
import { getApiBase } from "../utils/config";

type RequestOpts = {
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  data?: Record<string, unknown> | string | ArrayBuffer;
  header?: Record<string, string>;
  timeout?: number;
};

function extractMessage(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;
  const d = data as Record<string, unknown>;
  const detail = d.detail;
  if (detail && typeof detail === "object") {
    const m = (detail as Record<string, unknown>).message;
    if (typeof m === "string") return m;
  }
  if (typeof d.message === "string") return d.message;
  if (typeof detail === "string") return detail;
  return fallback;
}

export async function request<T = any>(path: string, opts: RequestOpts = {}): Promise<T> {
  const token = useAuthStore.getState().token;
  const header: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.header || {}),
  };
  if (token) header.Authorization = `Bearer ${token}`;

  const url = `${getApiBase()}${path.startsWith("/") ? path : `/${path}`}`;

  try {
    const res = await Taro.request({
      url,
      method: opts.method || "GET",
      data: opts.data,
      header,
      timeout: opts.timeout ?? 120000,
    });

    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.data as T;
    }
    throw new Error(extractMessage(res.data, `请求失败(${res.statusCode})`));
  } catch (e) {
    if (e instanceof Error) throw e;
    throw new Error("网络异常");
  }
}

export const api = {
  get: <T = any>(path: string) => request<T>(path, { method: "GET" }),
  post: <T = any>(path: string, data?: Record<string, unknown>) =>
    request<T>(path, { method: "POST", data }),
  put: <T = any>(path: string, data?: Record<string, unknown>) =>
    request<T>(path, { method: "PUT", data }),
  delete: <T = any>(path: string) => request<T>(path, { method: "DELETE" }),
};

/** multipart 上传（PDF） */
export async function uploadPaper(filePath: string, rightsConfirmed: boolean) {
  const token = useAuthStore.getState().token;
  const url = `${getApiBase()}/papers/upload`;
  const res = await Taro.uploadFile({
    url,
    filePath,
    name: "file",
    formData: {
      rights_confirmed: String(rightsConfirmed),
      embed: "true",
    },
    header: token ? { Authorization: `Bearer ${token}` } : {},
    timeout: 180000,
  });
  let body: any = res.data;
  try {
    body = typeof res.data === "string" ? JSON.parse(res.data) : res.data;
  } catch {
    /* keep raw */
  }
  if (res.statusCode >= 200 && res.statusCode < 300) return body;
  throw new Error(extractMessage(body, `上传失败(${res.statusCode})`));
}
