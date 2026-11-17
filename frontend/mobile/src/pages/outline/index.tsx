import { useState } from "react";
import { View, Text, Textarea, Input } from "@tarojs/components";
import Button from "../../components/TapButton";
import { useDidShow, useRouter } from "@tarojs/taro";
import { api } from "../../services/client";
import FlowNav from "../../components/FlowNav";
import { toast } from "../../utils/config";
import { requireAuth } from "../../utils/nav";

type Node = {
  id: string;
  level: number;
  title: string;
  intent: string;
  children?: Node[];
};

function flatten(nodes: Node[] = [], acc: { node: Node; path: string }[] = [], prefix = "") {
  nodes.forEach((n, i) => {
    const path = prefix ? `${prefix}.${i}` : `${i}`;
    acc.push({ node: n, path });
    if (n.children?.length) flatten(n.children, acc, path);
  });
  return acc;
}

export default function OutlinePage() {
  const { id = "" } = useRouter().params;
  const [goal, setGoal] = useState("");
  const [nodes, setNodes] = useState<Node[]>([]);
  const [version, setVersion] = useState<number | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);

  async function loadLatest() {
    if (!requireAuth() || !id) return;
    try {
      const res = await api.get(`/projects/${id}/outlines/latest`);
      const payload = res.data?.payload || res.data;
      setNodes(payload?.chapters || payload?.nodes || []);
      setVersion(res.data?.version ?? payload?.version ?? null);
      setConfirmed(!!res.data?.confirmed || !!payload?.confirmed);
    } catch {
      // 尚无大纲
    }
  }

  useDidShow(loadLatest);

  async function generate() {
    if (!goal.trim()) {
      toast("请填写研究目标");
      return;
    }
    setLoading(true);
    try {
      const res = await api.post(`/projects/${id}/outlines`, { research_goal: goal.trim() });
      const payload = res.data?.payload || res.data;
      setNodes(payload?.chapters || payload?.nodes || []);
      setVersion(res.data?.version ?? null);
      setConfirmed(false);
      toast("大纲已生成", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  }

  async function confirm() {
    if (version == null) {
      toast("请先生成大纲");
      return;
    }
    setLoading(true);
    try {
      await api.post(`/projects/${id}/outlines/${version}/confirm`);
      setConfirmed(true);
      toast("大纲已确认", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "确认失败");
    } finally {
      setLoading(false);
    }
  }

  const flat = flatten(nodes);

  return (
    <View className="page">
      <FlowNav projectId={id} />
      <View className="card">
        <View className="title">大纲（S7）</View>
        <View className="subtitle">
          {confirmed ? "已确认，可批量写作" : "未确认前只能单段试写，不能定稿"}
        </View>
        <Textarea
          className="input"
          style={{ minHeight: 100 }}
          placeholder="研究目标"
          value={goal}
          onInput={(e) => setGoal(e.detail.value)}
        />
        <Button className={`btn ${loading ? "disabled" : ""}`} onClick={generate} disabled={loading}>
          生成大纲
        </Button>
        {!confirmed && version != null ? (
          <Button className="btn secondary" onClick={confirm} disabled={loading}>
            确认大纲
          </Button>
        ) : null}
      </View>
      <View className="card">
        {flat.length === 0 ? (
          <Text className="muted">尚无大纲</Text>
        ) : (
          flat.map(({ node }) => (
            <View key={node.id} className="list-item" style={{ paddingLeft: (node.level - 1) * 24 }}>
              <View style={{ fontWeight: 600 }}>
                L{node.level} {node.title}
              </View>
              <Text className="muted">{node.intent}</Text>
            </View>
          ))
        )}
      </View>
    </View>
  );
}
