import { View, Text } from "@tarojs/components";
import { switchPage } from "../utils/navigate";

type TabKey = "home" | "library" | "tools";

const TABS: { key: TabKey; path: string; label: string }[] = [
  { key: "home", path: "/pages/home/index", label: "项目" },
  { key: "library", path: "/pages/library/index", label: "知识库" },
  { key: "tools", path: "/pages/tools/index", label: "分析" },
];

export default function BottomTab({ active }: { active: TabKey }) {
  return (
    <View className="tabbar">
      {TABS.map((t) => {
        const on = t.key === active;
        return (
          <View
            key={t.key}
            className={`tabbar-item ${on ? "on" : ""}`}
            style={{ color: on ? "#0f3d2e" : "#6a7d74", fontWeight: on ? 700 : 400 }}
            hoverClass="tabbar-item-hover"
            onClick={() => {
              if (on) return;
              switchPage(t.path);
            }}
          >
            <View
              className="tabbar-icon"
              style={{ backgroundColor: on ? "#0f3d2e" : "#e7efe9" }}
            >
              <View
                style={{
                  width: 14,
                  height: 14,
                  margin: "15px auto",
                  borderRadius: "50%",
                  backgroundColor: on ? "#ffffff" : "#6a7d74",
                }}
              />
            </View>
            <Text style={{ color: on ? "#0f3d2e" : "#6a7d74" }}>{t.label}</Text>
          </View>
        );
      })}
    </View>
  );
}
