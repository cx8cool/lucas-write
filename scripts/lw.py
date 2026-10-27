#!/usr/bin/env python3
"""lucas-write 工作区管理。

用法:
  lw.py init                       建 ~/lucas-write，复制 profile 模板，写 state.json
  lw.py status [--json]            看板
  lw.py round N done [--note ..]   标记第 N 轮完成（5 轮完 ready，10 轮完 graduated）
  lw.py round N skip               跳过第 N 轮
  lw.py round set N                把当前轮设为 N
  lw.py snapshot [--label ..]      profile 快照到 profile/history/，profile_version +1
  lw.py history                    列快照
  lw.py rollback NAME              从快照恢复 profile
  lw.py samples                    刷新样本计数
  lw.py wrote TITLE PATH           记录一次写稿，置 pending_review
  lw.py review-done                清 pending_review
  lw.py metric KEY VALUE           写指标（blind_test_score / edit_count 等）
"""
import argparse, json, os, shutil, sys
from datetime import datetime
from pathlib import Path

WS = Path(os.environ.get("LUCAS_WRITE_HOME", Path.home() / "lucas-write"))
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "profile-template"
STATE = WS / "state.json"
PROFILE = WS / "profile"
PROFILE_FILES = ["identity.md", "style-guide.md", "script-templates.md", "knowledge-compact.md",
                 "keyword-mapping.md", "data-sources.md", "title-formulas.md", "rubric.md"]
ROUND_NAMES = {0: "导出现有AI记忆", 1: "身份与受众", 2: "导入过去作品", 3: "结构模板", 4: "观点与案例库",
               5: "选题标准与数据源", 6: "红线", 7: "好坏样本定rubric", 8: "标题公式", 9: "盲测校准", 10: "实战首稿毕业"}


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def load():
    if not STATE.exists():
        sys.exit(f"ERROR: 工作区不存在（{WS}）。先跑: python3 {Path(__file__)} init")
    return json.loads(STATE.read_text(encoding="utf-8"))


def save(s):
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def todo_count(path):
    try:
        return path.read_text(encoding="utf-8").count("TODO")
    except OSError:
        return -1


def cmd_init(a):
    if STATE.exists() and not a.force:
        print(f"已存在 {WS}，不覆盖。要重置加 --force。")
        return
    for d in ["profile/history", "samples/raw", "samples/good", "samples/bad", "imports", "drafts", ".transcribe"]:
        (WS / d).mkdir(parents=True, exist_ok=True)
    for f in PROFILE_FILES:
        dst = PROFILE / f
        if not dst.exists() or a.force:
            shutil.copy(TEMPLATE / f, dst)
    s = {"version": 1, "profile_version": "0.0", "ready": False, "graduated": False, "current_round": 1,
         "rounds": {str(i): {"status": "pending"} for i in range(0, 11)},
         "metrics": {"installed_at": now(), "first_draft_at": None, "blind_test_score": None, "edit_counts": []},
         "samples": {"raw": 0, "good": 0, "bad": 0}, "pending_review": None, "drafts": []}
    save(s)
    print(f"✅ 工作区已建好：{WS}\n   profile 8 个文件来自模板，全部待训练。下一步：第 1 轮。")


def cmd_samples(a):
    s = load()
    for k in ["raw", "good", "bad"]:
        s["samples"][k] = len(list((WS / "samples" / k).glob("*.md")))
    save(s)
    print(json.dumps(s["samples"], ensure_ascii=False))


def cmd_status(a):
    s = load()
    for k in ["raw", "good", "bad"]:
        s["samples"][k] = len(list((WS / "samples" / k).glob("*.md")))
    save(s)
    completeness = {f: todo_count(PROFILE / f) for f in PROFILE_FILES}
    if a.json:
        out = dict(s)
        out["profile_todo"] = completeness
        out["ai_memory_export"] = (WS / "imports" / "ai-memory-export.md").exists()
        out["workspace"] = str(WS)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    print(f"Lucas-write 看板  ｜ 工作区 {WS} ｜ profile v{s['profile_version']}")
    print(f"ready={s['ready']}  graduated={s['graduated']}  当前第 {s['current_round']} 轮：{ROUND_NAMES.get(s['current_round'], '')}")
    print("\n训练轮次：")
    for i in range(0, 11):
        r = s["rounds"][str(i)]
        mark = {"done": "✅", "skipped": "⏭ ", "pending": "·"}[r["status"]]
        note = f"  — {r.get('note')}" if r.get("note") else ""
        print(f"  {mark} 第 {i:>2} 轮 {ROUND_NAMES[i]}{note}")
    print("\nprofile 待填（TODO 数）：")
    for f, n in completeness.items():
        print(f"  {'✅' if n == 0 else '·'} {f}: {n}")
    sm = s["samples"]
    print(f"\n样本：raw {sm['raw']} / good {sm['good']} / bad {sm['bad']}"
          + ("   ⚠️ 样本少于 10，建议补" if sm["raw"] < 10 else ""))
    m = s["metrics"]
    print(f"指标：首稿 {m['first_draft_at'] or '未写'} ｜ 盲测 {m['blind_test_score'] or '-'} ｜ 改稿段数 {m['edit_counts'] or '-'}")
    if s.get("pending_review"):
        print(f"待回收修改：{s['pending_review']['title']}（{s['pending_review']['at']}）")
    print(f"快照：{len(list((PROFILE / 'history').glob('*')))} 个")


