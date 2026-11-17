import axios from "axios";
import { useAuthStore } from "../store/auth";

export const api = axios.create({
  baseURL: "/api/v1",
  timeout: 120000,
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err?.response?.data?.detail;
    const message =
      (typeof detail === "object" && detail?.message) ||
      err?.response?.data?.message ||
      err.message ||
      "请求失败";
    return Promise.reject(new Error(message));
  }
);
