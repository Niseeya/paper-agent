import { View, Text } from "@tarojs/components";
import { CSSProperties, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

type Props = {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: Variant;
  /** 兼容旧写法：className="btn secondary" / `btn ${loading ? "disabled" : ""}` */
  className?: string;
  style?: CSSProperties;
};

const BG: Record<Variant, CSSProperties> = {
  primary: { backgroundColor: "#0f3d2e" },
  secondary: { backgroundColor: "#e7efe9" },
  ghost: {
    backgroundColor: "transparent",
    borderWidth: 2,
    borderStyle: "solid",
    borderColor: "#c5d6cc",
  },
};

const FG: Record<Variant, string> = {
  primary: "#ffffff",
  secondary: "#0f3d2e",
  ghost: "#1f5c45",
};

function resolveVariant(variant: Variant | undefined, className: string): Variant {
  if (variant) return variant;
  if (/\bsecondary\b/.test(className)) return "secondary";
  if (/\bghost\b/.test(className)) return "ghost";
  return "primary";
}

/** 作为各页 Button 使用：内联实色，避免小程序白底扁平按钮 */
export default function TapButton({
  children,
  onClick,
  disabled,
  variant,
  className = "",
  style,
}: Props) {
  const v = resolveVariant(variant, className);
  const isDisabled = !!disabled || /\bdisabled\b/.test(className);

  return (
    <View
      className={`tap-btn${isDisabled ? " disabled" : ""}`}
      style={{
        ...BG[v],
        opacity: isDisabled ? 0.45 : 1,
        ...style,
      }}
      hoverClass={isDisabled ? undefined : "tap-btn-hover"}
      hoverStayTime={80}
      onClick={() => {
        if (isDisabled) return;
        onClick?.();
      }}
    >
      <Text className="tap-btn-text" style={{ color: FG[v] }}>
        {children}
      </Text>
    </View>
  );
}
