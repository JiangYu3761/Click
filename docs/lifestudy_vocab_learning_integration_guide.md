# Life-study Vocabulary Learning and Integration Guide

Updated: 2026-06-29

## 一句话结论

现在不是“33,724 个词都已经确定翻译好了”。

当前正确口径是：

- 学习用总单词本：1 个，33,724 个词。
- 已确定可进前台查词的 Life-study 语境词：基础 A 级词 34 个；当前已应用到 Life-study domain glossary 的 active 前台词条为 100 个。
- 有中文文档证据、较适合下一轮审核的候选词：6,321 个，其中 4,116 个已自动归入学习候选，2,205 个不确定词已完成同条中英证据二审。
- 粗候选线索：27,369 个。

所以这个系统现在有两个层次：

1. 学习层：给人看、给后续审核用，覆盖 51 卷全量词。
2. 前台词典层：只给用户查词时直接展示，必须严格审核；当前 Life-study domain glossary 已有 100 个 active 词条，其中最新 15 个来自 2,205 needs-review 二审结果。

不要再把这两层混在一起。

## 关键文件

### 1. 学习用总单词本

主文件：

`reports/lifestudy_vocab_corpus/lifestudy_all_words_chinese_context_candidates.csv`

用途：

- 后续学习
- 人工审核
- 找高频词
- 找中文上下文候选义
- 决定哪些词可以升级进系统前台

当前数量：

- 总行数：33,724
- 每行一个清洗后的英文词或 lemma group
- 每行保留英文证据句、中文证据句、出处卷、页码

这个文件不是正式前台词典，不应该直接批量导入。

### 2. 原始全量词频总表

文件：

`reports/lifestudy_vocab_corpus/lifestudy_all_words_master.csv`

用途：

- 看 51 卷原始英文词频
- 看来源卷、页码、证据句
- 保留最初的全量统计口径

当前数量：

- 原始归一化英文词：38,166
- 原始英文 token：5,297,307
- 内容词 token：2,521,585

### 3. 清洗后全量词表

文件：

`reports/lifestudy_vocab_corpus/lifestudy_clean_all_words_master.csv`

用途：

- 去掉停用词、噪声、明显 OCR 残留后的全量词表
- 作为后续审核和候选义生成的基础

当前数量：

- Clean lemma groups：33,724
- 剔除噪声：864
- 合并词形变体：3,578

### 4. Top 500 审核队列

文件：

`reports/lifestudy_vocab_corpus/lifestudy_vocab_top500_queue.csv`

用途：

- 优先审核最有价值的 500 个词
- 包含高频、领域词、普通词典容易误解的词

当前数量：

- Top 500：500
- 自动通过：34
- 待审：466

### 5. 当前正式可入库词

文件：

`reports/lifestudy_vocab_corpus/lifestudy_vocab_v1_importable.csv`

用途：

- 只放已经审核通过、可以进前台的词

当前数量：

- 34 个 A 级词条

例子：

- `economy -> 经纶`
- `dispensing -> 分赐`
- `mingled -> 调和`

## 数字口径

| 层级 | 数量 | 用途 | 是否可直接进前台 |
| --- | ---: | --- | --- |
| 原始归一化英文词 | 38,166 | 全量统计 | 不可以 |
| 清洗后学习词表 | 33,724 | 学习、审核、候选义 | 不可以 |
| 中文文档候选义总表 | 33,724 | 后续学习和审核主表 | 不可以 |
| 词典辅助且命中中文上下文 | 6,321 | 下一轮重点审核；已拆成 4,116 自动学习候选和 2,205 二审结果 | 不可以，需前台级单独审核 |
| 统计中文上下文候选 | 27,369 | 线索 | 不可以 |
| 基础 A 级已确认词 | 34 | 前台查词基础批次 | 可以 |
| 当前 active Life-study domain glossary | 100 | Mac/iPad 查词实际可用词条 | 已应用 |

## 中文候选义怎么来的

主表：

`lifestudy_all_words_chinese_context_candidates.csv`

里面的核心字段：

