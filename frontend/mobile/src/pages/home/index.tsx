import { useState } from "react";
import { View, Text, Input, Picker } from "@tarojs/components";
import Button from "../../components/TapButton";
import Taro, { useDidShow } from "@tarojs/taro";
import { api } from "../../services/client";
import { useAuthStore } from "../../store/auth";
import BottomTab from "../../components/BottomTab";
import { STATUS_LABEL, toast } from "../../utils/config";
import { requireAuth, goProject } from "../../utils/nav";

type Project = {
  id: string;
  title: string;
  paper_type: string;
  status: string;
  outline_confirmed: boolean;
};

const TYPES = ["综述", "实证研究", "设计与实现"];

export default function HomePage() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [items, setItems] = useState<Project[]>([]);
  const [title, setTitle] = useState("");
  const [typeIdx, setTypeIdx] = useState(0);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  async function load() {
    if (!requireAuth()) return;
    try {
      const res = await api.get("/projects");
      setItems(res.data?.items || []);
    } catch (e) {
      toast(e instanceof Error ? e.message : "加载失败");
    }
  }

  useDidShow(() => {
    useAuthStore.getState().hydrate();
    load();
  });

  async function create() {
    if (!title.trim()) {
      toast("请输入题目");
      return;
    }
    setLoading(true);
    try {
      const res = await api.post("/projects", {
        title: title.trim(),
        paper_type: TYPES[typeIdx],
      });
      toast("已创建", "success");
      setTitle("");
      setShowCreate(false);
      goProject(res.data.id);
    } catch (e) {
      toast(e instanceof Error ? e.message : "创建失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <View className="page-app">
      <View className="page-body">
        <View className="topbar">
          <View>
            <View className="topbar-title">我的项目</View>
            <View className="topbar-sub">{user?.display_name || user?.username || "用户"}</View>
          </View>
          <View className="topbar-actions">
            <Text
              className="link-btn warn"
              onClick={() => {
                logout();
                Taro.reLaunch({ url: "/pages/login/index" });
              }}
            >
              退出
            </Text>
          </View>
        </View>

        <View className="group">
          <View className="group-hd">全部项目 · {items.length}</View>
          {items.length === 0 ? (
            <View className="empty">还没有项目，点下方新建开始成稿</View>
          ) : (
            items.map((p) => (
              <View key={p.id} className="cell cell-arrow" onClick={() => goProject(p.id)}>
                <View className="cell-title">{p.title}</View>
                <View className="cell-meta">
                  <Text className="tag">{STATUS_LABEL[p.status] || p.status}</Text>
                  <Text className="tag">{p.paper_type}</Text>
                  {p.outline_confirmed ? <Text className="tag ok">大纲已确认</Text> : null}
                </View>
              </View>
            ))
          )}
        </View>

        {!showCreate ? (
          <View className="action-block">
            <Button className="btn" onClick={() => setShowCreate(true)}>
              新建项目
            </Button>
          </View>
        ) : (
          <View className="group">
            <View className="group-hd">新建项目</View>
            <View style={{ padding: "8px 28px 28px" }}>
              <View className="field">
                <Input
                  className="field-input"
                  placeholder="输入论文题目"
                  placeholderClass="field-placeholder"
                  value={title}
                  onInput={(e) => setTitle(e.detail.value)}
                />
              </View>
              <Picker
                mode="selector"
                range={TYPES}
                value={typeIdx}
                onChange={(e) => setTypeIdx(Number(e.detail.value))}
              >
                <View className="field" style={{ color: "#152822" }}>
                  类型：{TYPES[typeIdx]}
                </View>
              </Picker>
              <Button className={`btn ${loading ? "disabled" : ""}`} onClick={create} disabled={loading}>
                创建并进入流程
              </Button>
              <Button className="btn ghost" onClick={() => setShowCreate(false)}>
                取消
              </Button>
            </View>
          </View>
        )}
      </View>
      <BottomTab active="home" />
    </View>
  );
}
