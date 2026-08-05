# 示例项目布局

```text
study-project/
├── manuscript.docx
├── results.md
├── tables.xlsx
├── protocol.pdf
├── references/
│   ├── direct-comparator-1.pdf
│   ├── direct-comparator-2.pdf
│   ├── mechanism-study.pdf
│   └── guideline.pdf
└── .discussion-workspace/
```

索引脚本只读取源项目文件，不修改论文和参考文献。所有结构化中间产物保存在 `.discussion-workspace`。
