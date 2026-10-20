# Domain Docs

工程类 skills 在探索代码库时应如何使用本仓库的领域文档。

## 探索前必读

- 根目录的 **`GLOSSARY.md`**（若存在）
- **`docs/architecture/adr/`**：阅读与即将进行的工作相关的 ADR（见 `docs/architecture/adr/README.md`）

如果上述任何文件不存在，**静默继续**。不要提示它们缺失，也不要提前建议创建。`/domain-modeling` skill（可通过 `/grill-with-docs` 和 `/improve-codebase-architecture` 调用）会在术语或决策实际确定时按需延迟创建。

## 文件结构

单上下文仓库（Single-context repo，适用于绝大多数仓库）：

```
/
├── GLOSSARY.md
├── docs/architecture/adr/
│   ├── 001-xxx.md
│   └── README.md
└── packages/ / apps/
```

## 遵循术语表（Glossary）中的词汇

当你的输出涉及到领域概念时（包括 issue 标题、重构方案、假设、测试用例名称等），必须使用 `GLOSSARY.md` 中定义的术语。严禁擅自使用术语表明确避免的同义词。

如果你需要的概念尚未收录在术语表中，这是一个信号：要么你引入了该项目未使用的表述（请重新考虑），要么确实存在定义缺失（记录下来以便后续由 `/domain-modeling` 补充）。

## 明确指出与 ADR 的冲突

如果你的输出与现有的 ADR 发生冲突，请显式提出，而非静默覆盖：

> _与 ADR-0005 (LLM integration and privacy) 存在冲突，但值得重新讨论，原因为……_
