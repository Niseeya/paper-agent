import { Alert, Button, Radio, Space, Typography, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import ProjectNav from "../components/ProjectNav";
import { api } from "../api/client";
import { useAuthStore } from "../store/auth";

export default function ExportPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const token = useAuthStore((s) => s.token);
  const [mode, setMode] = useState<"draft" | "final">("draft");

  const exportQuery = useQuery({
    queryKey: ["export", id],
    queryFn: async () => {
      try {
        return (await api.get(`/projects/${id}/exports/latest`)).data.data;
      } catch {
        return null;
      }
    },
  });

  const runMut = useMutation({
    mutationFn: async () => (await api.post(`/projects/${id}/exports`, { mode })).data.data,
    onSuccess: () => {
      message.success(mode === "final" ? "定稿导出成功" : "草稿导出成功");
      qc.invalidateQueries({ queryKey: ["export", id] });
      qc.invalidateQueries({ queryKey: ["project", id] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const files = exportQuery.data?.payload?.files;

  function download(fmt: string) {
    const url = `/api/v1/projects/${id}/exports/download?fmt=${fmt}`;
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (res) => {
        if (!res.ok) throw new Error("下载失败");
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `export.${fmt}`;
        a.click();
      })
      .catch((e) => message.error(e.message));
  }

  return (
    <ProjectNav>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        导出
      </Typography.Title>
      <Alert
        showIcon
        type="info"
        style={{ marginBottom: 16 }}
        message="定稿要求引用核查全部通过；失败时留在本页，并可回到问题句。"
        action={
          <Link to={`/projects/${id}/citations`}>
            <Button size="small">查看核查</Button>
          </Link>
        }
      />
      <Space direction="vertical" size="middle">
        <Radio.Group
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          options={[
            { value: "draft", label: "草稿导出（页眉注明辅助生成草稿）" },
            { value: "final", label: "定稿导出（需 L1/L2 全过）" },
          ]}
        />
        <Button type="primary" loading={runMut.isPending} onClick={() => runMut.mutate()}>
          开始导出（S10）
        </Button>
        {files ? (
          <Space>
            <Button onClick={() => download("docx")}>下载 DOCX</Button>
            <Button onClick={() => download("pdf")}>下载 PDF</Button>
            <Typography.Text type="secondary">模式：{exportQuery.data?.payload?.mode}</Typography.Text>
          </Space>
        ) : null}
      </Space>
    </ProjectNav>
  );
}
