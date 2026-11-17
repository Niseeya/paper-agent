import { useState } from "react";
import { View, Text } from "@tarojs/components";
import Button from "../../components/TapButton";
import Taro, { useDidShow, useRouter } from "@tarojs/taro";
import { api } from "../../services/client";
import FlowNav from "../../components/FlowNav";
import { toast } from "../../utils/config";
import { requireAuth } from "../../utils/nav";

export default function CitationsPage() {
  const { id = "" } = useRouter().params;
  const [payload, setPayload] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!requireAuth() || !id) return;
    try {
      const res = await api.get(`/projects/${id}/citation-checks/latest`);
      setPayload(res.data?.payload || null);
    } catch {
      setPayload(null);
    }
  }

  useDidShow(load);

  async function run() {
    setBusy(true);
    Taro.showLoading({ title: "S9 核查中…" });
    try {
      const res = await api.post(`/projects/${id}/citation-checks`);
      setPayload(res.data?.payload || res.data);
      toast("核查完成", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "核查失败");
    } finally {
      Taro.hideLoading();
      setBusy(false);
    }
  }

  const passed = !!payload?.passed;
  const citationIssues = payload?.citation_issues || payload?.issues || [];
  const logicIssues = payload?.logic_issues || [];

  return (
    <View className="page">
      <FlowNav projectId={id} />
      <View className="card">
        <View className="title">引用与逻辑核查（S9）</View>
        <View className="subtitle">L1 元数据一致 · L2 证据页码绑定 · 未通过不能定稿</View>
        <Button className="btn" disabled={busy} onClick={run}>
          运行核查
        </Button>
        {payload ? (
          <View className="row" style={{ marginTop: 16 }}>
            {passed ? (
              <Text className="tag ok">全部通过，可定稿</Text>
            ) : (
              <Text className="tag warn">存在未通过项</Text>
            )}
          </View>
        ) : null}
        {passed ? (
          <Button
            className="btn secondary"
            onClick={() =>
              Taro.navigateTo({ url: `/pages/export/index?id=${encodeURIComponent(id)}` })
            }
          >
            下一步：导出
          </Button>
        ) : null}
      </View>
      <View className="card">
        <View className="subtitle">引用问题</View>
        {citationIssues.length === 0 ? (
          <Text className="muted">无</Text>
        ) : (
          citationIssues.map((it: any, i: number) => (
            <View key={i} className="list-item">
              <Text>{it.sentence || it.message || JSON.stringify(it)}</Text>
            </View>
          ))
        )}
        <View className="subtitle" style={{ marginTop: 16 }}>
          逻辑问题
        </View>
        {logicIssues.length === 0 ? (
          <Text className="muted">无</Text>
        ) : (
          logicIssues.map((it: any, i: number) => (
            <View key={i} className="list-item">
              <Text>{it.sentence || it.message || JSON.stringify(it)}</Text>
            </View>
          ))
        )}
      </View>
    </View>
  );
}
