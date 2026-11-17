import { Alert, Button, Form, Input, Tabs, Typography, message } from "antd";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuthStore } from "../store/auth";

export default function LoginPage() {
  const token = useAuthStore((s) => s.token);
  const setAuth = useAuthStore((s) => s.setAuth);
  const nav = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (token) return <Navigate to="/" replace />;

  async function onLogin(values: { username: string; password: string }) {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post("/auth/login", values);
      setAuth(data.data.token, data.data.user);
      message.success("登录成功");
      nav("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  async function onRegister(values: {
    username: string;
    password: string;
    display_name?: string;
  }) {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post("/auth/register", values);
      setAuth(data.data.token, data.data.user);
      message.success("注册成功");
      nav("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "注册失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="hero-login">
      <section className="hero-panel">
        <Typography.Paragraph style={{ color: "#d7e7df", marginBottom: 12 }}>
          基于 RAG 与多 Skill 协同
        </Typography.Paragraph>
        <h1>学术论文研究与生成 AI 智能体</h1>
        <p>
          面向单一研究领域的公用知识库。系统负责证据约束下的检索、分析与写作辅助；
          大纲确认、润色确认与定稿导出由作者把关。正式引用必须回链库内论文与页码证据。
        </p>
      </section>
      <section className="login-panel">
        <div style={{ width: "min(420px, 100%)" }}>
          <Typography.Title level={3} style={{ marginTop: 0 }}>
            进入工作区
          </Typography.Title>
          {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
          <Tabs
            items={[
              {
                key: "login",
                label: "登录",
                children: (
                  <Form layout="vertical" onFinish={onLogin}>
                    <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
                      <Input autoComplete="username" />
                    </Form.Item>
                    <Form.Item name="password" label="密码" rules={[{ required: true }]}>
                      <Input.Password autoComplete="current-password" />
                    </Form.Item>
                    <Button type="primary" htmlType="submit" block loading={loading}>
                      登录
                    </Button>
                  </Form>
                ),
              },
              {
                key: "register",
                label: "注册",
                children: (
                  <Form layout="vertical" onFinish={onRegister}>
                    <Form.Item name="username" label="用户名" rules={[{ required: true, min: 3 }]}>
                      <Input />
                    </Form.Item>
                    <Form.Item name="display_name" label="显示名">
                      <Input />
                    </Form.Item>
                    <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
                      <Input.Password />
                    </Form.Item>
                    <Button type="primary" htmlType="submit" block loading={loading}>
                      注册并进入
                    </Button>
                  </Form>
                ),
              },
            ]}
          />
        </div>
      </section>
    </div>
  );
}
