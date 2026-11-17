import { useState } from "react";
import { View, Text, Input, Switch } from "@tarojs/components";
import Button from "../../components/TapButton";
import Taro, { useDidShow } from "@tarojs/taro";
import { api, uploadPaper } from "../../services/client";
import { useAuthStore } from "../../store/auth";
import { usePaperCartStore } from "../../store/paperCart";
import BottomTab from "../../components/BottomTab";
import { toast } from "../../utils/config";
import { requireAuth } from "../../utils/nav";

type Paper = {
  id: string;
  title: string;
  authors: string[];
  year?: number;
  source_type: string;
  direction?: string;
};

type DirectionStat = {
  direction: string;
  count: number;
  keywords: string[];
};

export default function LibraryPage() {
  const [q, setQ] = useState("");
  const [direction, setDirection] = useState<string | null>(null);
  const [items, setItems] = useState<Paper[]>([]);
  const [dirs, setDirs] = useState<DirectionStat[]>([]);
  const [total, setTotal] = useState(0);
  const [corpusTotal, setCorpusTotal] = useState(0);
  const [rights, setRights] = useState(false);
  const [loading, setLoading] = useState(false);
  const hydrateCart = usePaperCartStore((s) => s.hydrate);
  const add = usePaperCartStore((s) => s.add);
  const remove = usePaperCartStore((s) => s.remove);
  const has = usePaperCartStore((s) => s.has);
  usePaperCartStore((s) => s.items);

  async function loadDirs() {
    try {
      const res = await api.get("/papers/directions");
      setDirs(res.data?.directions || []);
      setCorpusTotal(res.data?.total || 0);
    } catch {
      /* ignore */
    }
  }

  async function load(query = q, dir = direction) {
    if (!requireAuth()) return;
    try {
      const params = [
        "page=1",
        "page_size=20",
        query ? `q=${encodeURIComponent(query)}` : "",
        dir ? `direction=${encodeURIComponent(dir)}` : "",
      ]
        .filter(Boolean)
        .join("&");
      const res = await api.get(`/papers?${params}`);
      setItems(res.data?.items || []);
      setTotal(res.data?.total || 0);
    } catch (e) {
      toast(e instanceof Error ? e.message : "加载失败");
    }
  }

  useDidShow(() => {
    useAuthStore.getState().hydrate();
    hydrateCart();
    loadDirs();
    load();
  });

  function selectDirection(d: string | null) {
    setDirection(d);
    load(q, d);
  }

  function toggleCart(p: Paper) {
    if (has(p.id)) {
      remove(p.id);
      toast("已移出备选");
      return;
    }
    const r = add({
      id: p.id,
      title: p.title,
      authors: p.authors,
      year: p.year,
    });
    toast(r.ok ? "已加入备选" : r.reason || "失败", r.ok ? "success" : "none");
  }

  async function chooseUpload() {
    if (!rights) {
      toast("请先确认有权上传并同意进入公用库");
      return;
    }
    try {
      const pick = await Taro.chooseMessageFile({
        count: 1,
        type: "file",
        extension: ["pdf"],
      }).catch(async () => {
        return Taro.chooseMedia({ count: 1, mediaType: ["file" as any] }) as any;
      });

      const file = pick.tempFiles?.[0];
      const path = file?.path || file?.tempFilePath;
      const size = file?.size || 0;
      if (!path) {
        toast("未选择文件");
        return;
      }
      if (size > 30 * 1024 * 1024) {
        toast("超过 30MB，请改用 Web 上传");
        return;
      }
      setLoading(true);
      Taro.showLoading({ title: "上传入库…" });
      const res = await uploadPaper(path, true);
      Taro.hideLoading();
      toast(`已入库：${res.data?.title || "成功"}`, "success");
      loadDirs();
      load();
    } catch (e) {
      Taro.hideLoading();
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("chooseMessageFile") || msg.includes("not support")) {
        toast("当前端上传受限，请用 Web 上传 PDF");
      } else {
        toast(msg || "上传失败");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <View className="page-app">
      <View className="page-body">
        <View className="topbar">
          <View>
            <View className="topbar-title">知识库</View>
            <View className="topbar-sub">
              {direction ? `本方向 ${total} 篇` : `已索引 ${total || corpusTotal} 篇`}
            </View>
          </View>
          <Text className="link-btn" onClick={() => Taro.redirectTo({ url: "/pages/tools/index" })}>
            备选分析
          </Text>
        </View>

        <View className="group" style={{ padding: "20px 28px" }}>
          <View className="muted" style={{ marginBottom: 12 }}>
            研究方向筛选
          </View>
          <View className="status-row">
            <Text
              className={`tag ${!direction ? "ok" : ""}`}
              onClick={() => selectDirection(null)}
            >
              全部（{corpusTotal}）
            </Text>
            {dirs.map((d) => (
              <Text
                key={d.direction}
                className={`tag ${direction === d.direction ? "ok" : ""}`}
                onClick={() => selectDirection(d.direction)}
              >
                {d.direction}（{d.count}）
              </Text>
            ))}
          </View>
        </View>

        <View className="group" style={{ padding: "20px 28px 8px" }}>
          <View className="field" style={{ marginBottom: 12 }}>
            <Input
              className="field-input"
              placeholder="搜索题名 / 关键词"
              placeholderClass="field-placeholder"
              value={q}
              onInput={(e) => setQ(e.detail.value)}
              onConfirm={() => load(q)}
            />
          </View>
          <Button className="btn secondary" onClick={() => load(q)}>
            搜索
          </Button>
          <View className="switch-row">
            <Switch checked={rights} onChange={(e) => setRights(!!e.detail.value)} />
            <Text className="muted" style={{ flex: 1 }}>
              我有权上传，并同意进入公用知识库
            </Text>
          </View>
          <Button className={`btn ${loading ? "disabled" : ""}`} onClick={chooseUpload} disabled={loading}>
            上传 PDF
          </Button>
          <View className="hint">小程序超限请改用 Web 上传</View>
        </View>

        <View className="group">
          <View className="group-hd">文献列表</View>
          {items.length === 0 ? (
            <View className="empty">{direction ? "该方向下暂无文章" : "暂无结果"}</View>
          ) : (
            items.map((p) => {
              const inCart = has(p.id);
              return (
                <View key={p.id} className="cell">
                  <View className="cell-title">{p.title}</View>
                  <View className="muted" style={{ marginBottom: 10 }}>
                    {(p.authors || []).slice(0, 3).join("、")}
                    {p.year ? ` · ${p.year}` : ""}
                  </View>
                  <View className="cell-meta" style={{ marginBottom: 12 }}>
                    <Text className="tag">{p.source_type}</Text>
                    {p.direction ? <Text className="tag">{p.direction}</Text> : null}
                  </View>
                  <Text className={`link-btn ${inCart ? "warn" : ""}`} onClick={() => toggleCart(p)}>
                    {inCart ? "移出备选" : "加入备选"}
                  </Text>
                </View>
              );
            })
          )}
        </View>
      </View>
      <BottomTab active="library" />
    </View>
  );
}