| 字段 | 意思 |
| --- | --- |
| `word` | 英文词 |
| `lemma` | 归一化词 |
| `variant_words` | 词形变体 |
| `total_content_frequency` | 内容词频 |
| `volume_count` | 出现卷数 |
| `draft_meaning_zh_from_chinese_context` | 从中文生命读经证据句里得到的候选中文义 |
| `candidate_source` | 候选义来源 |
| `candidate_confidence` | 候选置信度 |
| `review_decision` | 当前审核状态 |
| `import_ready` | 是否可入库 |
| `source_volume` | 来源卷 |
| `source_page` | 来源页 |
| `evidence_en` | 英文证据句 |
| `evidence_zh_simp` | 中文证据句 |

候选来源有三类：

| source | 含义 | 当前数量 | 怎么用 |
| --- | --- | ---: | --- |
| `known_term_found_in_chinese_context` | 已知 Life-study 术语，并在中文上下文中命中 | 34 | 可以进入前台 |
| `dictionary_guided_term_found_in_chinese_context` | 本地词典给出中文候选，且该中文词确实出现在生命读经中文证据句里 | 6,321 | 已完成学习层二审；仍不能直接进前台 |
| `statistical_chinese_context_candidate` | 从中文上下文统计抽出的候选短语 | 27,369 | 只作为线索 |

注意：

本地词典只用来帮助定位中文候选词。最终仍要求候选词出现在生命读经中文证据句里。不能把普通词典释义直接当 Life-study 语境义。

## 学习时怎么用

### 第一阶段：先看 34 个确定词

目的：

- 熟悉 Life-study 专属术语
- 建立前台查词的基准
- 确认这些词在阅读时显示正确

看这个文件：

`lifestudy_vocab_v1_importable.csv`

### 第二阶段：看 6,321 个较靠谱候选

筛选条件：

- `candidate_source = dictionary_guided_term_found_in_chinese_context`
- `candidate_confidence = medium`
- `total_content_frequency` 从高到低

目的：

- 扩大个人学习词库
- 找出真正应该进入系统前台的词

判断标准：

1. 英文词在英文证据句里清楚出现。
2. 中文候选义在中文证据句里清楚出现。
3. 这个中文候选义确实是在翻译这个英文词，而不是同一句里碰巧出现。
4. 如果一个词有多个常见义，必须写清楚语境条件。

### 第二阶段补充：2,205 个不确定词二审结果

本轮只处理这个文件：

`reports/lifestudy_vocab_corpus/lifestudy_dictionary_guided_review_v2_needs_manual_review.csv`

输入数量：

- 2,205 行
- 全部来自 `learning_review_decision = needs_manual_review`
- 不包含 26 个前台词
- 不包含 4,116 个已初审通过学习候选

二审输出：

| 文件 | 数量 | 用途 |
| --- | ---: | --- |
| `lifestudy_needs_review_adjudication_v1.csv` | 2,205 | 2,205 个不确定词的完整裁定表 |
| `lifestudy_needs_review_corrected_learning_candidate.csv` | 3 | 原候选义错位，但可由同条中文证据修正 |
| `lifestudy_needs_review_learning_only.csv` | 2,197 | 可作为学习词表材料，不进入前台正式词典 |
| `lifestudy_needs_review_reject.csv` | 5 | 页眉噪声、候选义过泛或证据不支持 |
| `lifestudy_needs_review_still_needs_manual_review.csv` | 0 | 当前没有剩余待审项 |

已修正的 3 个例子：

- `sermon -> 讲道`
- `misused -> 误用`
- `siloam -> 西罗亚`

注意：

这 2,205 条现在只是学习层裁定结果。它们没有写入 PostgreSQL，没有进入前台查词，也没有污染 `reader.dictionary_entries`。如果以后要把其中一部分升级进前台，必须另建前台级审核队列、dry-run、显式 apply。

### 第二阶段补充：2,205 派生前台第一批

当前已经完成第一批前台化，但不是把 2,205 全量入库。

输入只来自：

- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_corrected_learning_candidate.csv`
- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_learning_only.csv`

明确没有读取：

- 5 个 reject
- 0 个 still-needs-manual-review
- 26 个旧前台词
- 4,116 个已初审通过学习候选

本批流程：

