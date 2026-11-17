import { Button, Form, Input, List, Space, Typography, message } from "antd";
import { useMutation } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { useState } from "react";
import ProjectNav from "../components/ProjectNav";
import { api } from "../api/client";

export default function AnalysisPage() {
  const { id } = useParams();
  const [compare, setCompare] = useState<any>(null);
  const [classify, setClassify] = useState<any>(null);
  const [gaps, setGaps] = useState<any>(null);

  const compareMut = useMutation({
    mutationFn: async (paper_ids: string[]) =>
      (
        await api.post("/skills/invoke", {
          skill_code: "S4",
          input: { paper_ids },
        })
      ).data.data,
    onSuccess: (d) => setCompare(d.data),
    onError: (e: Error) => message.error(e.message),
  });

  const classifyMut = useMutation({
    mutationFn: async () =>
      (await api.post("/skills/invoke", { skill_code: "S5", input: {} })).data.data,
    onSuccess: (d) => setClassify(d.data),
    onError: (e: Error) => message.error(e.message),
  });

  const gapMut = useMutation({
    mutationFn: async (research_status: string) =>
      (
        await api.post("/skills/invoke", {
          skill_code: "S6",
          input: { research_status, paper_ids: [] },
        })
      ).data.data,
    onSuccess: (d) => setGaps(d.data),
    onError: (e: Error) => message.error(e.message),
  });

  return (
    <ProjectNav>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        研究分析
      </Typography.Title>
      <Typography.Paragraph type="secondary">项目 {id} · Skill S4 / S5 / S6</Typography.Paragraph>

      <Typography.Title level={4}>多篇对比（S4）</Typography.Title>
      <Form
        layout="inline"
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
                  ?.map((c: any) => `${c.paper_id.slice(0, 8)}…: ${c.value}`)
                  .join(" | ")}
              />
            </List.Item>
          )}
        />
      ) : null}

      <Space style={{ marginTop: 28 }}>
        <Button loading={classifyMut.isPending} onClick={() => classifyMut.mutate()}>
          方向分类（S5）
        </Button>
      </Space>
      {classify?.directions ? (
        <List
          style={{ marginTop: 12 }}
          dataSource={classify.directions}
          renderItem={(d: any) => (
            <List.Item>
              <List.Item.Meta
                title={d.direction}
                description={`${d.titles?.slice(0, 3).join("；") || ""}（${d.paper_ids?.length || 0} 篇）`}
              />
            </List.Item>
          )}
        />
      ) : null}

      <Typography.Title level={4} style={{ marginTop: 28 }}>
        研究空白（S6）
      </Typography.Title>
      <Form layout="vertical" onFinish={(v) => gapMut.mutate(v.research_status)}>
        <Form.Item name="research_status" rules={[{ required: true }]}>
          <Input.TextArea rows={3} placeholder="简述研究现状，可含“不足/尚未/空白”" />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={gapMut.isPending}>
          生成建议空白
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
    </ProjectNav>
  );
}
