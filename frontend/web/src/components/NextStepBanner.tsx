import { Alert, Button } from "antd";
import { Link } from "react-router-dom";

type NextStep = {
  code?: string;
  path?: string;
  label?: string;
  reason?: string;
};

export default function NextStepBanner({
  projectId,
  next,
}: {
  projectId?: string;
  next?: NextStep | null;
}) {
  if (!projectId || !next?.path || !next.label) return null;
  return (
    <Alert
      showIcon
      type="success"
      style={{ marginBottom: 16 }}
      message={`下一步：${next.label}`}
      description={next.reason}
      action={
        <Link to={`/projects/${projectId}/${next.path}`}>
          <Button type="primary" size="small">
            去完成
          </Button>
        </Link>
      }
    />
  );
}
