import { useState } from "react";
import { View, Text } from "@tarojs/components";
import Button from "../../components/TapButton";
import Taro, { useDidShow, useRouter } from "@tarojs/taro";
import { api } from "../../services/client";
import FlowNav from "../../components/FlowNav";
import { STATUS_LABEL, toast } from "../../utils/config";
import { requireAuth } from "../../utils/nav";

export default function ProjectPage() {
  const { id = "" } = useRouter().params;
  const [project, setProject] = useState<any>(null);
  const [plan, setPlan] = useState<any>(null);

  async function load() {
    if (!requireAuth() || !id) return;
    try {
      const [p, w] = await Promise.all([
        api.get(`/projects/${id}`),
        api.get(`/projects/${id}/writing-plan`).catch(() => null),
      ]);
      setProject(p.data);
      setPlan(w?.data || null);
    } catch (e) {
      toast(e instanceof Error ? e.message : "加载失败");
    }
  }

  useDidShow(load);

  const next = plan?.next_step;
  const written = plan?.written_count || 0;
  const total = plan?.total || 0;

  return (
    <View className="page-app no-tab">
      <FlowNav projectId={id} />
      <View className="page-body">
        <View className="group" style={{ padding: 28 }}>
          <View className="hero-title">{project?.title || "项目"}</View>
          <View className="status-row">
            <Text className="tag">{STATUS_LABEL[project?.status] || project?.status || "…"}</Text>
            <Text className="tag">{project?.paper_type}</Text>
            {project?.outline_confirmed ? (
              <Text className="tag ok">大纲已确认</Text>
            ) : (
              <Text className="tag warn">大纲未确认</Text>
            )}
            {total > 0 ? (
              <Text className="tag">
                成稿 {written}/{total}
              </Text>
            ) : null}
          </View>
          <View className="hint">
            按顶部步骤完成：检索 → 大纲 → 写作 → 润色 → 核查 → 导出
          </View>
          {next?.path ? (
            <Button
              className="btn"
              onClick={() =>
                Taro.navigateTo({
                  url: `/pages/${next.path}/index?id=${encodeURIComponent(id)}`,
                })
              }
            >
              {next.label || "继续下一步"}
            </Button>
          ) : null}
          <Button
            className="btn secondary"
            onClick={() =>
              Taro.navigateTo({ url: `/pages/outline/index?id=${encodeURIComponent(id)}` })
            }
          >
            跳过检索，直接生成大纲
          </Button>
          <Button className="btn ghost" onClick={() => Taro.reLaunch({ url: "/pages/home/index" })}>
            返回项目列表
          </Button>
        </View>
      </View>
    </View>
  );
}