| 步骤 | 数量 | 文件 |
| --- | ---: | --- |
| 可用学习来源 | 2,200 | corrected + learning_only |
| Top 前台队列 | 300 | `lifestudy_needs_review_frontend_queue_top300.csv` |
| 队列级前台候选 | 20 | `lifestudy_needs_review_frontend_queue_candidates.csv` |
| 前台级通过 | 15 | `lifestudy_needs_review_frontend_ready_for_dry_run.csv` |
| 实际写入 Life-study domain glossary | 15 | `reader.domain_glossary_entries` |
| 写入普通词典 | 0 | 不允许 |

已经应用的 15 个词：

| word | meaning |
| --- | --- |
| `authority` | 权柄 |
| `vision` | 异象 |
| `ascension` | 升天 |
| `parable` | 比喻 |
| `misused` | 误用 |
| `holy` | 神圣的 |
| `building` | 建筑 |
| `riches` | 财富 |
| `pray` | 祈祷 |
| `peace` | 和平 |
| `prayer` | 祈祷 |
| `testify` | 作证 |
| `function` | 功能 |
| `local` | 地方性的 |
| `preach` | 讲道 |

这 15 个是 B 级前台词条，写入位置是 `reader.domain_glossary_entries`，`source_title` 为 `Life-study Needs-review Frontend V1`。它们只在当前书被识别为 Life-study/生命读经时优先显示；普通书不会使用这些释义。

### 第三阶段：谨慎看 27,369 个粗候选

这部分不能当翻译看。

它的用途只是：

- 找线索
- 找高频词
- 找可能遗漏的领域词
- 给后续程序改进提供样本

## 系统接入原则

### 当前已经接入前台的是什么

当前前台只应该读取已审核词：

- 34 个 V1 A 级 Life-study 语境词
- 26 个旧前台 adjudicated B 级词
- 15 个 needs-review 派生 B 级词
- 已有 Genesis 受控短语词条

前台查词顺序：

1. 用户手动修正
2. 当前书 book glossary
3. Life-study domain glossary
4. 普通本地词典
5. 在线或其他 fallback

### 哪张表不能直接接前台

不能直接接：

`lifestudy_all_words_chinese_context_candidates.csv`

原因：

- 它是学习和审核表，不是正式词典。
- 里面 27,369 个统计候选可能有噪声。
- 6,321 个较靠谱候选仍然需要确认。

### 哪些数据可以接前台

只有满足这些条件才可以：

- `review_decision = approve` 或人工 correct 后 approve
- `import_ready = true`
- 有英文证据句
- 有中文证据句
- 有卷和页
- 不覆盖用户手动修正
- 不写入 `reader.dictionary_entries`

目标表：

- `reader.domain_glossary_entries`
- 必要时同步到具体书的 `reader.book_glossary`
- 必要时同步到 `reader.book_vocab_items`

禁止污染：

- `reader.dictionary_entries`

## 后续扩充流程

### 推荐下一步

不要从 33,724 个词开始审核。

正确顺序：

1. 从 6,321 个 dictionary-guided 候选里筛选。
2. 先按词频排序，取 Top 300。
3. 用证据句自动做二审。
4. 输出 `approve / correct / reject` 审核包。
5. 只把通过的词显式 dry-run。
6. 确认无污染后再 apply。

### 审核结果分级

| 结果 | 含义 | 是否入库 |
| --- | --- | --- |
| approve | 中文候选义准确 | 可以 |
| correct | 候选义方向对，但需要修正 | 修正后可以 |
| reject | 不是这个词的意思，或证据不足 | 不可以 |
| needs_review | 还不能判断 | 不可以 |

## 验收命令

全量中文候选义表：

```bash
.venv-reader-api/bin/python scripts/lifestudy_all_words_chinese_context_candidates_smoke.py
```

V1 安全入库边界：

```bash
.venv-reader-api/bin/python scripts/lifestudy_context_vocab_v1_apply_smoke.py
```

前台 live lookup：

```bash
.venv-reader-api/bin/python scripts/lifestudy_context_vocab_v1_live_lookup_smoke.py
```

完整产品验收仍然看：

```bash
./scripts/v1_acceptance.sh
./scripts/v21_ipad_lan_acceptance.sh
```

## 绝对不要做

