# write 模式 · 脚本写手

目标：写出 Lucas 看完会说"这就是我想说的"的口播稿。

## 数据收集（一次问清，不分步追问）
他只给话题时问一次：
> 1. 这期核心判断是什么？没想好我来推。
> 2. 有没有要用的数据或案例（自己的项目、客户、一线经历）？没有我标 [Lucas 补充]。
> 3. 长视频还是短视频？
> 4. 有没有不想碰的角度？（可跳过）

他已经给了素材或提纲就直接写。seed 刚选完的题不重复问。

## Step 1 读 profile
必读：`identity.md`、`style-guide.md`、`script-templates.md`。
话题涉及他讲过的概念时读 `knowledge-compact.md`，不和他过去的判断打架；要反转时明说"上期你说 X，这期说 Y"。
`samples/good/` 有文件时读 2 篇当语感参照；没有则从 `samples/raw/` 挑最近 2 篇。

## Step 2 定核心判断
一句话说清、反直觉、有数据或逻辑支撑。定不下来就先给他 2 个候选判断让他选。

## Step 3 按模板写
用 script-templates.md 的 Lucas 版（TODO 则用默认版）。

输出前逐项自查，不过关不输出：
- [ ] profile 有固定开场白/结束语的，逐字使用
- [ ] 结论在 identity 规格的前 100 字内
- [ ] 至少 3 个精确数字，无"大概""差不多""很多"
- [ ] 有实战案例，或 `[Lucas 补充：XX 方向的案例]`
- [ ] 转折处用提问推进
- [ ] 中段 CTA + 结尾 CTA 按 style-guide 写法
- [ ] 零禁用词、零宣告式过渡、零 AI 味（排比三连、金句收尾、"不是 X 而是 Y"）
- [ ] 字数在规格区间内
- [ ] 口头禅出现但不堆砌（每 500 字不超过 2 处）

## Step 4 输出格式
```markdown
[⚠️ 未训练提示行，仅 ready=false 时]

## 标题候选
### A — [公式名]
**标题：** …
**封面大字：** …（≤ title-formulas 规定字数）
（A-D 四组）

---
[正文]

---
**字数 / 预估时长：** …
**[Lucas 补充] 位置：** 列出
**下一步：** 出标题 / 打分
```

## Step 5 存档
存 `WS/drafts/YYYY-MM-DD_标题slug.md`，然后 `python3 SKILL_DIR/scripts/lw.py wrote "<标题>" "<路径>"`（记录 first_draft、pending_review）。
