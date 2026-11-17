import { useState } from "react";
import { View, Text, Textarea } from "@tarojs/components";
import Button from "../../components/TapButton";
import Taro, { useDidShow, useRouter } from "@tarojs/taro";
import { api } from "../../services/client";
import FlowNav from "../../components/FlowNav";
import { toast } from "../../utils/config";
import { requireAuth } from "../../utils/nav";

const LEVELS = [
  { value: "light", label: "轻度" },
  { value: "academic", label: "学术" },
  { value: "deep", label: "深度" },
];

export default function PolishPage() {
  const { id = "" } = useRouter().params;
  const [level, setLevel] = useState("academic");
  const [req, setReq] = useState("");
  const [payload, setPayload] = useState<any>(null);
  const [version, setVersion] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!requireAuth() || !id) return;
    try {
      const res = await api.get(`/projects/${id}/polishes/latest`);
      setPayload(res.data?.payload || null);
      setVersion(res.data?.version ?? null);
    } catch {
      setPayload(null);
    }
  }

  useDidShow(load);

  async function run() {
    setBusy(true);
    Taro.showLoading({ title: "润色中…" });
    try {
      const res = await api.post(`/projects/${id}/polishes`, {
        level,
        user_request: req,
      });
      setPayload(res.data?.payload || res.data);
      setVersion(res.data?.version ?? null);
      toast("请对照确认", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "润色失败");
    } finally {
      Taro.hideLoading();
      setBusy(false);
    }
  }

  async function confirm() {
    if (version == null) {
      toast("请先润色");
      return;
    }
    setBusy(true);
    try {
      await api.post(`/projects/${id}/polishes/${version}/confirm`);
      toast("已写入正文", "success");
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "确认失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View className="page">
      <FlowNav projectId={id} />
      <View className="card">
        <View className="title">润色</View>
        <View className="subtitle">确认前不替换正文。降重请求会被拒绝。不改数字与引用。</View>
        <View className="row">
          {LEVELS.map((l) => (
            <Text
              key={l.value}
              className={`tag ${level === l.value ? "ok" : ""}`}
              onClick={() => setLevel(l.value)}
            >
              {l.label}
            </Text>
          ))}
        </View>
        <Textarea
          className="input"
          style={{ minHeight: 80 }}
          placeholder="可选：润色要求（勿要求降重）"
          value={req}
          onInput={(e) => setReq(e.detail.value)}
        />
        <Button className="btn" disabled={busy} onClick={run}>
          开始润色
        </Button>
        {version != null ? (
          <Button className="btn secondary" disabled={busy} onClick={confirm}>
            确认写入正文
          </Button>
        ) : null}
      </View>
      {payload ? (
        <View className="card">
          <View className="subtitle">对照预览</View>
          <Text className="muted">
            {(payload.polished_text || payload.after || JSON.stringify(payload)).slice(0, 800)}
          </Text>
        </View>
      ) : null}
    </View>
  );
}
