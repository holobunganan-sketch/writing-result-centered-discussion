# Result-Centered Discussion Skill v2.0.0

用于 Codex 从本地论文项目中构建以研究结果为主线的 Discussion。系统将研究结果、外部文献证据、段落论证和最终文字分层管理，阻止无功能引用、文献罗列、来源幻觉、因果越界和绕过审计的最终输出。

## 安装

要求 Python 3.10 或更高版本。

```powershell
python -m pip install -r requirements.txt
python .\install.py --force
```

默认安装目录：

```text
%USERPROFILE%\.codex\skills\writing-result-centered-discussion
```

完整 Office/PDF、混合检索和 OCR 能力：

```powershell
python -m pip install -r requirements-optional.txt
```

OCR 还需要系统安装 Tesseract 和 Poppler。

## 推荐目录

```text
project/
├── manuscript.docx
├── results/
│   ├── results.docx
│   └── tables.xlsx
├── protocol/
├── references/
│   ├── paper-a.pdf
│   ├── paper-b.pdf
│   └── library.bib
└── notes/
```

文件角色在 `.discussion-workspace/config.json` 中配置：

- `study-evidence`：本研究 Results、表格、图和论文正文；
- `external-evidence`：拟引用的外部文献；
- `context-only`：方案、背景资料和笔记；
- `excluded_globs`：旧稿、重复文件、临时文件和禁止使用的资料。

## 核心命令

```bash
python scripts/discussion.py --project <项目> init
python scripts/discussion.py --project <项目> index
python scripts/discussion.py --project <项目> search-result --result-id R1
python scripts/discussion.py --project <项目> seal-card --id REF-001
python scripts/discussion.py --project <项目> validate
python scripts/discussion.py --project <项目> semantic-audit-init
python scripts/discussion.py --project <项目> audit
python scripts/discussion.py --project <项目> compile --citation-mode key
```

其他命令：

```bash
# 检查索引是否因文件变化而过期
python scripts/discussion.py --project <项目> freshness

# 生成 BibTeX、RIS、EndNote XML 映射
python scripts/discussion.py --project <项目> citation-registry

# 导出 claim 级证据矩阵和可比性矩阵
python scripts/discussion.py --project <项目> export-matrix
python scripts/discussion.py --project <项目> export-comparability

# 将旧版工作区迁移到 v2；所有来源摘录仍需人工重新核验
python scripts/discussion.py --project <项目> migrate-v1

# 把已有 Discussion 拆成待审计段落
python scripts/discussion.py --project <项目> revision-intake --draft old-discussion.docx

# 将通过发布门的 Discussion 追加到原稿副本
python scripts/discussion.py --project <项目> write-docx --manuscript manuscript.docx
```

## v2 关键机制

- 正式 JSON Schema 校验，拒绝额外字段和不完整结构；
- 外部证据池与本研究证据池强隔离；
- BM25、字符级 TF-IDF、项目术语扩展和可比性重排；
- DOI、PMID、文件哈希去重，优先保留正式发表版本；
- claim 级来源哈希、原文定位、摘录和摘录哈希；
- 研究可比性矩阵与证据冲突图；
- 中英文因果措辞审计；
- 结构化 Codex 语义审计和引用删除测试；
- 增量索引；
- 期刊 Discussion 总字数、段落字数和段落数限制；
- 每次编译重新执行全部门控并原子写入最终文件。

## 测试

```bash
python scripts/check_package.py
python -m unittest discover -s tests -v
python -m compileall -q scripts
```
