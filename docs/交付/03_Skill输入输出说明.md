# Skill 输入输出说明（S1～S10 + polish）

与需求规格说明书附录 B、`AGENTS.md`「最低 Skill」一致。每个 Skill 在 `backend/tests/skills/` 有独立测试；工作流调通不能代替独立测试。

统一包装：`SkillRequest` / `SkillResult`（见 API 与 Skill 接口设计说明书）。业务调用也可走 `POST /api/v1/skills/invoke`，body 含 `skill_code` 与 `input`。

| Skill | 代码 | 典型输入 | 通过条件（摘要） |
| --- | --- | --- | --- |
| S1 主题结构化 | `S1` / `s1_topic` | 一段研究主题 | 返回主题名称、研究对象、关键词、问题边界等结构，非自由散文 |
| S2 文献检索 | `S2` / `s2_retrieve` | 中文或英文关键词 | 每条文献均在公用库，含论文标识、题名、作者、年份等来源 |
| S3 论文解析 | `S3` / `s3_parse` | 文本型 PDF | 提取正文与章节树；验收样例须识别出章节 |
| S4 多篇对比 | `S4` / `s4_compare` | 2～8 篇已索引 `paper_ids` | 带证据的对比；空缺填「库内未找到」 |
| S5 方向分类 | `S5` / `s5_classify` | 一组已索引论文 | 形成研究方向分类，每类列出依据论文 |
| S6 研究空白 | `S6` / `s6_gap` | 研究现状文本，可选 `paper_ids` | 候选空白为「建议」类型，有证据或标明证据不足 |
| S7 大纲 | `S7` / `s7_outline` | 研究目标 | 可编辑一至三级标题与写作意图；`confirmed=false` 直至用户确认 |
| S8 章节写作 | `S8` / `s8_write` | 章节要求，且大纲已确认 | 正式引用回链库内论文与证据片段 |
| S9 论文检查 | `S9` / `s9_check` | 项目正文 | 列出 L1/L2 未通过句与逻辑问题 |
| S10 文档导出 | `S10` / `s10_export` | 项目 + 草稿/定稿 | 可打开的 DOCX（有正文）与 PDF（`%PDF` 开头非空）；定稿受引用闸门约束 |
| 润色 | `polish` | 正文片段 + 档位 | 对照可确认；不改数字/专名/引用/结论方向；降重请求拒绝 |

## 闸门与步数

- 大纲未确认：不可批量生成章节、不可定稿。  
- 定稿：全部正式引用须通过 L1+L2。  
- 主控：有限状态机；单节点最多重试 2 次；单任务最多 12 步。  
- 界面展示当前 Skill 名称；任务记录输入摘要、模型、耗时、token、结果/错误。

## 模块位置

```text
backend/app/skills/     s1_topic … s10_export、polish
backend/prompts/        按 Skill 分目录的 Prompt 版本
backend/tests/skills/   独立测试（勿把工作流测试放这里充数）
```