1. 不要把 33,724 个词直接入库。
2. 不要把 6,321 个候选词直接显示到前台。
3. 不要把统计候选当作确定翻译。
4. 不要把普通词典释义直接当 Life-study 语境义。
5. 不要写入 `reader.dictionary_entries`。
6. 不要覆盖用户手动修正。
7. 不要为了数量牺牲证据。

## 当前可确认结果

现在可以确认：

- 51 卷生命读经全量英文词已经汇总。
- 全量学习单词本已经生成。
- 每个清洗词都有中文文档候选义或中文上下文候选线索。
- 34 个词已经严格确认并进入前台安全词典。
- 6,321 个词是下一轮最值得审核的候选。
- 27,369 个词只能作为粗线索。

当前不能声称：

- 33,724 个词都已经翻译准确。
- 6,321 个词都可以直接进前台。
- 统计候选就是中文释义。

## 下一阶段建议

下一阶段应该叫：

`Life-study Vocabulary Review V2`

目标：

- 审核 6,321 个 dictionary-guided 候选中的高频前 300-500 个。
- 生成新的 reviewed importable pack。
- 把通过审核的词分批写入 Life-study 专属 domain glossary。
- 前台继续只显示审核通过的词。

这才是从“学习单词本”走向“系统可用词典”的正确路径。

## Life-study Vocabulary Review V2 进度

2026-06-29 已开始审核 6,321 个 dictionary-guided 候选。

新增产物：

`reports/lifestudy_vocab_corpus/lifestudy_dictionary_guided_review_v2.csv`

拆分表：

- `lifestudy_dictionary_guided_review_v2_auto_accept_learning.csv`
- `lifestudy_dictionary_guided_review_v2_possible_frontend_after_human_review.csv`
- `lifestudy_dictionary_guided_review_v2_needs_manual_review.csv`

当前二审结果：

| 分类 | 数量 | 含义 | 是否进前台 |
| --- | ---: | --- | --- |
| auto_accept_learning_candidate | 4,116 | 可以作为学习用可信候选 | 不直接进 |
| needs_manual_review | 2,205 | 还需要人工确认 | 不进 |
| possible_frontend_after_human_review | 4,102 | 后续可做人审入库候选 | 人审后才可进 |
| learning_only_generic_word | 14 | 普通高频词，适合学习，不适合作 Life-study 前台优先义 | 不进 |

例子：

- `love -> 爱`：学习用可信候选。
- `world -> 世界`：学习用可信候选。
- `wonderful -> 奇妙的`：学习用可信候选。
- `things -> 局面`：候选义可疑，保留人工审。
- `message -> 教训`：低置信，保留人工审。
- `holy -> 神圣的`：看起来可能对，但证据命中次数不足，保留人工审。

这一轮仍然没有写数据库，`front_end_import_ready` 全部保持 `false`。

后续如果要进入系统前台，必须再做一个人工/规则审核包，把 `possible_frontend_after_human_review` 中的词显式改成 `approve/correct/reject`，然后 dry-run，再 apply。

## Needs-review Adjudication V1 进度

2026-06-29 已按用户要求只处理 2,205 个 `needs_manual_review`，不处理 26 个前台词，不处理 4,116 个已初审通过词。

源文件：

`reports/lifestudy_vocab_corpus/lifestudy_dictionary_guided_review_v2_needs_manual_review.csv`

规则：

- 中文义必须来自同条 `evidence_en` / `evidence_zh_simp` 对应证据。
- 允许英文变体命中，例如 `wave/waves`，但变体必须出现在同一条英文证据里。
- 普通词典只作为提示，不作为最终答案。
- 页眉、书名、信息标题造成的假命中拒绝。
- 过泛中文义拒绝。
- 不写 PostgreSQL，不进前台词典，不污染 `reader.dictionary_entries`。

新增产物：

- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_adjudication_v1.csv`
- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_adjudication_v1.json`
- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_adjudication_v1.md`
- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_adjudication_v1_summary.json`
- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_corrected_learning_candidate.csv`
- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_learning_only.csv`
- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_reject.csv`
- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_still_needs_manual_review.csv`

当前结果：

