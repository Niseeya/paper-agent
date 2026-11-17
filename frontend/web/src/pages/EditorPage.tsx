import { Alert, Button, List, Popconfirm, Space, Tag, Typography, Input, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import ProjectNav from "../components/ProjectNav";
import NextStepBanner from "../components/NextStepBanner";
import { api } from "../api/client";

export default function EditorPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const [activeSectionKey, setActiveSectionKey] = useState<string | null>(null);

  const { data: project } = useQuery({
    queryKey: ["project", id],
    queryFn: async () => (await api.get(`/projects/${id}`)).data.data,
  });

  const planQuery = useQuery({
    queryKey: ["writing-plan", id],
    queryFn: async () => (await api.get(`/projects/${id}/writing-plan`)).data.data,
    enabled: !!id,
  });

  const docQuery = useQuery({
    queryKey: ["document", id],
    queryFn: async () => (await api.get(`/projects/${id}/document`)).data.data,
  });

  const draftMut = useMutation({
    mutationFn: async (ch: { id: string; title: string; intent?: string }) => {
      setActiveSectionKey(ch.id || ch.title);
      return (
        await api.post(`/projects/${id}/sections/${ch.id || "main"}/drafts`, {
          section_title: ch.title,
          writing_intent: ch.intent || "",
        })
      ).data.data;
    },
    onSuccess: () => {
      message.success("本节已更新，其它章节未改动");
      qc.invalidateQueries({ queryKey: ["document", id] });
      qc.invalidateQueries({ queryKey: ["writing-plan", id] });
      qc.invalidateQueries({ queryKey: ["project", id] });
    },
    onError: (e: Error) => message.error(e.message),
    onSettled: () => setActiveSectionKey(null),
  });

  const batchMut = useMutation({
    mutationFn: async (mode: "missing" | "all") =>
      (
        await api.post(`/projects/${id}/sections/batch-drafts`, {
          max_chapters: 12,
          mode,
        })
      ).data.data,
    onSuccess: (_d, mode) => {
      message.success(mode === "all" ? "全文已按大纲重写" : "已按大纲生成缺失章节");
      qc.invalidateQueries({ queryKey: ["document", id] });
      qc.invalidateQueries({ queryKey: ["writing-plan", id] });
      qc.invalidateQueries({ queryKey: ["project", id] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const saveMut = useMutation({
    mutationFn: async (sections: any[]) =>
      (await api.put(`/projects/${id}/document`, { sections })).data.data,
    onSuccess: () => message.success("已保存"),
    onError: (e: Error) => message.error(e.message),
  });

  const sections = docQuery.data?.payload?.sections || [];
  const chapters = planQuery.data?.chapters || [];
  const missing = chapters.filter((c: any) => !c.written).length;
  const busy = draftMut.isPending || batchMut.isPending;

  return (
    <ProjectNav>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        正文写作
      </Typography.Title>
      <NextStepBanner projectId={id} next={planQuery.data?.next_step} />
      {!project?.outline_confirmed ? (
        <Alert
          type="error"
          showIcon
          message="大纲未确认，不能生成章节。"
          action={
            <Link to={`/projects/${id}/outline`}>
              <Button size="small">去确认大纲</Button>
            </Link>
          }
        />
      ) : (
        <Alert
          type="info"
          showIcon
          message={`当前 Skill：S8。按大纲逐节写作（${planQuery.data?.written_count || 0}/${planQuery.data?.total || 0}）。「重写本节」只替换当前节；「重写全文」才会覆盖全部。`}
          style={{ marginBottom: 16 }}
        />
      )}

      <Space style={{ marginBottom: 16 }} wrap>
        <Button
          type="primary"
          disabled={!project?.outline_confirmed || missing === 0 || busy}
          loading={batchMut.isPending && batchMut.variables === "missing"}
          onClick={() => batchMut.mutate("missing")}
        >
          一键写完未写章节{missing ? `（${missing}）` : ""}
        </Button>
        <Popconfirm
          title="重写全文？"
          description="将按大纲顺序覆盖所有已写章节，不可撤销（仍保留历史版本）。"
          okText="重写全文"
          cancelText="取消"
          disabled={!project?.outline_confirmed || !chapters.length || busy}
          onConfirm={() => batchMut.mutate("all")}
        >
          <Button
            danger
            disabled={!project?.outline_confirmed || !chapters.length || busy}
            loading={batchMut.isPending && batchMut.variables === "all"}
          >
            重写全文
          </Button>
        </Popconfirm>
        <Link to={`/projects/${id}/polish`}>
          <Button disabled={!sections.length}>下一步：润色</Button>
        </Link>
        <Link to={`/projects/${id}/citations`}>
          <Button disabled={!sections.length}>或直接核查</Button>
        </Link>
      </Space>

      <Typography.Title level={4}>大纲章节</Typography.Title>
      <List
        dataSource={chapters}
        locale={{ emptyText: "请先生成并确认大纲" }}
        renderItem={(ch: any) => {
          const key = ch.id || ch.title;
          return (
            <List.Item
              actions={[
                <Button
                  key="write"
                  type={ch.written ? "default" : "primary"}
                  size="small"
                  disabled={!project?.outline_confirmed || busy}
                  loading={draftMut.isPending && activeSectionKey === key}
                  onClick={() => draftMut.mutate(ch)}
                >
                  {ch.written ? "重写本节" : "生成本节"}
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={
                  <Space>
                    {ch.title}
                    {ch.written ? <Tag color="green">已写</Tag> : <Tag>待写</Tag>}
                  </Space>
                }
                description={ch.intent}
              />
            </List.Item>
          );
        }}
      />

      <Typography.Title level={4} style={{ marginTop: 28 }}>
        当前正文
      </Typography.Title>
      <List
        dataSource={sections}
        locale={{ emptyText: "暂无章节，请从上方大纲生成" }}
        renderItem={(sec: any, idx: number) => (
          <List.Item>
            <Space direction="vertical" style={{ width: "100%" }}>
              <Typography.Title level={5} style={{ margin: 0 }}>
                {sec.title}
              </Typography.Title>
              {(sec.paragraphs || []).map((p: string, i: number) => (
                <Input.TextArea
                  key={`${idx}-${i}`}
                  value={p}
                  autoSize
                  onChange={(e) => {
                    const next = sections.map((s: any, si: number) =>
                      si === idx
                        ? {
                            ...s,
                            paragraphs: s.paragraphs.map((x: string, pi: number) =>
                              pi === i ? e.target.value : x
                            ),
                          }
                        : s
                    );
                    qc.setQueryData(["document", id], {
                      ...docQuery.data,
                      payload: { ...(docQuery.data?.payload || {}), sections: next },
                    });
                  }}
                />
              ))}
              {(sec.citations || []).length ? (
                <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                  引用：
                  {(sec.citations || [])
                    .map((c: any) => `${c.citation_id} ${c.title} p.${c.page_start}`)
                    .join("；")}
                </Typography.Paragraph>
              ) : null}
            </Space>
          </List.Item>
        )}
      />
      <Button
        style={{ marginTop: 12 }}
        loading={saveMut.isPending}
        onClick={() => saveMut.mutate(sections)}
        disabled={!sections.length}
      >
        保存正文版本
      </Button>
    </ProjectNav>
  );
}
