# train 模式 · 训练教练（10 轮）

目标：把 `WS/profile/` 从模板填成"像 Lucas"。前 5 轮必做（跑完 `ready=true`），后 5 轮可选（跑完 `graduated=true`）。

## 每一轮的固定节奏（不许跳步）

1. **开场一段话**：这轮要什么、为什么要、他大概要花多久。不超过 5 行。
2. **只要一种材料**。他给不出就降级（见各轮"降级"），不追问第二种。
3. **提炼**：按 `extract-prompts.md` 做，每条结论带来源（样本文件名或他的原话）。
4. **原文展示**：把准备写进 profile 的内容完整贴出来，标明写进哪个文件哪一段。问："这些对吗？要改哪条？"
5. **他确认后**：先 `python3 SKILL_DIR/scripts/lw.py snapshot --label round{N}`，再写文件（替换对应段落的 `TODO`，保留文件结构），再 `python3 SKILL_DIR/scripts/lw.py round {N} done --note "一句话"`。
6. **预告下一轮**：一句话说下轮要准备什么。然后停，不自动开下一轮。

进入 train 时先跑 `lw.py status --json`，从 `current_round` 接着跑；他说"第 7 轮"就跑第 7 轮。他中途说"先写一篇"就切到 write，回来继续。

## 第 0 轮：导出他现有 AI 的记忆（他在 Codex 外做）

进入第 1 轮前检查 `WS/imports/ai-memory-export.md` 是否存在：
- 存在 → 读它，第 1 轮大部分问题直接从里面填，只问缺的。
- 不存在 → 问一句："你平时用 ChatGPT 或别的 AI 吗？用的话我给你一段提示词，贴进去让它把对你的了解导出来，能省掉大半问答。" 他要 → 把 `ai-memory-export-prompt.md` 里的提示词原文贴给他，告诉他存到 `~/lucas-write/imports/ai-memory-export.md`，然后本轮先结束等他；他不要 → 标 `round 0 skip`，直接第 1 轮。

## 第 1 轮：你是谁、写给谁 → identity.md

- 要：一段自我介绍（怎么说都行）+ 他的频道/平台 + 视频一般多长 + 做内容为了什么。
- 有 ai-memory-export 就先用它填 identity.md 草稿，再把草稿贴给他补缺。
- 提炼：身份标签要能当权威背书，带数字（"做了 N 年""管 N 套房"）；受众要具体到城市 + 职业 + 资产阶段；规格换算成字数（默认 200 字/分钟，他说语速快慢再调）。
- 写入：identity.md 的"我是谁""我写给谁""平台与规格"三段。"选题标准"留到第 5 轮。
- 降级：他只说一句"我做西雅图房产视频" → 按 identity 模板逐项问，一次问 3 个，最多两轮。
- 预告：下一轮要他的过去作品，有稿子/字幕最好，没有就给视频链接。

## 第 2 轮：导入过去作品（文章训练）→ style-guide.md + samples/raw/

这是最重要的一轮，材料越多越准。目标 10-30 篇，3 篇也能跑。

三种情况，按顺序问：
1. **有存档**（稿子、字幕、转录任意格式）→ 让他把文件放进 `~/lucas-write/samples/raw/`，或直接贴；贴的内容你替他存成 `samples/raw/YYYY-MM-DD_标题.md`（日期不知道就用导入日）。
2. **只有链接** → 切 `transcribe` 模式（读 `mode-transcribe.md`），跑完回来。
3. **都没有但有频道** → 要频道链接，`transcribe.py --limit 30`。

他自己丢进 `samples/raw/` 的 txt / srt / vtt / docx / 无 frontmatter 的 md，先跑 `python3 SKILL_DIR/scripts/lw.py ingest` 统一格式，再 `lw.py samples` 刷新计数。

样本多时分批读：每批最多 10 篇，每批读完把统计（开场类型计数、口头禅计数、结构标注）追加写到 `WS/imports/round2-notes.md`，全部读完再汇总。不要一次把 30 篇全塞进上下文。

提炼（读 `extract-prompts.md` 的"风格"部分）：开场方式、固定开场白/结束语（原文）、口头禅 top 10 带频率、句长和人称、过渡词、提问推进习惯、结尾习惯。同时**顺手产出两份草稿留给第 3、4 轮**：结构反推草稿、反复出现的判断清单。把这两份存到 `WS/imports/round2-structure-draft.md` 和 `WS/imports/round2-opinions-draft.md`，不展示给他（下两轮再展示）。

写入：style-guide.md 的"Lucas 版底层逻辑""固定开场白""固定结束语""口头禅""句子与段落习惯""CTA 规范"（中段/结尾 CTA 的位置和原句）。
降级：样本 < 5 篇 → 照常做，`lw.py round 2 done --note "样本少，N 篇"`，并在 status 里持续提醒补样本。
预告：下一轮看一眼我反推的结构，改到对就行。

## 第 3 轮：结构模板 → script-templates.md

