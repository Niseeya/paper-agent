import { Alert, Button, Form, Input, Space, Typography, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ProjectNav from "../components/ProjectNav";
import { api } from "../api/client";

type Node = {
  id: string;
  level: number;
  title: string;
  intent: string;
  related_paper_ids?: string[];
  children?: Node[];
};

function cloneNodes(nodes: Node[] = []): Node[] {
  return nodes.map((n) => ({
    ...n,
    id: n.id || crypto.randomUUID().replace(/-/g, ""),
    children: cloneNodes(n.children || []),
  }));
}

function updateAt(nodes: Node[], path: number[], patch: Partial<Node>): Node[] {
  if (!path.length) return nodes;
  const [i, ...rest] = path;
  return nodes.map((n, idx) => {
    if (idx !== i) return n;
    if (!rest.length) return { ...n, ...patch };
    return { ...n, children: updateAt(n.children || [], rest, patch) };
  });
}

function removeAt(nodes: Node[], path: number[]): Node[] {
  if (!path.length) return nodes;
  const [i, ...rest] = path;
  if (!rest.length) return nodes.filter((_, idx) => idx !== i);
  return nodes.map((n, idx) => {
    if (idx !== i) return n;
    return { ...n, children: removeAt(n.children || [], rest) };
  });
}

function addChildAt(nodes: Node[], path: number[], level: number): Node[] {
  const child: Node = {
    id: crypto.randomUUID().replace(/-/g, ""),
    level,
    title: "新章节",
    intent: "补充本节写作意图",
    children: [],
  };
  if (!path.length) return [...nodes, child];
  const [i, ...rest] = path;
  return nodes.map((n, idx) => {
    if (idx !== i) return n;
    if (!rest.length) return { ...n, children: [...(n.children || []), { ...child, level: Math.min(3, n.level + 1) }] };
    return { ...n, children: addChildAt(n.children || [], rest, level) };
  });
}

function addSiblingAfter(nodes: Node[], path: number[]): Node[] {
  if (!path.length) return nodes;
  const [i, ...rest] = path;
  if (!rest.length) {
    const base = nodes[i];
    const sibling: Node = {
      id: crypto.randomUUID().replace(/-/g, ""),
      level: base?.level || 1,
      title: "新章节",
      intent: "补充本节写作意图",
      children: [],
    };
    const next = [...nodes];
    next.splice(i + 1, 0, sibling);
    return next;
  }
  return nodes.map((n, idx) => {
    if (idx !== i) return n;
    return { ...n, children: addSiblingAfter(n.children || [], rest) };
  });
}

function NodeEditor({
  nodes,
  path,
  disabled,
  onChange,
}: {
  nodes: Node[];
  path: number[];
  disabled?: boolean;
  onChange: (next: Node[]) => void;
}) {
  return (
    <>
      {nodes.map((n, idx) => {
        const cur = [...path, idx];
        const pad = (n.level - 1) * 20;
        return (
          <div key={n.id || cur.join("-")} style={{ marginBottom: 12 }}>
            <div
              style={{
                marginLeft: pad,
                padding: "10px 12px",
                border: "1px solid #f0f0f0",
                borderRadius: 8,
                background: "#fafafa",
              }}
            >
              <Space direction="vertical" style={{ width: "100%" }} size={8}>
                <Space wrap style={{ width: "100%" }}>
                  <Typography.Text type="secondary">L{n.level}</Typography.Text>
                  <Input
                    disabled={disabled}
                    value={n.title}
                    placeholder="章节标题"
                    style={{ width: 280 }}
                    onChange={(e) => onChange(updateAt(nodes, [idx], { title: e.target.value }))}
                  />
                  <Button
                    size="small"
                    disabled={disabled}
                    onClick={() => onChange(addSiblingAfter(nodes, [idx]))}
                  >
                    同级
                  </Button>
                  <Button
                    size="small"
                    disabled={disabled || n.level >= 3}
                    onClick={() => onChange(addChildAt(nodes, [idx], Math.min(3, n.level + 1)))}
                  >
                    子节
                  </Button>
                  <Button
                    size="small"
                    danger
                    disabled={disabled || (path.length === 0 && nodes.length <= 1 && !(n.children || []).length)}
                    onClick={() => onChange(removeAt(nodes, [idx]))}
                  >
                    删除
                  </Button>
                </Space>
                <Input.TextArea
                  disabled={disabled}
                  value={n.intent}
                  placeholder="写作意图"
                  autoSize={{ minRows: 1, maxRows: 3 }}
                  onChange={(e) => onChange(updateAt(nodes, [idx], { intent: e.target.value }))}
                />
              </Space>
            </div>
            {(n.children || []).length ? (
              <div style={{ marginTop: 8 }}>
                <NodeEditor
                  nodes={n.children || []}
                  path={[]}
                  disabled={disabled}
                  onChange={(children) => onChange(updateAt(nodes, [idx], { children }))}
                />
              </div>
            ) : null}
          </div>
        );
      })}
    </>
  );
}

export default function OutlinePage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const [draftNodes, setDraftNodes] = useState<Node[]>([]);
  const [dirty, setDirty] = useState(false);

  const { data: project } = useQuery({
    queryKey: ["project", id],
    queryFn: async () => (await api.get(`/projects/${id}`)).data.data,
  });

  const outlineQuery = useQuery({
    queryKey: ["outline", id],
    queryFn: async () => {
      try {
        return (await api.get(`/projects/${id}/outlines/latest`)).data.data;
      } catch {
        return null;
      }
    },
  });

  useEffect(() => {
    if (!outlineQuery.data?.payload?.nodes) return;
    setDraftNodes(cloneNodes(outlineQuery.data.payload.nodes));
    setDirty(false);
  }, [outlineQuery.data?.id, outlineQuery.data?.version]);

  const genMut = useMutation({
    mutationFn: async (research_goal?: string) =>
      (await api.post(`/projects/${id}/outlines`, { research_goal })).data.data,
    onSuccess: () => {
      message.success("大纲已生成，可直接修改后保存");
      qc.invalidateQueries({ queryKey: ["outline", id] });
      qc.invalidateQueries({ queryKey: ["project", id] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const saveMut = useMutation({
    mutationFn: async (nodes: Node[]) =>
      (
        await api.put(`/projects/${id}/outlines`, {
          nodes,
          topic_name: outlineQuery.data?.payload?.topic_name,
          paper_type: outlineQuery.data?.payload?.paper_type || project?.paper_type,
        })
      ).data.data,
    onSuccess: () => {
      message.success("大纲已保存，请确认后再写作");
      setDirty(false);
      qc.invalidateQueries({ queryKey: ["outline", id] });
      qc.invalidateQueries({ queryKey: ["project", id] });
      qc.invalidateQueries({ queryKey: ["writing-plan", id] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const confirmMut = useMutation({
    mutationFn: async (version: number) =>
      (await api.post(`/projects/${id}/outlines/${version}/confirm`)).data.data,
    onSuccess: () => {
      message.success("大纲已确认，可进入写作");
      qc.invalidateQueries({ queryKey: ["outline", id] });
      qc.invalidateQueries({ queryKey: ["project", id] });
      qc.invalidateQueries({ queryKey: ["writing-plan", id] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const confirmed = !!(outlineQuery.data?.confirmed || project?.outline_confirmed);
  const canConfirm = !!outlineQuery.data && !dirty && !confirmed;

  const setNodes = (next: Node[]) => {
    setDraftNodes(next);
    setDirty(true);
  };

  return (
    <ProjectNav>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        大纲
      </Typography.Title>
      <Alert
        style={{ marginBottom: 16 }}
        type="info"
        showIcon
        message="生成后可直接改标题与写作意图，也可增删章节；保存后需确认大纲，才能批量写作。修改已确认大纲会取消确认。"
      />
      <Form
        layout="inline"
        style={{ marginBottom: 16 }}
        onFinish={(v) => genMut.mutate(v.research_goal || project?.title)}
        initialValues={{ research_goal: project?.title }}
      >
        <Form.Item name="research_goal" label="研究目标">
          <Input style={{ width: 420 }} />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={genMut.isPending}>
          生成大纲（S7）
        </Button>
      </Form>

      {outlineQuery.data ? (
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Space wrap>
            <Typography.Text>版本 v{outlineQuery.data.version}</Typography.Text>
            {dirty ? <Typography.Text type="warning">有未保存修改</Typography.Text> : null}
            {confirmed && !dirty ? (
              <>
                <Typography.Text type="success">已确认</Typography.Text>
                <Link to={`/projects/${id}/editor`}>
                  <Button type="primary">下一步：按大纲写作</Button>
                </Link>
              </>
            ) : null}
            <Button
              type="primary"
              loading={saveMut.isPending}
              disabled={!dirty}
              onClick={() => saveMut.mutate(draftNodes)}
            >
              保存修改
            </Button>
            <Button
              disabled={!canConfirm}
              loading={confirmMut.isPending}
              onClick={() => confirmMut.mutate(outlineQuery.data.version)}
            >
              确认大纲
            </Button>
            <Button
              disabled={draftNodes.length >= 20}
              onClick={() =>
                setNodes([
                  ...draftNodes,
                  {
                    id: crypto.randomUUID().replace(/-/g, ""),
                    level: 1,
                    title: "新章节",
                    intent: "补充本节写作意图",
                    children: [],
                  },
                ])
              }
            >
              添加一级章节
            </Button>
          </Space>
          <NodeEditor nodes={draftNodes} path={[]} onChange={setNodes} />
        </Space>
      ) : (
        <Typography.Paragraph type="secondary">尚未生成大纲</Typography.Paragraph>
      )}
    </ProjectNav>
  );
}
