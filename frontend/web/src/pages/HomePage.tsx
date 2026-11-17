import { Button, Form, Input, List, Select, Space, Tag, Typography, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";

type Project = {
  id: string;
  title: string;
  paper_type: string;
  status: string;
  outline_confirmed: boolean;
};

const statusLabel: Record<string, string> = {
  draft: "草稿",
  preparing: "资料准备",
  outline_pending: "大纲待确认",
  writing: "写作中",
  checking: "核验中",
  exportable: "可导出",
};

export default function HomePage() {
  const qc = useQueryClient();
  const nav = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: async () => (await api.get("/projects")).data.data as { items: Project[]; total: number },
  });

  const createMut = useMutation({
    mutationFn: async (body: { title: string; paper_type: string }) =>
      (await api.post("/projects", body)).data.data as Project,
    onSuccess: (p) => {
      message.success("项目已创建，进入成稿流程");
      qc.invalidateQueries({ queryKey: ["projects"] });
      nav(`/projects/${p.id}`);
    },
    onError: (e: Error) => message.error(e.message),
  });

  return (
    <div>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        我的项目
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        新建后按「检索 → 大纲 → 写作 → 润色 → 核查 → 导出」引导完成。项目删除仅管理员可操作。
      </Typography.Paragraph>
      <Form
        layout="inline"
        style={{ marginBottom: 24 }}
        onFinish={(v) => createMut.mutate(v)}
        initialValues={{ paper_type: "综述" }}
      >
        <Form.Item name="title" rules={[{ required: true, message: "请输入题目" }]}>
          <Input placeholder="新项目题目" style={{ width: 360 }} />
        </Form.Item>
        <Form.Item name="paper_type">
          <Select
            style={{ width: 140 }}
            options={[
              { value: "综述", label: "综述" },
              { value: "实证研究", label: "实证研究" },
              { value: "设计与实现", label: "设计与实现" },
            ]}
          />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={createMut.isPending}>
          新建并进入流程
        </Button>
      </Form>

      <List
        loading={isLoading}
        dataSource={data?.items || []}
        locale={{ emptyText: "还没有项目，先新建一个" }}
        renderItem={(item) => (
          <List.Item
            actions={[
              <Link key="open" to={`/projects/${item.id}`}>
                继续流程
              </Link>,
            ]}
          >
            <List.Item.Meta
              title={item.title}
              description={
                <Space>
                  <Tag>{statusLabel[item.status] || item.status}</Tag>
                  <span>{item.paper_type}</span>
                  {item.outline_confirmed ? <Tag color="green">大纲已确认</Tag> : null}
                </Space>
              }
            />
          </List.Item>
        )}
      />
    </div>
  );
}