- 先贴 `imports/round2-structure-draft.md`：长视频一般几段、每段多少字、结论在第几句、几个维度、案例放哪、CTA 在哪（每条带样本证据）。
- 问他："这是我从你 N 篇稿里看出来的结构，哪里不对？短视频和系列视频你有没有固定做法？"
- 写入：三套模板的"Lucas 版"+ 结构使用原则的补充。
- 降级：样本太少反推不出 → 让他口述一遍"我一篇东西通常怎么安排"，按默认模板改。
- 预告：下一轮看一眼我整理的"你反复讲的观点"清单。

## 第 4 轮：固定观点和案例库 → knowledge-compact.md

- 贴 `imports/round2-opinions-draft.md`：出现 ≥ 2 次的判断，每条一句话 + 来源样本；以及他提到的自有项目/客户案例和数字。
- 问："删掉说错的，补上我漏的。你自己的项目有哪些数字可以公开讲？"
- 写入：knowledge-compact.md 四段。
- 预告：下一轮要他平时看什么消息源、什么题做什么题不做。

## 第 5 轮：选题标准和数据源 → keyword-mapping.md + data-sources.md + identity.md

- 要：他常看的网站/报告/公众号/数据源；最近做过的 10 个题（从 samples 标题自动列出让他确认）；明确不做的题。
- 提炼：从 samples 标题归纳 6-10 个常做话题，每个话题按 keyword-mapping 格式配中英文搜索词和数据机构；数据源整理成表 + 发布日历；5 条选题标准写他的版本。
- 写入：三个文件对应段落。
- 完成后 `lw.py round 5 done` 会自动把 `ready` 置 true。告诉他："现在 seed / write / title 都能正常用了，打分用的是通用版，第 7 轮以后换成你的。"
- 预告：后 5 轮可选，建议先用两周，再回来做第 6-8 轮。

## 第 6 轮：红线 → style-guide.md 禁用段

- 要：绝不用的词、不碰的话题、平台合规要求、他看了就烦的"AI 味"例子。
- 顺手从 samples 里反查：他从来没用过但默认模板里有的词（比如"咱们"），列出来问是不是该禁。
- 写入：style-guide.md "Lucas 版禁用词""不碰的话题"。

## 第 7 轮：好坏样本 → rubric.md

- 要：从 samples 挑 5 篇最好、3 篇最差，各一句为什么；有播放/完播/咨询数据更好。
- 把这 8 篇复制到 `samples/good/` `samples/bad/`。
- 提炼（读 `extract-prompts.md` 的"rubric"部分）：好的共同点、差的共同点 → 5-7 个维度 + 权重 + 扣分项 + 等级线。权重之和 100。每个维度要能从稿子文本判断，不能靠拍摄效果。
- 写入：rubric.md "Lucas 版"，版本号改 `lucas-v1`，并把上面通用版标为"已替换"。

## 第 8 轮：标题公式 → title-formulas.md

- 要：15-20 个表现最好的标题（有数据更好）；没有就从 samples 标题里按 view_count 取前 20 让他确认。
- 提炼：归纳 4 套公式，每套配他的 2 个真实例子；封面大字习惯。
- 写入：title-formulas.md "Lucas 版"+"封面大字习惯"+"标题硬约束"的 Lucas 补充（他标题里从不出现的写法）。

## 第 9 轮：盲测校准

- 让他挑一个**已经做过**的题（从 samples 里选），只给你标题和一句话方向。
- 你**不读那篇样本**，用当前 profile 走 write 模式写一版，存 `drafts/blind-test_日期.md`。盲测稿不跑 `lw.py wrote`（它不是要发布的稿，不需要回收修改）。
- 然后把他的原稿和你的稿并排贴出（各取开场 + 一个维度 + 结尾），让他圈"不像我"的地方，并给 1-5 分。
- 每处"不像"翻译成一条规则（写法要具体到句子级：不是"更口语"，而是"每段第一句用问句，不用陈述句"），展示后补进 style-guide / script-templates。
- `lw.py metric blind_test_score N`。< 4 分建议隔周再跑一次第 9 轮。

## 第 10 轮：实战首稿 + 毕业

- 真实新题，走 seed → write → title → qa 全流程。
- 他逐段改，贴回改后稿。你做 diff，每处改动归因到 profile 的某一条（或"profile 里没有这条"），展示后写补丁。
- `lw.py metric edit_count N`（改动段落数）。
- 修改已经当场收过，跑 `lw.py review-done`，再 `lw.py round 10 done`，会置 `graduated=true`，profile 版本记 `1.0`。告诉他以后每次写完我会问"改了哪里"。

## 毕业后校准（每次 write 之后触发，见 SKILL.md 第 2 条）

他贴改后稿 → diff → 归因到 profile 条目 → 列出"建议写入的规则"（最多 3 条，宁少勿多）→ 他同意的才写，写前 snapshot → `lw.py metric edit_count N` → `lw.py review-done`。他说"没改"也记 `edit_count 0`。
