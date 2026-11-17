import {
  Alert,
  Button,
  Form,
  Input,
  List,
  Popconfirm,
  Space,
  Switch,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuthStore } from "../store/auth";

const statusLabel: Record<string, string> = {
  draft: "草稿",
  preparing: "资料准备",
  outline_pending: "大纲待确认",
  writing: "写作中",
  checking: "核验中",
  exportable: "可导出",
};

type ChatModel = {
  id: string;
  endpoint: string;
  model_name: string;
  enabled: boolean;
  notes: string;
  api_key_set: boolean;
  api_key_masked: string;
};

type PromptItem = {
  id: string;
  skill_code: string;
  prompt_key: string;
  title: string;
  content: string;
  version: number;
};

/** 管理后台：模型/提示词配置、项目删除与测试入口。 */
export default function AdminPage() {
  const role = useAuthStore((s) => s.user?.role);
  const qc = useQueryClient();
  const [modelForm] = Form.useForm();
  const [promptForm] = Form.useForm();
  const [selectedPrompt, setSelectedPrompt] = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["admin-projects"],
    queryFn: async () =>
      (await api.get("/admin/projects", { params: { page_size: 50 } })).data.data as {
        items: any[];
        total: number;
      },
    enabled: role === "admin",
  });

  const modelQuery = useQuery({
    queryKey: ["admin-chat-model"],
    queryFn: async () => (await api.get("/admin/model-configs/chat")).data.data as ChatModel | null,
    enabled: role === "admin",
  });

  const promptsQuery = useQuery({
    queryKey: ["admin-prompts"],
    queryFn: async () =>
      (await api.get("/admin/prompts")).data.data as { items: PromptItem[] },
    enabled: role === "admin",
  });

  useEffect(() => {
    const m = modelQuery.data;
    if (!m) return;
    modelForm.setFieldsValue({
      endpoint: m.endpoint,
      model_name: m.model_name,
      enabled: m.enabled,
      notes: m.notes,
      api_key: "",
    });
  }, [modelQuery.data, modelForm]);

  useEffect(() => {
    const items = promptsQuery.data?.items || [];
    if (!items.length) return;
    const first = items.find((p) => `${p.skill_code}.${p.prompt_key}` === selectedPrompt) || items[0];
    setSelectedPrompt(`${first.skill_code}.${first.prompt_key}`);
    promptForm.setFieldsValue({
      skill_code: first.skill_code,
      prompt_key: first.prompt_key,
      title: first.title,
      content: first.content,
    });
  }, [promptsQuery.data]); // eslint-disable-line react-hooks/exhaustive-deps

  const deleteMut = useMutation({
    mutationFn: async (id: string) => (await api.delete(`/projects/${id}`)).data,
    onSuccess: () => {
      message.success("项目已删除");
      qc.invalidateQueries({ queryKey: ["admin-projects"] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const saveModelMut = useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await api.put("/admin/model-configs/chat", body)).data.data,
    onSuccess: () => {
      message.success("模型配置已保存");
      qc.invalidateQueries({ queryKey: ["admin-chat-model"] });
      modelForm.setFieldValue("api_key", "");
    },
    onError: (e: Error) => message.error(e.message),
  });

  const testModelMut = useMutation({
    mutationFn: async () => (await api.post("/admin/model-configs/chat/test")).data.data,
    onSuccess: (d) => message.success(`连通成功：${d.reply || d.model_id}`),
    onError: (e: Error) => message.error(e.message),
  });

  const savePromptMut = useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await api.put("/admin/prompts", body)).data.data,
    onSuccess: (d) => {
      message.success(`提示词已保存为 v${d.version}`);
      qc.invalidateQueries({ queryKey: ["admin-prompts"] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  if (role !== "admin") {
    return <Navigate to="/" replace />;
  }

  const prompts = promptsQuery.data?.items || [];

  return (
    <div>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        管理后台
      </Typography.Title>
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        message="模型 Key 与提示词仅管理员可改；接口返回脱敏密钥。修改后立即作用于大纲/写作/润色。"
      />

      <Tabs
        items={[
          {
            key: "model",
            label: "对话模型",
            children: (
              <div style={{ maxWidth: 720 }}>
                <Alert
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                  message={
                    modelQuery.data?.api_key_set
                      ? `当前密钥：${modelQuery.data.api_key_masked}（留空保存表示不修改）`
                      : "尚未配置 API Key，请填写后保存"
                  }
                />
                <Form
                  form={modelForm}
                  layout="vertical"
                  initialValues={{
                    endpoint: "https://api.deepseek.com",
                    model_name: "deepseek-chat",
                    enabled: true,
                  }}
                  onFinish={(v) =>
                    saveModelMut.mutate({
                      endpoint: v.endpoint,
                      model_name: v.model_name,
                      enabled: v.enabled,
                      notes: v.notes || "",
                      api_key: v.api_key || null,
                    })
                  }
                >
                  <Form.Item name="endpoint" label="Endpoint" rules={[{ required: true }]}>
                    <Input placeholder="https://api.deepseek.com" />
                  </Form.Item>
                  <Form.Item name="model_name" label="模型名" rules={[{ required: true }]}>
                    <Input placeholder="deepseek-chat" />
                  </Form.Item>
                  <Form.Item name="api_key" label="API Key">
                    <Input.Password placeholder="粘贴新密钥；留空则保持原密钥" />
                  </Form.Item>
                  <Form.Item name="notes" label="备注">
                    <Input.TextArea rows={2} placeholder="例如：DeepSeek 生产密钥" />
                  </Form.Item>
                  <Form.Item name="enabled" label="启用" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                  <Space>
                    <Button type="primary" htmlType="submit" loading={saveModelMut.isPending}>
                      保存模型配置
                    </Button>
                    <Button loading={testModelMut.isPending} onClick={() => testModelMut.mutate()}>
                      测试连通
                    </Button>
                  </Space>
                </Form>
              </div>
            ),
          },
          {
            key: "prompts",
            label: "提示词",
            children: (
              <div style={{ maxWidth: 860 }}>
                <Space wrap style={{ marginBottom: 12 }}>
                  {prompts.map((p) => (
                    <Button
                      key={p.id}
                      size="small"
                      type={selectedPrompt === `${p.skill_code}.${p.prompt_key}` ? "primary" : "default"}
                      onClick={() => {
                        setSelectedPrompt(`${p.skill_code}.${p.prompt_key}`);
                        promptForm.setFieldsValue({
                          skill_code: p.skill_code,
                          prompt_key: p.prompt_key,
                          title: p.title,
                          content: p.content,
                        });
                      }}
                    >
                      {p.skill_code}.{p.prompt_key} · v{p.version}
                    </Button>
                  ))}
                </Space>
                <Form
                  form={promptForm}
                  layout="vertical"
                  onFinish={(v) => savePromptMut.mutate(v)}
                >
                  <Form.Item name="skill_code" label="Skill" rules={[{ required: true }]}>
                    <Input placeholder="S7 / S8 / polish" />
                  </Form.Item>
                  <Form.Item name="prompt_key" label="键名" rules={[{ required: true }]}>
                    <Input placeholder="system" />
                  </Form.Item>
                  <Form.Item name="title" label="标题">
                    <Input />
                  </Form.Item>
                  <Form.Item name="content" label="提示词正文" rules={[{ required: true }]}>
                    <Input.TextArea rows={12} />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={savePromptMut.isPending}>
                    保存为新版本
                  </Button>
                </Form>
              </div>
            ),
          },
          {
            key: "projects",
            label: "项目运维",
            children: (
              <>
                <Typography.Title level={4}>测试入口</Typography.Title>
                <Space wrap style={{ marginBottom: 24 }}>
                  <Button onClick={() => window.open("/tools/analysis", "_blank", "noopener,noreferrer")}>
                    研究工具（对比/空白）
                  </Button>
                  <Link to="/library">
                    <Button>公用知识库</Button>
                  </Link>
                </Space>
                <Typography.Title level={4}>全部项目（可删除）</Typography.Title>
                <List
                  loading={isLoading}
                  dataSource={data?.items || []}
                  locale={{ emptyText: "暂无项目" }}
                  header={<Typography.Text type="secondary">共 {data?.total ?? 0} 个</Typography.Text>}
                  renderItem={(item) => (
                    <List.Item
                      actions={[
                        <Link key="open" to={`/projects/${item.id}`}>
                          打开
                        </Link>,
                        <Popconfirm
                          key="del"
                          title="删除该项目？"
                          description="将删除大纲、正文、润色与导出；公用知识库不受影响。"
                          okText="删除"
                          cancelText="取消"
                          okButtonProps={{ danger: true }}
                          onConfirm={() => deleteMut.mutate(item.id)}
                        >
                          <Button type="link" danger loading={deleteMut.isPending}>
                            删除
                          </Button>
                        </Popconfirm>,
                      ]}
                    >
                      <List.Item.Meta
                        title={item.title}
                        description={
                          <Space wrap>
                            <Tag>{statusLabel[item.status] || item.status}</Tag>
                            <span>{item.paper_type}</span>
                            <span>作者：{item.owner_name || item.owner_id?.slice(0, 8)}</span>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              </>
            ),
          },
        ]}
      />
    </div>
  );
}
