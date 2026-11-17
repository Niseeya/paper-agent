import { Alert, Button, Form, Input, Radio, Space, Typography, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import ProjectNav from "../components/ProjectNav";
import { api } from "../api/client";

export default function PolishPage() {
  const { id } = useParams();
  const qc = useQueryClient();

  const polishQuery = useQuery({
    queryKey: ["polish", id],
    queryFn: async () => {
      try {
        return (await api.get(`/projects/${id}/polishes/latest`)).data.data;
      } catch {
        return null;
      }
    },
  });

  const runMut = useMutation({
    mutationFn: async (body: { level: string; user_request?: string }) =>
      (await api.post(`/projects/${id}/polishes`, body)).data.data,
    onSuccess: () => {
      message.success("润色完成，请对照确认");
      qc.invalidateQueries({ queryKey: ["polish", id] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const confirmMut = useMutation({
    mutationFn: async (version: number) =>
      (await api.post(`/projects/${id}/polishes/${version}/confirm`)).data.data,
    onSuccess: () => {
      message.success("已写入正文（保留章节与引用）");
      qc.invalidateQueries({ queryKey: ["polish", id] });
      qc.invalidateQueries({ queryKey: ["document", id] });
      qc.invalidateQueries({ queryKey: ["writing-plan", id] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const payload = polishQuery.data?.payload;

  return (
    <ProjectNav>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        润色
      </Typography.Title>
      <Alert
        showIcon
        type="info"
        message="确认前不替换正文。降重/规避查重请求会被拒绝。不改数字与引用标记。"
        style={{ marginBottom: 16 }}
      />
      <Form
        layout="vertical"
        style={{ maxWidth: 720 }}
        initialValues={{ level: "academic", user_request: "" }}
        onFinish={(v) => runMut.mutate(v)}
      >
        <Form.Item name="level" label="档位">
          <Radio.Group
            options={[
              { value: "light", label: "轻度" },
              { value: "academic", label: "学术" },
              { value: "deep", label: "深度" },
            ]}
          />
        </Form.Item>
        <Form.Item name="user_request" label="附加说明">
          <Input placeholder="不要填写降重/查重规避" />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={runMut.isPending}>
          生成润色对照
        </Button>
      </Form>

      {payload ? (
        <Space direction="vertical" style={{ width: "100%", marginTop: 24 }} size="middle">
          {payload.rejected ? (
            <Alert type="error" showIcon message={payload.reject_reason || "请求被拒绝"} />
          ) : (
            <>
              <Typography.Title level={5}>原文</Typography.Title>
              <Typography.Paragraph>{payload.original}</Typography.Paragraph>
              <Typography.Title level={5}>润色稿</Typography.Title>
              <Typography.Paragraph>{payload.polished}</Typography.Paragraph>
              <Space>
                <Button
                  type="primary"
                  disabled={polishQuery.data?.confirmed}
                  loading={confirmMut.isPending}
                  onClick={() => confirmMut.mutate(polishQuery.data.version)}
                >
                  {polishQuery.data?.confirmed ? "已确认" : "确认并替换正文"}
                </Button>
                <Link to={`/projects/${id}/citations`}>
                  <Button>下一步：引用核查</Button>
                </Link>
              </Space>
            </>
          )}
        </Space>
      ) : null}
    </ProjectNav>
  );
}
