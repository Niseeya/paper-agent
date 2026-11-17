import { Button, Form, Input, List, Radio, Space, Tag, Typography, message } from "antd";
import { useMutation } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { useState } from "react";
import { api } from "../api/client";
import ProjectNav from "../components/ProjectNav";
import { usePaperCartStore } from "../store/paperCart";

type Hit = {
  paper_id: string;
  title: string;
  authors: string[];
  year?: number;
  snippet: string;
  page_start?: number;
  page_end?: number;
  score: number;
  source: string;
};

export default function SearchPage() {
  const { id } = useParams();
  const [hits, setHits] = useState<Hit[]>([]);
  const [meta, setMeta] = useState<Record<string, unknown> | null>(null);
  const add = usePaperCartStore((s) => s.add);
  const has = usePaperCartStore((s) => s.has);
  const remove = usePaperCartStore((s) => s.remove);
  usePaperCartStore((s) => s.items);

  const mut = useMutation({
    mutationFn: async (body: { query: string; mode: string; language: string }) => {
      const { data } = await api.post(`/projects/${id}/retrievals`, { ...body, top_k: 8 });
      return data.data;
    },
    onSuccess: (payload) => {
      setHits(payload.data.papers || []);
      setMeta(payload.data.retrieval_meta || null);
    },
    onError: (e: Error) => message.error(e.message),
  });

  return (
    <ProjectNav>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        文献检索
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        当前 Skill：S2。可将结果加入备选篮，再到研究工具中对比分析。
      </Typography.Paragraph>
      <Form
        layout="vertical"
        initialValues={{ mode: "hybrid", language: "all" }}
        onFinish={(v) => mut.mutate(v)}
        style={{ maxWidth: 720 }}
      >
        <Form.Item name="query" label="查询" rules={[{ required: true }]}>
          <Input.TextArea rows={2} placeholder="例如：国产青春电影的怀旧叙事" />
        </Form.Item>
        <Form.Item name="mode" label="模式">
          <Radio.Group
            options={[
              { value: "hybrid", label: "混合检索（推荐）" },
              { value: "keyword", label: "仅关键词" },
            ]}
          />
        </Form.Item>
        <Form.Item name="language" label="语言">
          <Radio.Group
            options={[
              { value: "all", label: "全部语言" },
              { value: "zh", label: "中文" },
              { value: "en", label: "英文" },
            ]}
          />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={mut.isPending}>
          检索
        </Button>
      </Form>

      {meta ? (
        <Typography.Paragraph type="secondary" style={{ marginTop: 16 }}>
          model={String(meta.model_id)} · reranker={String(meta.reranker_model_id)} · keyword=
          {String(meta.keyword)} · vector={String(meta.vector)}
        </Typography.Paragraph>
      ) : null}

      <List
        style={{ marginTop: 12 }}
        dataSource={hits}
        locale={{ emptyText: "尚无结果" }}
        renderItem={(h) => {
          const inCart = has(h.paper_id);
          return (
            <List.Item
              actions={[
                inCart ? (
                  <Button key="rm" danger onClick={() => remove(h.paper_id)}>
                    移出备选
                  </Button>
                ) : (
                  <Button
                    key="add"
                    type="primary"
                    ghost
                    onClick={() => {
                      const r = add({
                        id: h.paper_id,
                        title: h.title,
                        authors: h.authors,
                        year: h.year,
                      });
                      if (r.ok) message.success("已加入备选篮");
                      else message.warning(r.reason);
                    }}
                  >
                    加入备选
                  </Button>
                ),
              ]}
            >
              <List.Item.Meta
                title={h.title}
                description={
                  <Space direction="vertical" size={4}>
                    <Space wrap>
                      <span>{(h.authors || []).join("、")}</span>
                      <span>{h.year ?? "年份未识别"}</span>
                      <Tag>{h.source}</Tag>
                      <Tag>
                        p.{h.page_start}
                        {h.page_end && h.page_end !== h.page_start ? `-${h.page_end}` : ""}
                      </Tag>
                      <Tag color="blue">score {h.score?.toFixed?.(3) ?? h.score}</Tag>
                    </Space>
                    <Typography.Text copyable={{ text: h.paper_id }} type="secondary" style={{ fontSize: 12 }}>
                      编码：{h.paper_id}
                    </Typography.Text>
                    <Typography.Paragraph style={{ marginBottom: 0 }}>{h.snippet}</Typography.Paragraph>
                  </Space>
                }
              />
            </List.Item>
          );
        }}
      />
    </ProjectNav>
  );
}
