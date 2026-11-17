import { ScrollView, View, Text } from "@tarojs/components";
import Taro, { useRouter } from "@tarojs/taro";

const STEPS = [
  { page: "project", label: "概览" },
  { page: "search", label: "检索" },
  { page: "outline", label: "大纲" },
  { page: "editor", label: "写作" },
  { page: "polish", label: "润色" },
  { page: "citations", label: "核查" },
  { page: "export", label: "导出" },
];

export default function FlowNav({ projectId }: { projectId: string }) {
  const route = useRouter().path || "";
  const current = STEPS.find((s) => route.includes(`/pages/${s.page}/`))?.page || "project";

  return (
    <View className="flow-bar-wrap">
      <ScrollView scrollX className="flow-bar" showScrollbar={false}>
        {STEPS.map((s) => {
          const on = current === s.page;
          return (
            <Text
              key={s.page}
              className={`flow-chip ${on ? "on" : ""}`}
              style={{
                backgroundColor: on ? "#0f3d2e" : "#ffffff",
                color: on ? "#ffffff" : "#6a7d74",
                borderColor: on ? "#0f3d2e" : "#e3ebe6",
                fontWeight: on ? 600 : 400,
              }}
              onClick={() =>
                Taro.redirectTo({
                  url: `/pages/${s.page}/index?id=${encodeURIComponent(projectId)}`,
                }).catch(() =>
                  Taro.navigateTo({
                    url: `/pages/${s.page}/index?id=${encodeURIComponent(projectId)}`,
                  })
                )
              }
            >
              {s.label}
            </Text>
          );
        })}
      </ScrollView>
    </View>
  );
}