def cmd_round(a):
    s = load()
    if a.action == "set":
        s["current_round"] = a.n
    else:
        s["rounds"][str(a.n)] = {"status": "done" if a.action == "done" else "skipped", "at": now(), "note": a.note}
        if a.n >= s["current_round"]:
            s["current_round"] = min(a.n + 1, 10)
        done = {int(k) for k, v in s["rounds"].items() if v["status"] == "done"}
        if {1, 2, 3, 4, 5} <= done:
            s["ready"] = True
        if {1, 2, 3, 4, 5, 6, 7, 8, 9, 10} <= done:
            s["graduated"] = True
            s["profile_version"] = "1.0"
    save(s)
    print(f"✅ 第 {a.n} 轮 {a.action}。ready={s['ready']} graduated={s['graduated']} 下一轮：第 {s['current_round']} 轮")


def cmd_snapshot(a):
    s = load()
    name = datetime.now().strftime("%Y%m%d-%H%M%S") + (f"_{a.label}" if a.label else "")
    dst = PROFILE / "history" / name
    dst.mkdir(parents=True)
    for f in PROFILE_FILES:
        if (PROFILE / f).exists():
            shutil.copy(PROFILE / f, dst / f)
    major, minor = s["profile_version"].split(".")
    if not s["graduated"]:
        s["profile_version"] = f"{major}.{int(minor) + 1}"
    else:
        s["profile_version"] = f"{major}.{int(minor) + 1}"
    save(s)
    print(f"✅ 快照 {name}，profile 现在 v{s['profile_version']}")


def cmd_history(a):
    for p in sorted((PROFILE / "history").glob("*")):
        print(p.name)


def cmd_rollback(a):
    src = PROFILE / "history" / a.name
    if not src.exists():
        sys.exit(f"没有快照 {a.name}")
    cmd_snapshot(argparse.Namespace(label="before-rollback"))
    for f in PROFILE_FILES:
        if (src / f).exists():
            shutil.copy(src / f, PROFILE / f)
    print(f"✅ 已从 {a.name} 恢复 profile（恢复前已自动快照）")


def cmd_wrote(a):
    s = load()
    s["metrics"]["first_draft_at"] = s["metrics"]["first_draft_at"] or now()
    s["pending_review"] = {"title": a.title, "path": a.path, "at": now()}
    s["drafts"].append({"title": a.title, "path": a.path, "at": now()})
    save(s)
    print("✅ 已记录，下次调用会先问改了哪里")


def cmd_review_done(a):
    s = load()
    s["pending_review"] = None
    save(s)
    print("✅ 已清")


def cmd_metric(a):
    s = load()
    v = a.value
    try:
        v = float(v) if "." in v else int(v)
    except ValueError:
        pass
    if a.key == "edit_count":
        s["metrics"]["edit_counts"].append(v)
    else:
        s["metrics"][a.key] = v
    save(s)
    print(json.dumps(s["metrics"], ensure_ascii=False))


p = argparse.ArgumentParser()
sub = p.add_subparsers(dest="cmd", required=True)
x = sub.add_parser("init"); x.add_argument("--force", action="store_true")
x = sub.add_parser("status"); x.add_argument("--json", action="store_true")
x = sub.add_parser("round"); x.add_argument("n_or_set"); x.add_argument("rest", nargs="?"); x.add_argument("--note", default=None)
x = sub.add_parser("snapshot"); x.add_argument("--label", default=None)
sub.add_parser("history")
x = sub.add_parser("rollback"); x.add_argument("name")
sub.add_parser("samples")
x = sub.add_parser("wrote"); x.add_argument("title"); x.add_argument("path")
sub.add_parser("review-done")
x = sub.add_parser("metric"); x.add_argument("key"); x.add_argument("value")
args = p.parse_args()

if args.cmd == "round":
    if args.n_or_set == "set":
        args.action, args.n = "set", int(args.rest)
    else:
        args.n, args.action = int(args.n_or_set), (args.rest or "done")
        if args.action not in ("done", "skip"):
            sys.exit("round 用法: round N done|skip 或 round set N")
    cmd_round(args)
else:
    {"init": cmd_init, "status": cmd_status, "snapshot": cmd_snapshot, "history": cmd_history, "rollback": cmd_rollback,
     "samples": cmd_samples, "wrote": cmd_wrote, "review-done": cmd_review_done, "metric": cmd_metric}[args.cmd](args)
