# 研究结果驱动的 Discussion 写作 Skill

该 Skill 用于 Codex 在项目目录中读取研究结果和预先准备的参考文献，构建以本研究结果为主轴的 Discussion。它通过本地全文索引、结果账本、证据卡、段落论证契约和自动审计限制无意义信息拼接与无功能引用。

## 安装

解压 ZIP，进入解压后的目录，在 PowerShell 或终端运行：

```powershell
python .\install.py --force
```

默认安装到：

```text
%CODEX_HOME%\skills\writing-result-centered-discussion
```

未设置 `CODEX_HOME` 时使用：

```text
%USERPROFILE%\.codex\skills\writing-result-centered-discussion
```

指定其他目录：

```powershell
python .\install.py --target "D:\CodexSkills" --force
```

安装后重启 Codex。自动发现未生效时，可把 `integration/AGENTS.md.snippet` 的内容加入项目 `AGENTS.md`，并修正 Skill 路径。

## 推荐项目结构

```text
project/
├── manuscript.docx
├── results/
│   ├── results.docx
│   ├── tables.xlsx
│   └── figures/
├── protocol/
├── references/
│   ├── study-a.pdf
│   ├── study-b.pdf
│   └── review-c.pdf
└── notes/
```

无需严格采用该结构。索引器会递归扫描支持的文件类型，并忽略 `.git`、`node_modules` 和 `.discussion-workspace`。

## 使用

在 Codex 中直接提出任务，例如：

```text
使用 writing-result-centered-discussion Skill，读取本项目的 Results 和 references 目录，先构建结果账本、证据矩阵、Discussion 主线和段落契约。通过验证后再起草 Discussion。
```

核心命令：

```bash
python scripts/discussion.py --project <项目目录> init
python scripts/discussion.py --project <项目目录> index
python scripts/discussion.py --project <项目目录> search-result --result-id R1
python scripts/discussion.py --project <项目目录> validate
python scripts/discussion.py --project <项目目录> audit
python scripts/discussion.py --project <项目目录> compile --citation-mode key
```

## 本地索引能力

支持直接读取：

- Markdown、TXT、CSV、TSV、JSON、YAML、XML、HTML、TeX、BibTeX、RIS；
- DOCX、PPTX、XLSX；
- 可提取文本的 PDF。

PDF 优先使用 `pypdf`，其次调用系统 `pdftotext`。两者均不可用或 PDF 为扫描件时，索引清单会把文件标记为不可读。此时需要安装 `pypdf`、安装 Poppler，或提供可搜索文本版 PDF。

可选安装：

```bash
python -m pip install pypdf
```

索引检索使用本地 BM25，不向外部服务上传项目文件。中文检索使用汉字单字和双字组合，英文检索使用词项。

## 工作区

运行后在论文项目中生成：

```text
.discussion-workspace/
├── project_inventory.json
├── result_ledger.json
├── index/
├── candidate_searches/
├── evidence_cards/
├── evidence_matrix.csv
├── argument_map.json
├── paragraph_contracts/
├── discussion_trace.md
├── validation_report.json
├── audit_report.json
└── discussion_final.md
```

该目录保存全部推理结构和来源追踪。最终投稿文本位于 `discussion_final.md`。

## 引用输出

`compile` 支持三种模式：

- `key`：把 `[REF-001]` 转换为 `[@CitationKey]`；
- `rendered`：使用证据卡中的 `rendered_citation`；
- `keep`：保留 `[REF-001]`，便于后续人工处理。

## 自动化测试

```bash
python scripts/discussion.py --project . selftest
```

测试覆盖本地索引排序、证据追溯验证、段落契约验证、越权引用审计和最终稿编译。`evals/` 中包含需要在 Codex 会话中运行的行为评估场景。
