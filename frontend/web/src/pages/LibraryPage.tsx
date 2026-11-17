import { Alert, Button, Checkbox, Input, List, Pagination, Space, Tag, Typography, Upload, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { usePaperCartStore } from "../store/paperCart";

type Paper = {
  id: string;
  title: string;
  authors: string[];
  year?: number;
  source_type: string;
  page_count?: number;
  section_recognized?: boolean;
  direction?: string;
};

type DirectionStat = {
  direction: string;
  count: number;
  keywords: string[];
  sample_titles: string[];
};

export default function LibraryPage() {
  const [q, setQ] = useState("");
  const [direction, setDirection] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [rights, setRights] = useState(false);
  const qc = useQueryClient();
  const add = usePaperCartStore((s) => s.add);
  const has = usePaperCartStore((s) => s.has);
  const remove = usePaperCartStore((s) => s.remove);
  usePaperCartStore((s) => s.items);

  const { data: dirData } = useQuery({
    queryKey: ["paper-directions"],
    queryFn: async () =>
      (await api.get("/papers/directions")).data.data as {
        total: number;
        directions: DirectionStat[];
      },
  });

  const { data, isLoading } = useQuery({
    queryKey: ["papers", q, direction, page, pageSize],
    queryFn: async () =>
      (
        await api.get("/papers", {
          params: {
            q: q || undefined,
            direction: direction || undefined,
            page,
            page_size: pageSize,
          },
        })
      ).data.data as {
        items: Paper[];
        total: number;
        page: number;
        page_size: number;
      },
  });

  const uploadMut = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      form.append("rights_confirmed", String(rights));
      form.append("embed", "true");
      return (await api.post("/papers/upload", form)).data.data;
    },
    onSuccess: (d) => {
      message.success(`已入库：${d.title}`);
      qc.invalidateQueries({ queryKey: ["papers"] });
      qc.invalidateQueries({ queryKey: ["paper-directions"] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const total = data?.total ?? 0;
  const corpusTotal = dirData?.total ?? total;

  const selectDirection = (name: string | null) => {
    setPage(1);
    setDirection(name);
  };

  return (
    <div>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        公用知识库
      </Typography.Title>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="可按研究方向筛选查看具体文章；也可加入备选篮，再到研究工具做对比分析。"
      />

      <Typography.Title level={5} style={{ marginBottom: 8 }}>
        研究方向筛选
      </Typography.Title>
      <Space wrap style={{ marginBottom: 8 }}>
        <Tag.CheckableTag checked={!direction} onChange={(c) => c && selectDirection(null)}>
          全部（{corpusTotal}）
        </Tag.CheckableTag>
        {(dirData?.directions || []).map((d) => (
          <Tag.CheckableTag
            key={d.direction}
            checked={direction === d.direction}
            onChange={(c) => selectDirection(c ? d.direction : null)}
          >
            {d.direction}（{d.count}）
          </Tag.CheckableTag>
        ))}
      </Space>
      {direction ? (
        <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
          当前方向：{direction}
          {(() => {
            const cur = dirData?.directions?.find((d) => d.direction === direction);
            if (!cur?.keywords?.length) return " · 题名未命中预置词，归入其他";
            return ` · 题名关键词：${cur.keywords.join("、")}`;
          })()}
        </Typography.Paragraph>
      ) : (
        <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
          选择上方方向可只看该方向下的文章；列表中每篇也会标注所属方向。
        </Typography.Paragraph>
      )}

      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="按题名过滤"
          allowClear
          onSearch={(v) => {
            setPage(1);
            setQ(v);
          }}
          style={{ width: 320 }}
        />
        <Checkbox checked={rights} onChange={(e) => setRights(e.target.checked)}>
          我有权上传，并同意进入公用知识库供其他登录用户检索
        </Checkbox>
        <Upload
          accept=".pdf"
          showUploadList={false}
          beforeUpload={(file) => {
            if (!rights) {
              message.warning("请先勾选上传授权");
              return Upload.LIST_IGNORE;
            }
            uploadMut.mutate(file);
            return false;
          }}
        >
          <Button type="primary" loading={uploadMut.isPending}>
            上传 PDF
          </Button>
        </Upload>
      </Space>

      <Typography.Paragraph type="secondary">
        {direction ? `本方向 ${total} 篇` : `共 ${total} 篇已索引`}
        {total > 0 ? `（当前第 ${page} 页，每页 ${pageSize} 条）` : ""}
      </Typography.Paragraph>
      <List
        loading={isLoading}
        dataSource={data?.items || []}
        locale={{ emptyText: direction ? "该方向下暂无文章" : "暂无已索引论文" }}
        renderItem={(p) => {
          const inCart = has(p.id);
          return (
            <List.Item
              actions={[
                inCart ? (
                  <Button key="rm" danger onClick={() => remove(p.id)}>
                    移出备选
                  </Button>
                ) : (
                  <Button
                    key="add"
                    type="primary"
                    ghost
                    onClick={() => {
                      const r = add({
                        id: p.id,
                        title: p.title,
                        authors: p.authors,
                        year: p.year,
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
                title={p.title}
                description={
                  <Space direction="vertical" size={2}>
                    <Space wrap>
                      <Tag color="blue">{p.direction || "未分类"}</Tag>
                      <span>{(p.authors || []).join("、") || "作者未识别"}</span>
                      <span>{p.year || "年份未识别"}</span>
                      <Tag>{p.source_type}</Tag>
                      {p.section_recognized ? <Tag color="green">章节已识别</Tag> : <Tag>章节未识别</Tag>}
                      <span>{p.page_count ?? "-"} 页</span>
                    </Space>
                    <Typography.Text copyable={{ text: p.id }} type="secondary" style={{ fontSize: 12 }}>
                      编码：{p.id}
                    </Typography.Text>
                  </Space>
                }
              />
            </List.Item>
          );
        }}
      />
      {total > 0 ? (
        <Pagination
          style={{ marginTop: 16, textAlign: "right" }}
          current={page}
          pageSize={pageSize}
          total={total}
          showSizeChanger
          pageSizeOptions={["10", "20", "50"]}
          showQuickJumper
          showTotal={(t) => `共 ${t} 篇`}
          onChange={(p, ps) => {
            setPage(p);
            setPageSize(ps);
          }}
        />
      ) : null}
    </div>
  );
}
