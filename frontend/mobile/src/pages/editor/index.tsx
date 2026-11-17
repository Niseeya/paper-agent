import { useState } from "react";
import { View, Text } from "@tarojs/components";
import Button from "../../components/TapButton";
import Taro, { useDidShow, useRouter } from "@tarojs/taro";
import { api } from "../../services/client";
import FlowNav from "../../components/FlowNav";
import { toast } from "../../utils/config";
import { requireAuth } from "../../utils/nav";

export default function EditorPage() {
  const { id = "" } = useRouter().params;
  const [project, setProject] = useState<any>(null);
  const [chapters, setChapters] = useState<any[]>([]);
  const [sections, setSections] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!requireAuth() || !id) return;
    try {
      const [p, plan, doc] = await Promise.all([
        api.get(`/projects/${id}`),
        api.get(`/projects/${id}/writing-plan`),
        api.get(`/projects/${id}/document`),
      ]);
      setProject(p.data);
      setChapters(plan.data?.chapters || []);
      setSections(doc.data?.payload?.sections || []);
    } catch (e) {
      toast(e instanceof Error ? e.message : "加载失败");
    }
  }

  useDidShow(load);

  async function draftOne(ch: { id: string; title: string; intent?: string }) {
    if (!project?.outline_confirmed) {
      toast("请先确认大纲");
      return;
    }
    setBusy(true);
    Taro.showLoading({ title: "生成本节…" });
    try {
      await api.post(`/projects/${id}/sections/${ch.id || "main"}/drafts`, {
        section_title: ch.title,
        writing_intent: ch.intent || "",
      });
      toast("本节已更新", "success");
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "生成失败");
    } finally {
      Taro.hideLoading();
      setBusy(false);
    }
  }

  async function batch(mode: "missing" | "all") {
    if (!project?.outline_confirmed) {
      toast("请先确认大纲");
      return;
    }
    setBusy(true);
    Taro.showLoading({ title: mode === "all" ? "重写全文…" : "生成缺失…" });
    try {
      await api.post(`/projects/${id}/sections/batch-drafts`, { max_chapters: 12, mode });
      toast(mode === "all" ? "全文已重写" : "缺失章节已生成", "success");
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "失败");
    } finally {
      Taro.hideLoading();
      setBusy(false);
    }
  }

  return (
    <View className="page">
      <FlowNav projectId={id} />
      <View className="card">
        <View className="title">章节写作（S8）</View>
        <View className="subtitle">正式引用仅限库内已索引论文；未确认大纲不可批量生成</View>
        <Button className="btn secondary" disabled={busy} onClick={() => batch("missing")}>
          按大纲生成缺失章节
        </Button>
        <Button className="btn" disabled={busy} onClick={() => batch("all")}>
          重写全文
        </Button>
      </View>
      <View className="card">
        <View className="subtitle">大纲章节</View>
        {chapters.map((ch) => (
          <View key={ch.id || ch.title} className="list-item">
            <View style={{ fontWeight: 600 }}>
              {ch.title} {ch.written ? <Text className="tag ok">已写</Text> : <Text className="tag warn">未写</Text>}
            </View>
            <Text className="muted">{ch.intent}</Text>
            <Button className="btn secondary" disabled={busy} onClick={() => draftOne(ch)}>
              重写本节
            </Button>
          </View>
        ))}
      </View>
      <View className="card">
        <View className="subtitle">正文预览</View>
        {sections.length === 0 ? (
          <Text className="muted">尚无正文</Text>
        ) : (
          sections.map((s: any, i: number) => (
            <View key={s.id || i} className="list-item">
              <View style={{ fontWeight: 600 }}>{s.title || `节 ${i + 1}`}</View>
              <Text className="muted">{(s.content || s.text || "").slice(0, 400)}</Text>
            </View>
          ))
        )}
      </View>
    </View>
  );
}
