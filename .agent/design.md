# .agent/design.md — 视觉设计规范

> 深色专业法务风格。本文件不是安全红线；实现 UI 时遵循，变更需在 `plan.md` 记录。

## 色彩

- 策略 Restrained：暖调墨黑基底（hue 32，饱和度 8–12%）+ 单一琥珀金强调色（hue 36, 78%, 56%），强调色占比约 10%。
- 风险语义色：高风险 `hsl(4 70% 52%)`、中风险 `hsl(32 82% 55%)`、低风险 `hsl(152 46% 44%)`，仅用于风险标注与统计数字。

## 字体与组件

- 字体：正文 Sora，标题 Noto Serif SC；数字启用 `tabular-nums`。
- 组件：radius `0.375rem`，边框优先于阴影；卡片用 `border-border/70 + bg-card`；辅助纹理用 paper-grid 与 amber-glow。
- Outline 按钮必须带 `!bg-transparent hover:!bg-transparent`；按钮文字与背景必须强对比，禁止同色。

## 禁用

渐变文字、蓝紫渐变、玻璃拟态默认面板、霓虹深色配色、左侧色条边框。
