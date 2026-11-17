import { useState } from "react";
import { View, Text, Textarea } from "@tarojs/components";
import Button from "../../components/TapButton";
import { useRouter } from "@tarojs/taro";
import { api } from "../../services/client";
import FlowNav from "../../components/FlowNav";
import { toast } from "../../utils/config";
import { requireAuth } from "../../utils/nav";

type Hit = {
  paper_id: string;
  title: string;
  authors: string[];
  year?: number;
  snippet: string;
  page_start?: number;
  score: number;
};

export default function SearchPage() {
  const { id = "" } = useRouter().params;
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState("all");
  const [hits, setHits] = useState<Hit[]>([]);
  const [loading, setLoading] = useState(false);

  async function search() {
    if (!requireAuth()) return;
    if (!query.trim()) {
      toast("请输入查询");
      return;
    }
    setLoading(true);
    try {
      const res = await api.post(`/projects/${id}/retrievals`, {
        query: query.trim(),
        mode: "hybrid",
        language,
        top_k: 8,
      });
      setHits(res.data?.data?.papers || res.data?.papers || []);
    } catch (e) {
      toast(e instanceof Error ? e.message : "检索失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <View className="page-app no-tab">
      <FlowNav projectId={id} />
      <View className="page-body">
        <View className="group" style={{ padding: 28 }}>
          <View className="hero-title">文献检索</View>
          <View className="hint">Skill S2 · 仅检索公用知识库已索引论文</View>
          <Textarea
            className="textarea-field"
            placeholder="例如：国产青春电影的怀旧叙事"
            value={query}
            onInput={(e) => setQuery(e.detail.value)}
          />
          <View className="status-row">
            {[
              ["all", "全部"],
              ["zh", "中文"],
              ["en", "英文"],
            ].map(([v, label]) => (
              <Text
                key={v}
                className={`tag ${language === v ? "ok" : ""}`}
                onClick={() => setLanguage(v)}
              >
                {label}
              </Text>
            ))}
          </View>
          <Button className={`btn ${loading ? "disabled" : ""}`} onClick={search} disabled={loading}>
            混合检索
          </Button>
        </View>

        <View className="group">
          <View className="group-hd">检索结果 · {hits.length}</View>
          {hits.length === 0 ? (
            <View className="empty">尚无结果</View>
          ) : (
            hits.map((h) => (
              <View key={h.paper_id + h.snippet?.slice(0, 12)} className="cell">
                <View className="cell-title">{h.title}</View>
                <View className="muted" style={{ marginBottom: 8 }}>
                  {(h.authors || []).slice(0, 3).join("、")}
                  {h.year ? ` · ${h.year}` : ""}
                  {h.page_start != null ? ` · p.${h.page_start}` : ""}
                </View>
                <Text className="muted">{h.snippet}</Text>
              </View>
            ))
          )}
        </View>
      </View>
    </View>
  );
}
