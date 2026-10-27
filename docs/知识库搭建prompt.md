# 给 Lucas：在 Codex 里搭自己的 Obsidian 知识库

前提：`$lucas-write` 第 2 轮已经跑过，`~/lucas-write/samples/raw/` 里有他的视频转录。把下面整段贴进 Codex（不用加 $lucas-write）。

---

帮我在 `~/LucasVault/` 建一个 Obsidian 知识库，把我过去的视频变成可以反复查、可以让 AI 学的资料。按下面的规格做，每一步做完告诉我做了什么，再做下一步。

## 目录结构
```
~/LucasVault/
  00_AI配置/        给 AI 看的说明：我的写作风格指南、知识库使用说明、写稿流程说明
  01_我的内容/
    视频/           每个视频一篇结构化笔记
    转录/           原始转录稿（从 ~/lucas-write/samples/raw 复制过来，不改）
    文章/           以后我写的文章
  02_对标频道/      以后放别人频道的分析，先建空目录
  03_知识卡片/      从视频里提炼的概念卡，一个概念一张
  04_稿件/          以后 lucas-write 写的稿子按期归档
  06_数据/          选题复盘和数据
  Templates/        三个模板：视频笔记、知识卡片、稿件
  README.md         知识库说明 + 更新日志
  AGENTS.md         给 Codex 的规则（目录规范、frontmatter 规范、新视频入库流程）
```

## 第 1 步：转录稿入库
把 `~/lucas-write/samples/raw/*.md` 复制到 `01_我的内容/转录/`，文件名保持 `日期_标题.md`，frontmatter 原样保留。

## 第 2 步：每个视频一篇笔记（01_我的内容/视频/）
读每篇转录，按这个模板写，文件名和转录稿相同：
```
---
title: "标题"
date: 发布日期
category: 一个分类词（比如 市场判断 / 投资策略 / 政策解读 / 自有项目 / 其他）
type: video
tags: [Lucas, 分类]
source: "[[转录/同名文件]]"
---
# 标题

## 核心论点
一段话，这期视频的核心判断是什么，结论前置。

## 关键数据
- 视频里出现的每一个具体数字，带上下文和来源（视频里说的是谁的数据）

## 观点清单
- 每条一句话，"我认为……"，只记视频里明确说过的判断

## 我的案例
- 视频里提到的我自己的项目、客户、经历，带数字

## 可以拆出的知识卡片
- 概念名 1
- 概念名 2
```
不要编视频里没有的东西。数字必须原文有。一次处理 10 篇，做完汇报再继续。

## 第 3 步：知识卡片（03_知识卡片/）
把第 2 步每篇笔记"可以拆出的知识卡片"里的概念合并去重，一个概念一张卡，文件名就是概念名：
```
---
title: 概念名
created: 今天
sources: [视频笔记文件名, …]
---
# 概念名

## 一句话定义

## 详细解释

## 对我观众的启示
（我的观众是谁见 ~/lucas-write/profile/identity.md）

## 来源
- [[视频笔记文件名]]
```
同一个概念在多期视频里讲过的，合并到一张卡，来源列全。两个相反概念的对比（"A vs B"）单独成卡。

## 第 4 步：00_AI配置
- `01-写作风格指南.md`：直接链接到 `~/lucas-write/profile/style-guide.md`，不要复制，写一句"以 lucas-write 的 profile 为准"。
- `02-知识库使用说明.md`：这个库怎么用，每个目录放什么。
- `03-新视频入库流程.md`：以后我发了新视频，走这几步：在 Codex 里 `$lucas-write 转录 <链接>` → 转录稿复制到 01/转录 → 按模板生成视频笔记 → 更新或新建知识卡片 → 把新观点同步进 `~/lucas-write/profile/knowledge-compact.md`。

## 第 5 步：AGENTS.md 和 README.md
AGENTS.md 写清楚：目录规范、frontmatter 字段、笔记和卡片模板位置、"不编造、数字必须来自原文"、新视频入库流程。
README.md 写知识库说明，并开一个"更新日志"段，这次写 v1.0，说明做了什么、多少篇笔记多少张卡。以后每次改结构都要在这里加一条，写清楚为什么改。

## 第 6 步：Obsidian 显示设置
在 `.obsidian/app.json` 里把 `AGENTS.md`、`README.md`、`Templates/`、`00_AI配置/` 加进 `userIgnoreFilters`，给人看的时候不显示这些。

## 第 7 步：回写 lucas-write
把 03_知识卡片 里的每张卡压成一行"【概念】定义 → 对观众的启示 ｜来源"，追加到 `~/lucas-write/profile/knowledge-compact.md` 的"一贯判断"段。追加前先跑 `python3 ~/.agents/skills/lucas-write/scripts/lw.py snapshot --label vault-sync`。

做完告诉我：笔记几篇、卡片几张、哪些视频转录质量差需要我补稿。
