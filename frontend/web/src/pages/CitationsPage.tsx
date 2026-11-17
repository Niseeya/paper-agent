import { Alert, Button, List, Tag, Typography, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import ProjectNav from "../components/ProjectNav";
import { api } from "../api/client";

export default function CitationsPage() {
  const { id } = useParams();
  const qc = useQueryClient();

  const checkQuery = useQuery({
    queryKey: ["citation-check", id],
    queryFn: async () => {
      try {
        return (await api.get(`/projects/${id}/citation-checks/latest`)).data.data;
      } catch {
        return null;
      }
    },
  });

  const runMut = useMutation({
    mutationFn: async () => (await api.post(`/projects/${id}/citation-checks`)).data.data,
    onSuccess: () => {
      message.success("核查完成");
      qc.invalidateQueries({ queryKey: ["citation-check", id] });
      qc.invalidateQueries({ queryKey: ["project", id] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const payload = checkQuery.data?.payload;
  const passed = !!payload?.passed;

  return (
    <ProjectNav>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        引用与逻辑核查
      </Typography.Title>
      <Button type="primary" loading={runMut.isPending} onClick={() => runMut.mutate()} style={{ marginBottom: 16 }}>
        运行 S9 核查
      </Button>
      {payload ? (
        <>
          {passed ? (
            <Alert
              type="success"
              showIcon
              message="全部通过，可定稿导出"
              action={
                <Link to={`/projects/${id}/export`}>
                  <Button type="primary" size="small">
                    下一步：导出定稿
                  </Button>
                </Link>
              }
            />
          ) : (
            <Alert
              type="warning"
              showIcon
              message="存在未通过项，定稿将被拒绝；仍可草稿导出"
              action={
                <Link to={`/projects/${id}/export`}>
                  <Button size="small">去导出草稿</Button>
                </Link>
              }
            />
          )}
          <Typography.Title level={4}>引用问题</Typography.Title>
          <List
            dataSource={payload.citation_issues || []}
            locale={{ emptyText: "无" }}
            renderItem={(item: any) => (
              <List.Item>
                <List.Item.Meta
                  title={<Tag color="red">{item.detail}</Tag>}
                  description={item.sentence}
                />
              </List.Item>
            )}
          />
          <Typography.Title level={4}>逻辑问题</Typography.Title>
          <List
            dataSource={payload.logic_issues || []}
            locale={{ emptyText: "无" }}
            renderItem={(item: any) => (
              <List.Item>
                <List.Item.Meta title={<Tag>{item.detail}</Tag>} description={item.sentence} />
              </List.Item>
            )}
          />
        </>
      ) : (
        <Typography.Paragraph type="secondary">尚未核查</Typography.Paragraph>
      )}
    </ProjectNav>
  );
}