| 分类 | 数量 | 含义 |
| --- | ---: | --- |
| input | 2,205 | 原 needs_manual_review |
| adjudicated | 2,202 | 本轮已分流 |
| corrected_learning_candidate | 2 | 原候选义错位，但同条中文证据可修正 |
| learning_only | 2,195 | 同条中英证据支持，学习可用，但不进前台 |
| reject | 5 | 噪声、泛词或证据不支持 |
| still_needs_manual_review | 3 | 同条证据不足，需同页/相邻页补证 |

两条修正：

- `sermon`: `启示` 修正为 `讲道`
- `misused`: `使用` 修正为 `误用`

五条拒绝：

- `message -> 教训`：英文命中来自 `Life-Study ... Message` 页眉/标题噪声。
- `things -> 局面`
- `situation -> 情形`
- `case -> 情形`
- `stuff -> 东西`

仍待补证据的 3 条：

- `siloam`
- `cosmic`
- `moisture`

复验：

```bash
.venv-reader-api/bin/python scripts/lifestudy_needs_review_adjudication_v1_smoke.py
```

这一步完成的是学习词库分流，不是前台正式词典入库。

## Frontend Candidate Review V2 进度

2026-06-29 已从 4,102 个 `possible_frontend_after_human_review` 候选里生成更窄的前台候选人工审核包。

新增产物：

- `reports/lifestudy_vocab_corpus/lifestudy_frontend_candidate_review_v2_top500.csv`
- `reports/lifestudy_vocab_corpus/lifestudy_frontend_candidate_review_v2_approve_after_human_check.csv`
- `reports/lifestudy_vocab_corpus/lifestudy_frontend_candidate_review_v2_overrides_template.json`
- `reports/lifestudy_vocab_corpus/lifestudy_frontend_candidate_review_v2_overrides_template.csv`
- `reports/lifestudy_vocab_corpus/lifestudy_frontend_candidate_review_v2.md`

当前结果：

| 分类 | 数量 | 含义 | 是否入库 |
| --- | ---: | --- | --- |
| source rows | 4,102 | 学习可信候选中可能进入前台的一层 | 否 |
| top review rows | 500 | 优先人工审核的前台候选 | 否 |
| approve_after_human_check | 28 | 领域/神学倾向更强，建议人工确认 | 否 |
| needs_human_review | 472 | Top 500 中仍需人工判断 | 否 |
| front_end_import_ready | 0 | 本轮无任何正式入库 | 否 |

这 28 个不是已经入库的词，而是“值得你或系统下一轮重点确认”的词。

例子：

- `salvation -> 拯救`
- `grace -> 恩典`
- `glory -> 荣耀`
- `anointing -> 受膏`
- `priesthood -> 祭司职`
- `sanctuary -> 圣所`
- `consecration -> 奉献`

同时，脚本会把 `matter`、`therefore`、`actually` 这类高频普通词挡在前台候选之外，避免把学习词表污染成领域词库。

## Frontend Candidate Adjudication V2 进度

2026-06-29 已把上面 28 个候选做成 Codex 代理审核确定包。用户不需要逐条看表，本项目后续以这个确定包为第一批前台扩充依据。

新增产物：

- `reports/lifestudy_vocab_corpus/lifestudy_frontend_candidate_adjudication_v2.csv`
- `reports/lifestudy_vocab_corpus/lifestudy_frontend_candidate_adjudication_v2_ready_for_dry_run.csv`
- `reports/lifestudy_vocab_corpus/lifestudy_frontend_candidate_adjudication_v2.json`
- `reports/lifestudy_vocab_corpus/lifestudy_frontend_candidate_adjudication_v2.md`
- `reports/lifestudy_vocab_corpus/lifestudy_frontend_candidate_adjudication_v2_summary.json`

当前裁定结果：

| 分类 | 数量 | 含义 | 是否已入库 |
| --- | ---: | --- | --- |
| approve | 21 | 中文证据直接支持，释义可保留 | 否 |
| correct | 5 | 原候选方向对，但需修正中文义 | 否 |
| learning_only | 1 | 学习可用，但不适合作前台优先义 | 否 |
| needs_more_evidence | 1 | 证据不足以进入前台 | 否 |
| ready_for_dry_run | 26 | 下一步可进入受控 dry-run 候选包 | 否 |
| front_end_import_ready | 0 | 本轮仍不直接入库 | 否 |

