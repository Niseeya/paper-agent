import { Alert, Button, Form, Input, List, Space, Tag, Typography, message } from "antd";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuthStore } from "../store/auth";
import { usePaperCartStore } from "../store/paperCart";

async function invokeSkill(skill_code: string, input: Record<string, unknown>) {
  const res = await api.post("/skills/invoke", { skill_code, input });
  const envelope = res.data;
  const skill = envelope?.data;
  if (envelope?.code !== "OK" || skill?.status !== "succeeded") {
    throw new Error(envelope?.message || skill?.error || `${skill_code} 执行失败`);
  }
  return skill.data;
}

/**
 * 独立研究工具页：对比 / 研究空白。
 * 方向浏览已迁到公用知识库筛选；备选篮用于对比。
 */
export default function ResearchToolsPage() {
  const [compare, setCompare] = useState<any>(null);
  const [gaps, setGaps] = useState<any>(null);
  const [hydrated, setHydrated] = useState(() => useAuthStore.persist.hasHydrated());
  const token = useAuthStore((s) => s.token);
  const items = usePaperCartStore((s) => s.items);
  const remove = usePaperCartStore((s) => s.remove);
  const clear = usePaperCartStore((s) => s.clear);
  const cartIds = useMemo(() => items.map((x) => x.id), [items]);

  useEffect(() => {
    const unsub = useAuthStore.persist.onFinishHydration(() => setHydrated(true));
    if (useAuthStore.persist.hasHydrated()) setHydrated(true);
    return unsub;
  }, []);

  const compareMut = useMutation({
    mutationFn: (paper_ids: string[]) => invokeSkill("S4", { paper_ids }),
    onSuccess: (d) => {
      setCompare(d);
      message.success("对比完成");
    },
    onError: (e: Error) => message.error(e.message),
  });

  const gapMut = useMutation({
    mutationFn: (body: { research_status: string; paper_ids: string[] }) => invokeSkill("S6", body),
    onSuccess: (d) => {
      setGaps(d);
      message.success("研究空白已生成");
    },
    onError: (e: Error) => message.error(e.message),
  });

  if (!hydrated) {
    return <Typography.Paragraph>加载中…</Typography.Paragraph>;
  }
  if (!token) {
    return <Alert type="error" showIcon message="未登录，请先登录后再打开研究工具。" />;
  }

  return (
    <div>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        研究工具
      </Typography.Title>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message={
          <>
            本页独立于成稿主流程。按方向浏览文章请到{" "}
            <Link to="/library">公用知识库</Link>
            ；此处用备选篮做对比与研究空白。
          </>
        }
      />

      <Typography.Title level={4}>备选篮（{items.length}/8）</Typography.Title>
      {items.length ? (
        <List
          size="small"
          bordered
          style={{ marginBottom: 16, maxWidth: 860 }}
          dataSource={items}
          renderItem={(p) => (
            <List.Item
              actions={[
                <Button key="rm" type="link" danger onClick={() => remove(p.id)}>
                  移除
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={p.title}
                description={
                  <Space wrap>
                    <Typography.Text copyable={{ text: p.id }} type="secondary" style={{ fontSize: 12 }}>
                      {p.id}
                    </Typography.Text>
                    <Tag>{p.year || "年份未识别"}</Tag>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      ) : (
        <Typography.Paragraph type="secondary">
          备选篮为空。请到公用知识库或项目检索页点击「加入备选」。
        </Typography.Paragraph>
      )}
      <Space style={{ marginBottom: 24 }} wrap>
        <Button
          type="primary"
          disabled={items.length < 2}
          loading={compareMut.isPending}
          onClick={() => compareMut.mutate(cartIds)}
        >
          用备选篮论文对比分析（S4）
        </Button>
        <Button disabled={!items.length} onClick={() => clear()}>
          清空备选篮
        </Button>
      </Space>

      <Typography.Title level={4}>多篇对比（S4）</Typography.Title>
      <Typography.Paragraph type="secondary">也可手动粘贴编码（至少 2 个）。</Typography.Paragraph>
      <Form
        layout="inline"
        initialValues={{ ids: cartIds.join(",") }}
        key={cartIds.join(",")}
        onFinish={(v) =>
          compareMut.mutate(
            String(v.ids || "")
              .split(/[\s,，]+/)
              .map((x: string) => x.trim())
              .filter(Boolean)
          )
        }
      >
        <Form.Item name="ids" rules={[{ required: true, message: "填入至少 2 个 paper_id" }]}>
          <Input style={{ width: 480 }} placeholder="paper_id1,paper_id2" />
        </Form.Item>
        <Button htmlType="submit" loading={compareMut.isPending}>
          对比
        </Button>
      </Form>
      {compare?.matrix ? (
        <List
          style={{ marginTop: 12 }}
          dataSource={compare.matrix}
          renderItem={(row: any) => (
            <List.Item>
              <List.Item.Meta
                title={row.dimension}
                description={row.cells
                  ?.map((c: any) => `${String(c.paper_id || "").slice(0, 8)}…: ${c.value}`)
                  .join(" | ")}
              />
            </List.Item>
          )}
        />
      ) : null}

      <Typography.Title level={4} style={{ marginTop: 28 }}>
        研究空白（S6）
      </Typography.Title>
      <Form
        layout="vertical"
        onFinish={(v) =>
          gapMut.mutate({
            research_status: v.research_status,
            paper_ids: cartIds,
          })
        }
      >
        <Form.Item name="research_status" rules={[{ required: true }]}>
          <Input.TextArea rows={3} placeholder="简述研究现状，可含“不足/尚未/空白”" />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={gapMut.isPending}>
          生成建议空白{cartIds.length ? `（附带备选 ${cartIds.length} 篇）` : ""}
        </Button>
      </Form>
      {gaps?.gaps ? (
        <List
          style={{ marginTop: 12 }}
          dataSource={gaps.gaps}
          renderItem={(g: any) => (
            <List.Item>
              <List.Item.Meta
                title={`${g.type} · ${g.evidence_status}`}
                description={g.statement}
              />
            </List.Item>
          )}
        />
      ) : null}
    </div>
  );
}
