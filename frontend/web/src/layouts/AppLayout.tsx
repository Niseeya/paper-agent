import { Button, Space, Typography } from "antd";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import PaperCartButton from "../components/PaperCartButton";

export default function AppLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const nav = useNavigate();
  const isAdmin = user?.role === "admin";

  return (
    <div className="app-shell">
      <header className="topbar">
        <Space size="large">
          <Link to="/" style={{ textDecoration: "none" }}>
            <h1 className="brand">论文智能体</h1>
          </Link>
          <Link to="/">项目</Link>
          <Link to="/library">公用知识库</Link>
          <a
            href="/tools/analysis"
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => {
              e.preventDefault();
              window.open("/tools/analysis", "_blank", "noopener,noreferrer");
            }}
          >
            研究工具
          </a>
          {isAdmin ? <Link to="/admin">管理后台</Link> : null}
        </Space>
        <Space>
          <PaperCartButton />
          <Typography.Text type="secondary">
            {user?.display_name || user?.username}
            {isAdmin ? " · 管理员" : ""}
          </Typography.Text>
          <Button
            onClick={() => {
              logout();
              nav("/login");
            }}
          >
            退出
          </Button>
        </Space>
      </header>
      <main className="page">
        <Outlet />
      </main>
    </div>
  );
}