本轮明确修正：

- `redemption`: `拯救` 改为 `救赎`
- `righteousness`: `公正` 改为 `公义`
- `reality`: `事实` 改为 `实际`
- `anointing`: `受膏` 改为 `受膏；膏油的涂抹`
- `priesthood`: `祭司职` 改为 `祭司职分`

本轮明确暂不进前台：

- `living -> 生活`：学习可用，但 living 多义，作为前台优先义容易误导。
- `sacrifice -> 牺牲`：当前证据支持牺牲，但 Life-study/圣经语境还可能是祭牲、祭物、祭；需要更多证据后再决定。

## Frontend Candidate Apply Boundary V2 进度

2026-06-29 已为这 26 个词建立受控 dry-run/apply 边界。

新增脚本：

- `scripts/lifestudy_frontend_candidate_adjudication_apply.py`
- `scripts/lifestudy_frontend_candidate_adjudication_apply_smoke.py`

当前 dry-run/apply 结果：

| 项目 | 数量/状态 |
| --- | ---: |
| dry-run candidates | 26 |
| dictionary pollution | 0 |
| explicit apply written | 26 |
| active Life-study domain terms before apply | 59 |
| active Life-study domain terms after apply | 85 |
| target table | `reader.domain_glossary_entries` |

这个脚本默认只 dry-run。显式 `--apply` 已经执行过一次，把 26 个词写入 Life-study 专属 domain glossary。它没有写入 `reader.dictionary_entries`，也不会覆盖 `metadata.user_corrected=true` 的用户修正。

复验 dry-run：

```bash
.venv-reader-api/bin/python scripts/lifestudy_frontend_candidate_adjudication_apply.py
```

复验已应用状态：

```bash
.venv-reader-api/bin/python scripts/lifestudy_frontend_candidate_adjudication_applied_smoke.py
```

复验前台查词路径：

```bash
.venv-reader-api/bin/python scripts/lifestudy_frontend_candidate_adjudication_live_lookup_smoke.py
```

当前 live lookup 已通过。`redemption`、`righteousness`、`reality`、`anointing`、`priesthood` 会在 Life-study 书里优先显示本轮裁定义，普通书不会使用这些 Life-study 释义。

## Needs-review Frontend Slice V1 进度

2026-06-30 已从 2,205 个 needs-review 学习层二审结果中，抽取第一批前台可查词。

来源文件只允许这两个：

- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_corrected_learning_candidate.csv`
- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_learning_only.csv`

本轮没有处理 5 个 reject、0 个 still-needs-manual-review、旧的 26 个前台词，也没有处理 4,116 个已初审通过学习词。

当前结果：

| 项目 | 数量/状态 |
| --- | ---: |
| eligible learning rows | 2,200 |
| Top queue | 300 |
| queue-level front-end candidates | 20 |
| final front-end-ready terms | 15 |
| frontend_ready | 10 |
| frontend_corrected | 5 |
| learning_only_keep | 279 |
| needs_more_evidence | 6 |
| actual apply | 15 |
| target table | `reader.domain_glossary_entries` |
| ordinary dictionary writes | 0 |

已应用的 15 个词：`authority`, `vision`, `ascension`, `parable`, `misused`, `holy`, `building`, `riches`, `pray`, `peace`, `prayer`, `testify`, `function`, `local`, `preach`。

复验命令：

```bash
.venv-reader-api/bin/python scripts/lifestudy_needs_review_frontend_smoke.py
.venv-reader-api/bin/python scripts/lifestudy_needs_review_frontend_applied_smoke.py
.venv-reader-api/bin/python scripts/lifestudy_needs_review_frontend_live_lookup_smoke.py
.venv-reader-api/bin/python scripts/lifestudy_needs_review_frontend_ui_static_smoke.py
```

这 15 个词已经能在 Life-study/生命读经书内走普通查词入口，优先显示生命读经语境义、卷页和中英文证据。普通书不会使用这些释义。下一步不是回头看 6,321 个候选，也不是把 2,205 全量入库，而是继续处理 Top300 中的 6 个 `needs_more_evidence` 和下一批高价值候选。
