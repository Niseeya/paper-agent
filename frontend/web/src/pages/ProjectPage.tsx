import { Alert, Button, Progress, Space, Steps, Tag, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import ProjectNav from "../components/ProjectNav";
import NextStepBanner from "../components/NextStepBanner";
import { useAuthStore } from "../store/auth";

const statusLabel: Record<string, string> = {
  draft: "草稿",
  preparing: "资料准备",
  outline_pending: "大纲待确认",
  writing: "写作中",
  checking: "核验中",
  exportable: "可导出",
};

const FLOW = [
  { key: "search", title: "检索文献", desc: "在公用知识库查找证据" },
  { key: "outline", title: "确认大纲", desc: "生成并人工确认章节结构" },
  { key: "editor", title: "章节写作", desc: "按大纲生成带真实引用的正文" },
  { key: "polish", title: "润色确认", desc: "对照润色，确认前不替换" },
  { key: "citations", title: "引用核查", desc: "L1/L2 与逻辑问题" },
  { key: "export", title: "导出成稿", desc: "草稿或定稿 DOCX/PDF" },
];

export default function ProjectPage() {
  const { id } = useParams();
  const role = useAuthStore((s) => s.user?.role);
  const isAdmin = role === "admin";

  const { data, isLoading } = useQuery({
    queryKey: ["project", id],
    queryFn: async () => (await api.get(`/projects/${id}`)).data.data,
  });
  const planQuery = useQuery({
    queryKey: ["writing-plan", id],
    queryFn: async () => (await api.get(`/projects/${id}/writing-plan`)).data.data,
    enabled: !!id,
  });

  const next = planQuery.data?.next_step;
  const flowStep = planQuery.data?.flow_step ?? next?.step ?? 0;
  const written = planQuery.data?.written_count || 0;
  const total = planQuery.data?.total || 0;

  return (
    <ProjectNav>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        {data?.title || "项目"}
      </Typography.Title>
      {isLoading ? (
        <Typography.Text>加载中…</Typography.Text>
      ) : (
        <>
          <Space style={{ marginBottom: 16 }} wrap>
            <Tag>{statusLabel[data?.status] || data?.status}</Tag>
            <Tag>{data?.paper_type}</Tag>
            {data?.outline_confirmed ? <Tag color="green">大纲已确认</Tag> : <Tag>大纲未确认</Tag>}
            {total > 0 ? (
              <Tag color="blue">
                成稿 {written}/{total}
              </Tag>
            ) : null}
          </Space>

          <NextStepBanner projectId={id} next={next} />

          <Typography.Title level={4}>成稿流程</Typography.Title>
          <Steps
            current={Math.min(flowStep, FLOW.length - 1)}
            style={{ marginBottom: 24, maxWidth: 960 }}
            items={FLOW.map((s) => ({
              title: s.title,
              description: s.desc,
            }))}
          />

          {total > 0 ? (
            <Progress
              percent={Math.round((written / Math.max(total, 1)) * 100)}
              style={{ maxWidth: 480, marginBottom: 20 }}
            />
          ) : null}

          <Space wrap style={{ marginBottom: 24 }}>
            {next?.path ? (
              <Link to={`/projects/${id}/${next.path}`}>
                <Button type="primary" size="large">
                  {next.label}
                </Button>
              </Link>
            ) : null}
            {flowStep === 0 ? (
              <Link to={`/projects/${id}/outline`}>
                <Button size="large">跳过检索，直接生成大纲</Button>
              </Link>
            ) : null}
            <Link to="/library">
              <Button>公用知识库</Button>
            </Link>
          </Space>

          <Alert
            type="info"
            showIcon
            style={{ maxWidth: 720 }}
            message="按左侧流程逐步完成即可成稿。对比、方向分类与研究空白不在主流程内。"
            action={
              <Button
                size="small"
                onClick={() => window.open("/tools/analysis", "_blank", "noopener,noreferrer")}
              >
                打开研究工具
              </Button>
            }
          />

          {isAdmin ? (
            <Alert
              style={{ marginTop: 16, maxWidth: 720 }}
              type="warning"
              showIcon
              message="管理员可在管理后台使用测试入口与项目删除。"
              action={
                <Link to="/admin">
                  <Button size="small">前往管理后台</Button>
                </Link>
              }
            />
          ) : null}
        </>
      )}
    </ProjectNav>
  );
}
