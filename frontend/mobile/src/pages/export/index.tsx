import { useState } from "react";
import { View, Text } from "@tarojs/components";
import Button from "../../components/TapButton";
import Taro, { useDidShow, useRouter } from "@tarojs/taro";
import { api } from "../../services/client";
import FlowNav from "../../components/FlowNav";
import { getApiBase, toast } from "../../utils/config";
import { useAuthStore } from "../../store/auth";
import { requireAuth } from "../../utils/nav";

export default function ExportPage() {
  const { id = "" } = useRouter().params;
  const [mode, setMode] = useState<"draft" | "final">("draft");
  const [files, setFiles] = useState<Record<string, string> | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!requireAuth() || !id) return;
    try {
      const res = await api.get(`/projects/${id}/exports/latest`);
      setFiles(res.data?.payload?.files || null);
    } catch {
      setFiles(null);
    }
  }

  useDidShow(load);

  async function run() {
    setBusy(true);
    Taro.showLoading({ title: "导出中…" });
    try {
      const res = await api.post(`/projects/${id}/exports`, { mode });
      setFiles(res.data?.payload?.files || res.data?.files || null);
      toast(mode === "final" ? "定稿导出成功" : "草稿导出成功", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "导出失败");
    } finally {
      Taro.hideLoading();
      setBusy(false);
    }
  }

  async function download(fmt: string) {
    const token = useAuthStore.getState().token;
    const url = `${getApiBase()}/projects/${id}/exports/download?fmt=${fmt}`;
    try {
      if (process.env.TARO_ENV === "h5") {
        const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
        if (!res.ok) throw new Error("下载失败");
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `export.${fmt}`;
        a.click();
        return;
      }
      const dl = await Taro.downloadFile({
        url,
        header: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (dl.statusCode >= 200 && dl.statusCode < 300) {
        await Taro.openDocument({ filePath: dl.tempFilePath, showMenu: true });
      } else {
        throw new Error("下载失败");
      }
    } catch (e) {
      toast(e instanceof Error ? e.message : "下载失败");
    }
  }

  return (
    <View className="page">
      <FlowNav projectId={id} />
      <View className="card">
        <View className="title">导出（S10）</View>
        <View className="subtitle">定稿需引用核查全部通过；失败可改草稿导出</View>
        <View className="row">
          <Text
            className={`tag ${mode === "draft" ? "ok" : ""}`}
            onClick={() => setMode("draft")}
          >
            草稿
          </Text>
          <Text
            className={`tag ${mode === "final" ? "ok" : ""}`}
            onClick={() => setMode("final")}
          >
            定稿
          </Text>
        </View>
        <Button className="btn" disabled={busy} onClick={run}>
          开始导出
        </Button>
        <Button
          className="btn secondary"
          onClick={() =>
            Taro.navigateTo({ url: `/pages/citations/index?id=${encodeURIComponent(id)}` })
          }
        >
          查看核查
        </Button>
      </View>
      {files ? (
        <View className="card">
          <View className="subtitle">下载</View>
          {Object.keys(files).map((fmt) => (
            <Button key={fmt} className="btn secondary" onClick={() => download(fmt)}>
              打开 {fmt.toUpperCase()}
            </Button>
          ))}
        </View>
      ) : null}
    </View>
  );
}
