import { useState } from "react";
import { View, Text, Input } from "@tarojs/components";
import Taro, { useDidShow } from "@tarojs/taro";
import Button from "../../components/TapButton";
import { api } from "../../services/client";
import { useAuthStore } from "../../store/auth";
import { toast } from "../../utils/config";

const IS_WEAPP = process.env.TARO_ENV === "weapp";

export default function LoginPage() {
  const setAuth = useAuthStore((s) => s.setAuth);
  const hydrate = useAuthStore((s) => s.hydrate);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useDidShow(() => {
    hydrate();
    if (useAuthStore.getState().token) {
      Taro.reLaunch({ url: "/pages/home/index" });
    }
  });

  async function submit() {
    if (!username.trim() || !password) {
      setError("请填写用户名和密码");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const body: Record<string, string> = { username: username.trim(), password };
      if (mode === "register" && displayName.trim()) body.display_name = displayName.trim();
      const res = await api.post(path, body);
      setAuth(res.data.token, res.data.user);
      toast("成功", "success");
      Taro.reLaunch({ url: "/pages/home/index" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "失败");
    } finally {
      setLoading(false);
    }
  }

  const actionLabel = loading ? "请稍候…" : mode === "login" ? "登录" : "注册并进入";

  // 微信小程序：单元格表单 + View 按钮（原生 button 易被压扁）
  if (IS_WEAPP) {
    return (
      <View className="mp-login">
        <View className="mp-login-brand">
          <Text className="mp-login-title">论文智能体</Text>
          <Text className="mp-login-sub">证据约束下的检索、大纲、写作与导出</Text>
        </View>

        <View className="mp-tabs">
          <View className={`mp-tab ${mode === "login" ? "on" : ""}`} onClick={() => setMode("login")}>
            <Text className="mp-tab-text">登录</Text>
          </View>
          <View
            className={`mp-tab ${mode === "register" ? "on" : ""}`}
            onClick={() => setMode("register")}
          >
            <Text className="mp-tab-text">注册</Text>
          </View>
        </View>

        {error ? <Text className="error mp-login-error">{error}</Text> : null}

        <View className="mp-form">
          <View className="mp-cell">
            <Text className="mp-label">账号</Text>
            <Input
              className="mp-input"
              placeholder="请输入用户名"
              placeholderClass="field-placeholder"
              value={username}
              onInput={(e) => setUsername(e.detail.value)}
            />
          </View>
          {mode === "register" ? (
            <View className="mp-cell">
              <Text className="mp-label">昵称</Text>
              <Input
                className="mp-input"
                placeholder="可选"
                placeholderClass="field-placeholder"
                value={displayName}
                onInput={(e) => setDisplayName(e.detail.value)}
              />
            </View>
          ) : null}
          <View className="mp-cell">
            <Text className="mp-label">密码</Text>
            <Input
              className="mp-input"
              password
              placeholder="请输入密码"
              placeholderClass="field-placeholder"
              value={password}
              onInput={(e) => setPassword(e.detail.value)}
            />
          </View>
        </View>

        <View className="mp-login-action">
          <Button disabled={loading} onClick={submit}>
            {actionLabel}
          </Button>
        </View>
        <Text className="mp-login-hint">管理后台仅 Web 端提供</Text>
      </View>
    );
  }

  // H5 / Android WebView：保持原登录布局与原生 Button
  return (
    <View className="login-screen">
      <View className="login-hero">
        <View className="brand">论文智能体</View>
        <View className="desc">
          证据约束下的检索、大纲、写作与导出。正式引用须回链公用知识库。
        </View>
      </View>

      <View className="login-sheet">
        <View className="segment">
          <Text
            className={`segment-item ${mode === "login" ? "on" : ""}`}
            onClick={() => setMode("login")}
          >
            登录
          </Text>
          <Text
            className={`segment-item ${mode === "register" ? "on" : ""}`}
            onClick={() => setMode("register")}
          >
            注册
          </Text>
        </View>

        {error ? <Text className="error">{error}</Text> : null}

        <View className="field">
          <Input
            className="field-input"
            placeholder="用户名"
            placeholderClass="field-placeholder"
            value={username}
            onInput={(e) => setUsername(e.detail.value)}
          />
        </View>
        {mode === "register" ? (
          <View className="field">
            <Input
              className="field-input"
              placeholder="显示名（可选）"
              placeholderClass="field-placeholder"
              value={displayName}
              onInput={(e) => setDisplayName(e.detail.value)}
            />
          </View>
        ) : null}
        <View className="field">
          <Input
            className="field-input"
            password
            placeholder="密码"
            placeholderClass="field-placeholder"
            value={password}
            onInput={(e) => setPassword(e.detail.value)}
          />
        </View>

        <Button className={`btn ${loading ? "disabled" : ""}`} onClick={submit} disabled={loading}>
          {actionLabel}
        </Button>
        <View className="hint" style={{ marginTop: 20, textAlign: "center" }}>
          管理后台仅 Web 端提供
        </View>
      </View>
    </View>
  );
}
