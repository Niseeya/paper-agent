import { useState } from "react";
import { View, Text, Textarea } from "@tarojs/components";
import Button from "../../components/TapButton";
import Taro, { useDidShow } from "@tarojs/taro";
import { api } from "../../services/client";
import BottomTab from "../../components/BottomTab";
import { usePaperCartStore } from "../../store/paperCart";
import { toast } from "../../utils/config";
import { requireAuth } from "../../utils/nav";

async function invokeSkill(skill_code: string, input: Record<string, unknown>) {
  const envelope = await api.post("/skills/invoke", { skill_code, input });
  const skill = envelope?.data;
  if (envelope?.code !== "OK" || skill?.status !== "succeeded") {
    throw new Error(envelope?.message || skill?.error || `${skill_code} 执行失败`);
  }
  return skill.data;
}

export default function ToolsPage() {
  const items = usePaperCartStore((s) => s.items);
  const remove = usePaperCartStore((s) => s.remove);
  const clear = usePaperCartStore((s) => s.clear);
  const hydrate = usePaperCartStore((s) => s.hydrate);
  const [compare, setCompare] = useState<any>(null);
  const [gaps, setGaps] = useState<any>(null);
  const [statusText, setStatusText] = useState("");
  const [busy, setBusy] = useState<"compare" | "gap" | null>(null);

  useDidShow(() => {
    if (!requireAuth()) return;
    hydrate();
  });

  const cartIds = items.map((x) => x.id);

  async function runCompare() {
    if (cartIds.length < 2) {
      toast("备选篮至少 2 篇");
      return;
    }
    setBusy("compare");
    Taro.showLoading({ title: "对比中…" });
    try {
      const d = await invokeSkill("S4", { paper_ids: cartIds });
      setCompare(d);
      toast("对比完成", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "对比失败");
    } finally {
      Taro.hideLoading();
      setBusy(null);
    }
  }

  async function runGap() {
    if (!statusText.trim()) {
      toast("请填写研究现状");
      return;
    }
    setBusy("gap");
    Taro.showLoading({ title: "分析空白…" });
    try {
      const d = await invokeSkill("S6", {
        research_status: statusText.trim(),
        paper_ids: cartIds,
      });
      setGaps(d);
      toast("研究空白已生成", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "生成失败");
    } finally {
      Taro.hideLoading();
      setBusy(null);
    }
  }

  return (
    <View className="page-app">
      <View className="page-body">
        <View className="topbar">
          <View>
            <View className="topbar-title">研究工具</View>
            <View className="topbar-sub">对比 · 研究空白（独立于成稿主流程）</View>
          </View>
        </View>

        <View className="hint">
          方向浏览在「知识库」筛选；此处用备选篮做 S4 对比与 S6 研究空白。
        </View>

        <View className="group">
          <View className="group-hd">备选篮（{items.length}/8）</View>
          {items.length === 0 ? (
            <View className="empty">到知识库或检索结果点「加入备选」</View>
          ) : (
            items.map((p) => (
              <View key={p.id} className="cell">
                <View className="cell-title">{p.title}</View>
                <View className="muted" style={{ marginBottom: 10 }}>
                  {(p.authors || []).slice(0, 2).join("、")}
                  {p.year ? ` · ${p.year}` : ""}
                </View>
                <Text className="link-btn warn" onClick={() => remove(p.id)}>
                  移出
                </Text>
              </View>
            ))
          )}
        </View>

        <View className="action-block">
          <Button
            className={`btn ${busy === "compare" ? "disabled" : ""}`}
            disabled={busy !== null || items.length < 2}
            onClick={runCompare}
          >
            多篇对比（S4）
          </Button>
          <Button className="btn secondary" disabled={!items.length} onClick={() => clear()}>
            清空备选篮
          </Button>
        </View>

        {compare?.matrix ? (
          <View className="group">
            <View className="group-hd">对比矩阵</View>
            {compare.matrix.map((row: any, i: number) => (
              <View key={i} className="cell">
                <View className="cell-title">{row.dimension}</View>
                <Text className="muted">
                  {row.cells
                    ?.map((c: any) => `${String(c.paper_id || "").slice(0, 8)}: ${c.value}`)
                    .join(" · ")}
                </Text>
              </View>
            ))}
          </View>
        ) : null}

        <View className="group" style={{ padding: 28 }}>
          <View className="hero-title" style={{ fontSize: 32 }}>
            研究空白（S6）
          </View>
          <Textarea
            className="textarea-field"
            placeholder="简述研究现状，可含「不足 / 尚未 / 空白」"
            value={statusText}
            onInput={(e) => setStatusText(e.detail.value)}
          />
          <Button
            className={`btn ${busy === "gap" ? "disabled" : ""}`}
            disabled={busy !== null}
            onClick={runGap}
          >
            生成建议空白{cartIds.length ? `（附带备选 ${cartIds.length} 篇）` : ""}
          </Button>
        </View>

        {gaps?.gaps ? (
          <View className="group">
            <View className="group-hd">候选空白</View>
            {gaps.gaps.map((g: any, i: number) => (
              <View key={i} className="cell">
                <View className="cell-meta" style={{ marginBottom: 8 }}>
                  <Text className="tag">{g.type}</Text>
                  <Text className="tag warn">{g.evidence_status}</Text>
                </View>
                <Text>{g.statement}</Text>
              </View>
            ))}
          </View>
        ) : null}
      </View>
      <BottomTab active="tools" />
    </View>
  );
}
