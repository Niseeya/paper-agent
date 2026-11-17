import { Badge, Button, Drawer, List, Space, Typography, message } from "antd";
import { useState } from "react";
import { usePaperCartStore } from "../store/paperCart";

export default function PaperCartButton() {
  const [open, setOpen] = useState(false);
  const items = usePaperCartStore((s) => s.items);
  const remove = usePaperCartStore((s) => s.remove);
  const clear = usePaperCartStore((s) => s.clear);

  return (
    <>
      <Badge count={items.length} size="small">
        <Button onClick={() => setOpen(true)}>备选篮</Button>
      </Badge>
      <Drawer
        title={`论文备选篮（${items.length}/8）`}
        open={open}
        onClose={() => setOpen(false)}
        width={420}
        extra={
          <Space>
            <Button
              size="small"
              disabled={!items.length}
              onClick={() => {
                clear();
                message.success("已清空备选篮");
              }}
            >
              清空
            </Button>
            <Button
              type="primary"
              size="small"
              disabled={items.length < 2}
              onClick={() => {
                setOpen(false);
                window.open("/tools/analysis", "_blank", "noopener,noreferrer");
              }}
            >
              去对比分析
            </Button>
          </Space>
        }
      >
        <Typography.Paragraph type="secondary">
          从知识库或检索结果加入论文编码后，可在研究工具中一键对比（需至少 2 篇）。
        </Typography.Paragraph>
        <List
          dataSource={items}
          locale={{ emptyText: "还没有加入论文" }}
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
                  <Space direction="vertical" size={0}>
                    <Typography.Text copyable={{ text: p.id }} type="secondary" style={{ fontSize: 12 }}>
                      编码：{p.id}
                    </Typography.Text>
                    <span>
                      {(p.authors || []).join("、") || "作者未识别"}
                      {p.year ? ` · ${p.year}` : ""}
                    </span>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Drawer>
    </>
  );
}
