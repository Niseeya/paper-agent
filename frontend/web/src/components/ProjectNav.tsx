import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

/** 主流程导航：不含对比/方向/研究空白（已抽离为独立工具页）。 */
const FLOW_ITEMS = [
  { key: "overview", path: "", label: "流程" },
  { key: "search", path: "search", label: "检索" },
  { key: "outline", path: "outline", label: "大纲" },
  { key: "editor", path: "editor", label: "正文" },
  { key: "polish", path: "polish", label: "润色" },
  { key: "citations", path: "citations", label: "核查" },
  { key: "export", path: "export", label: "导出" },
] as const;

const STORAGE_KEY = "paper-agent-flow-nav-collapsed";

export default function ProjectNav({ children }: { children?: ReactNode }) {
  const { id } = useParams();
  const loc = useLocation();
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [collapsed]);

  if (!id) return children ? <>{children}</> : null;

  const selected =
    FLOW_ITEMS.find(
      (i) =>
        (i.key === "overview" && loc.pathname === `/projects/${id}`) ||
        (i.path && loc.pathname.endsWith(`/${i.path}`))
    )?.key || "overview";

  const rail = (
    <aside className={`flow-rail${collapsed ? " is-collapsed" : ""}`} aria-label="成稿流程">
      <div className="flow-rail-head">
        {!collapsed ? <span className="flow-rail-title">成稿</span> : <span className="flow-rail-title-dot" />}
        <button
          type="button"
          className="flow-rail-toggle"
          aria-expanded={!collapsed}
          aria-label={collapsed ? "展开流程导航" : "折叠流程导航"}
          title={collapsed ? "展开" : "折叠"}
          onClick={() => setCollapsed((v) => !v)}
        >
          {collapsed ? "»" : "«"}
        </button>
      </div>
      <nav className="flow-rail-nav">
        {FLOW_ITEMS.map((item, idx) => {
          const to = item.path ? `/projects/${id}/${item.path}` : `/projects/${id}`;
          const active = selected === item.key;
          return (
            <Link
              key={item.key}
              to={to}
              className={`flow-rail-item${active ? " is-active" : ""}`}
              title={item.label}
              aria-current={active ? "page" : undefined}
            >
              <span className="flow-rail-dot" aria-hidden>
                <span className="flow-rail-dot-core" />
                {idx < FLOW_ITEMS.length - 1 ? <span className="flow-rail-line" /> : null}
              </span>
              {!collapsed ? <span className="flow-rail-label">{item.label}</span> : null}
            </Link>
          );
        })}
      </nav>
    </aside>
  );

  if (!children) return rail;

  return (
    <div className={`project-workbench${collapsed ? " is-collapsed" : ""}`}>
      {rail}
      <div className="project-workbench-body">{children}</div>
    </div>
  );
}
