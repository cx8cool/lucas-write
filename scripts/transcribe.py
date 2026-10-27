#!/usr/bin/env python3
"""把视频（单条 / 播放列表 / 频道，任何 yt-dlp 支持的网站）转成 ~/lucas-write/samples/raw/*.md。

三级降级：官方字幕 → 自动字幕 → FunASR 本地转录（中文专用）。字幕太稀（部分字幕）也回退 FunASR。
幂等，已导入的 video_id 跳过。FunASR 装在 ~/lucas-write/.venv 里，脚本自动切换到那个解释器。

用法:
  transcribe.py --check-env                      检查/安装 yt-dlp ffmpeg 和 FunASR 虚拟环境
  transcribe.py --url URL [--url ...] [--limit 30] [--no-asr]
  transcribe.py --url URL --background            后台跑，立刻返回
  transcribe.py --progress                        看后台进度
  transcribe.py --list-only --url URL             只列清单
"""
import argparse, csv, json, os, re, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

WS = Path(os.environ.get("LUCAS_WRITE_HOME", Path.home() / "lucas-write"))
RAW = WS / "samples" / "raw"
WORK = WS / ".transcribe"
MEDIA = WORK / "media"
SUBS = WORK / "subs"
PROGRESS = WORK / "progress.json"
LOG = WORK / "log.txt"
VENV = WS / ".venv"
VENV_PY = VENV / "bin" / "python3"
SUB_LANGS = "zh-Hans,zh-Hant,zh-CN,zh,zh-TW"
MIN_DENSITY = 3.0   # 中文口播约 4-5 汉字/秒，低于 3 视为部分字幕
MIN_COVERAGE = 0.7  # 字幕 cue 覆盖时长不足 70% 视为部分字幕

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E0-\U0001F1FF\U0000FE00-\U0000FE0F\U00002B50-\U00002B55]+")


# ---------- 环境 ----------
def has_funasr():
    try:
        import funasr  # noqa
        return True
    except Exception:
        return False


def pick_python():
    """FunASR/torch 只在 3.10-3.12 上稳定（Mac 自带 3.9 太旧，brew 默认 3.13+ 太新）。"""
    for name in ["python3.12", "python3.11", "python3.10"]:
        p = shutil.which(name)
        if p:
            return p
    if (3, 10) <= sys.version_info[:2] <= (3, 12):
        return sys.executable
    return None


def check_env(auto_install=True):
    problems = []
    for name, pkg in [("yt-dlp", "yt-dlp"), ("ffmpeg", "ffmpeg")]:
        if not shutil.which(name) and auto_install and sys.platform == "darwin" and shutil.which("brew"):
            print(f"  📦 brew install {pkg}")
            subprocess.run(["brew", "install", pkg])
        if shutil.which(name):
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} 缺失。手动装：brew install {pkg}（没有 brew 先装 https://brew.sh）")
            problems.append(name)

    if has_funasr():
        print("  ✅ FunASR（当前 Python）")
        return problems
    if VENV_PY.exists() and subprocess.run([str(VENV_PY), "-c", "import funasr"], capture_output=True).returncode == 0:
        print(f"  ✅ FunASR（{VENV}）")
        return problems
    if not auto_install:
        print("  ❌ FunASR 未装"); problems.append("funasr"); return problems

    py = pick_python()
    if not py:
        print(f"  ❌ 当前 Python {sys.version.split()[0]} 不在 3.10-3.12 之间，FunASR 装不上。先跑：brew install python@3.12，然后重跑 --check-env")
        problems.append("funasr"); return problems
    print(f"  📦 用 {py} 建虚拟环境 {VENV} 并安装 FunASR（下载约 1-2 GB，要几分钟）")
    VENV.parent.mkdir(parents=True, exist_ok=True)
    if not VENV_PY.exists():
        subprocess.run([py, "-m", "venv", str(VENV)])
    r = subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "-U", "pip", "funasr", "modelscope", "torch", "torchaudio"])
    if r.returncode == 0 and subprocess.run([str(VENV_PY), "-c", "import funasr"], capture_output=True).returncode == 0:
        print("  ✅ FunASR 装好了")
    else:
        print("  ⚠️ FunASR 安装失败。先用 --no-asr 只拿字幕；把上面的报错发给 Christine")
        problems.append("funasr")
    return problems


def reexec_in_venv_if_needed(a):
    """主解释器没有 funasr 但 venv 有 → 用 venv 的 python 重新跑自己。"""
    if a.no_asr or a.list_only or a.check_env or a.progress or has_funasr():
        return
    if VENV_PY.exists() and Path(sys.executable).resolve() != VENV_PY.resolve():
        os.execv(str(VENV_PY), [str(VENV_PY)] + sys.argv)


# ---------- yt-dlp ----------
def ytdlp_json(args_list):
    proc = subprocess.run(["yt-dlp", "--no-warnings", "--ignore-errors"] + args_list, capture_output=True, text=True)
    out = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out, proc.stderr


NET_ERR = ("Failed to resolve", "nodename nor servname", "Network is unreachable", "Temporary failure in name resolution",
           "Connection refused", "unable to download webpage")


def network_blocked(err):
    return any(k in (err or "") for k in NET_ERR)


def list_videos(urls, limit):
    videos = []
    for url in urls:
        extra = ["--playlist-end", str(limit)] if limit else []
        entries, err = ytdlp_json(["--flat-playlist", "--dump-json"] + extra + [url])
        if not entries and network_blocked(err):
            sys.exit("❌ 连不上网（DNS/连接失败）。多半是 Codex 沙盒禁网：请批准这条命令联网重跑，"
                     "或在 ~/.codex/config.toml 加 [sandbox_workspace_write] network_access = true 后重启 Codex。")
        if not entries:
            print(f"❌ {url} 没拿到任何视频。可能链接错、要登录或地区限制。{err.strip()[-300:]}")
            continue
        for e in entries:
            vid = e.get("id")
            if not vid:
                continue
            u = e.get("webpage_url") or e.get("url") or ""
            if not u.startswith("http"):
                u = f"https://www.youtube.com/watch?v={vid}" if e.get("ie_key") == "Youtube" else url
            videos.append({"id": vid, "title": e.get("title") or "", "url": u, "upload_date": e.get("upload_date") or "",
                           "duration": e.get("duration") or 0, "view_count": e.get("view_count") or 0})
    seen, uniq = set(), []
    for v in videos:
        if v["id"] not in seen:
            seen.add(v["id"]); uniq.append(v)
    return uniq[:limit] if limit else uniq


def imported_ids():
    ids = set()
    for md in RAW.glob("*.md"):
        m = re.search(r"^video_id:\s*(\S+)", md.read_text(encoding="utf-8", errors="ignore"), re.M)
        if m:
            ids.add(m.group(1))
    return ids


def fill_meta(v):
    if v["upload_date"] and v["duration"]:
        return v
    entries, _ = ytdlp_json(["--dump-json", "--skip-download", v["url"]])
    if entries:
        e = entries[0]
        v.update({"title": e.get("title") or v["title"], "upload_date": e.get("upload_date") or "", "duration": e.get("duration") or 0,
                  "view_count": e.get("view_count") or 0, "url": e.get("webpage_url") or v["url"]})
    return v


# ---------- 字幕 ----------
TS_RE = re.compile(r"(\d+):(\d+):(\d+)[.,](\d+)\s*-->\s*(\d+):(\d+):(\d+)[.,](\d+)")


def last_err(stderr):
    lines = [l for l in (stderr or "").splitlines() if l.strip()]
    return lines[-1][-200:] if lines else ""


def sub_coverage(raw, duration):
    """字幕 cue 覆盖的秒数 / 视频时长。部分字幕（只配了一部分）会远低于 1。"""
    total = 0.0
    for m in TS_RE.finditer(raw):
        h1, m1, s1, _, h2, m2, s2, _ = (int(x) for x in m.groups())
        total += max(0, (h2 * 3600 + m2 * 60 + s2) - (h1 * 3600 + m1 * 60 + s1))
    return total / duration if duration else None


def cjk_density(text, duration):
    return len(re.findall(r"[一-鿿]", text)) / duration if duration else None


def get_subs(v):
    """返回 (text, partial, why)。partial=True 表示字幕只覆盖了一部分。"""
    existing = list(SUBS.glob(f"{v['id']}*.vtt")) + list(SUBS.glob(f"{v['id']}*.srt"))
    err = ""
    if not existing:
        r = subprocess.run(["yt-dlp", "--write-sub", "--write-auto-sub", "--sub-lang", SUB_LANGS, "--skip-download",
                            "--no-warnings", "--ignore-errors", "-o", str(SUBS / "%(id)s.%(ext)s"), v["url"]], capture_output=True, text=True)
        err = r.stderr
        existing = list(SUBS.glob(f"{v['id']}*.vtt")) + list(SUBS.glob(f"{v['id']}*.srt"))
    if not existing:
        return None, False, last_err(err)
    f = existing[0]
    raw = f.read_text(encoding="utf-8", errors="ignore")
    text = clean_vtt(raw) if f.suffix == ".vtt" else clean_srt(raw)
    cov = sub_coverage(raw, v["duration"])
    dens = cjk_density(text, v["duration"])
    partial = (cov is not None and cov < MIN_COVERAGE) or (dens is not None and dens < MIN_DENSITY)
    why = f"覆盖 {cov:.0%}，{dens:.1f} 字/秒" if cov is not None else ""
    return text, partial, why


def clean_vtt(t):
    t = re.sub("<[^>]+>", "", t)
    result, prev = [], ""
    for line in t.splitlines():
        line = line.strip()
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:")) or "-->" in line:
            continue
        if prev and line.startswith(prev):
            prev = line
        elif prev and not prev.startswith(line):
            result.append(prev); prev = line
        else:
            prev = line
    if prev:
        result.append(prev)
    return paragraphs(result)


def clean_srt(t):
    lines = [l.strip() for l in t.splitlines() if l.strip() and not l.strip().isdigit() and "-->" not in l]
    return paragraphs(lines)


def paragraphs(lines):
    dedup = []
    for l in lines:
        if not dedup or l != dedup[-1]:
            dedup.append(l)
    return "\n\n".join(" ".join(dedup[i:i + 8]) for i in range(0, len(dedup), 8))


# ---------- FunASR ----------
_model = None


def asr(v):
    global _model
    mp3 = MEDIA / f"{v['id']}.mp3"
    r = subprocess.CompletedProcess([], 0, "", "")
    if not mp3.exists():
        r = subprocess.run(["yt-dlp", "--extract-audio", "--audio-format", "mp3", "--no-warnings", "--ignore-errors",
                            "-o", str(MEDIA / "%(id)s.%(ext)s"), v["url"]], capture_output=True, text=True)
    if not mp3.exists():
        raise RuntimeError("音频下载失败：" + (last_err(r.stderr) or "yt-dlp 没给出原因"))
    if _model is None:
        from funasr import AutoModel
        print("  ⏳ 加载 FunASR 模型（首次会下载几百 MB）", flush=True)
        _model = AutoModel(model="paraformer-zh", vad_model="fsmn-vad", punc_model="ct-punc", disable_update=True, disable_pbar=True)
    res = _model.generate(input=str(mp3), batch_size_s=300, disable_pbar=True)
    text = res[0]["text"] if res else ""
    if not text.strip():
        return None
    mp3.unlink(missing_ok=True)
    sents = [s for s in re.split(r"(?<=[。！？])", text) if s.strip()]
    return "\n\n".join("".join(sents[i:i + 6]) for i in range(0, len(sents), 6))


# ---------- 输出 ----------
def slug(t):
    t = EMOJI_RE.sub("", t or "").strip()
    t = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", t)
    t = re.sub(r"[\s_&]+", "-", t)
    t = re.sub(r"[^\w\-一-鿿]", "", t)
    return re.sub(r"-+", "-", t).strip("-")[:60] or "untitled"


def write_md(v, text, source):
    d = v["upload_date"]
    d = f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 else datetime.now().strftime("%Y-%m-%d")
    title = (v["title"] or "").replace("\n", " ").replace("'", "''")
    fm = (f"---\ntitle: '{title}'\nsource: video\nvideo_id: {v['id']}\nvideo_url: {v['url']}\nupload_date: {d}\n"
          f"duration_sec: {v['duration']}\nview_count: {v['view_count']}\nlanguage: zh\ntranscript_source: {source}\n"
          f"chars: {len(text)}\nimported: {datetime.now().strftime('%Y-%m-%d')}\n---\n")
    path = RAW / f"{d}_{slug(v['title'])}.md"
    i = 1
    while path.exists():
        path = RAW / f"{d}_{slug(v['title'])}_{i}.md"; i += 1
    path.write_text(fm + f"\n# {v['title']}\n\n{text}\n", encoding="utf-8")
    return path


def save_progress(p):
    PROGRESS.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")


def show_progress():
    if not PROGRESS.exists():
        print("没有转录记录"); return
    p = json.loads(PROGRESS.read_text(encoding="utf-8"))
    print(f"状态：{p['status']}  进度：{p['done']}/{p['total']}（字幕 {p['subtitle']} / FunASR {p['asr']}）  失败 {len(p['failed'])}")
    if p.get("current"):
        print(f"正在处理：{p['current']}")
    for f in p["failed"]:
        print(f"  ❌ {f['title'][:50]} — {f['why']}  {f['url']}")
    for f in p.get("partial", []):
        print(f"  ⚠️ 部分字幕：{f['title'][:50]}  {f['url']}")
    if p["status"] == "running" and LOG.exists():
        print("最近日志：")
        print("".join(LOG.read_text(encoding="utf-8", errors="ignore").splitlines(True)[-5:]))


def run(a):
    print("📡 拉清单…", flush=True)
    videos = list_videos(a.url, a.limit)
    done = imported_ids()
    todo = [v for v in videos if v["id"] not in done]
    print(f"共 {len(videos)} 条，已导入 {len(videos) - len(todo)}，待处理 {len(todo)}", flush=True)
    with open(WORK / "video_list.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "title", "upload_date", "duration", "view_count", "url"])
        w.writeheader(); w.writerows(videos)
    if not videos:
        sys.exit("❌ 一条视频都没拿到，没有可导入的内容。")
    if a.list_only:
        for v in videos:
            print(f"  {v['upload_date'] or '????????'} | {v['title'][:60]} | {v['url']}")
        return

    prog = {"started": datetime.now().strftime("%Y-%m-%d %H:%M"), "total": len(todo), "done": 0, "subtitle": 0, "asr": 0,
            "failed": [], "partial": [], "status": "running", "current": None, "finished": None}
    save_progress(prog)
    use_asr = not a.no_asr and has_funasr()
    if not a.no_asr and not use_asr:
        print("⚠️ FunASR 不可用，本次只拿字幕（跑 --check-env 可以装）", flush=True)
    for i, v in enumerate(todo, 1):
        v = fill_meta(v)
        prog["current"] = v["title"]; save_progress(prog)
        print(f"[{i}/{len(todo)}] {v['title'][:50]}", flush=True)
        sub_text, is_partial, why = get_subs(v)
        text, source, partial = sub_text, "subtitle", None
        if text and is_partial:
            print(f"  ⚠️ 字幕不完整（{why}），" + ("改用 FunASR" if use_asr else "未开 FunASR，先保留并标记 partial"), flush=True)
            partial, text = sub_text, None
        if text:
            print(f"  ✅ 字幕（{len(text)} 字）", flush=True); prog["subtitle"] += 1
        elif use_asr:
            asr_err = ""
            try:
                text = asr(v); source = "funasr"
            except Exception as e:
                text = None; asr_err = str(e); print(f"  ❌ FunASR 失败：{e}", flush=True)
            if text:
                print(f"  ✅ FunASR（{len(text)} 字）", flush=True); prog["asr"] += 1
            elif partial:
                text, source = partial, "subtitle-partial"
                print("  ⚠️ 保留部分字幕，标记 subtitle-partial", flush=True); prog["subtitle"] += 1
        elif partial:
            text, source = partial, "subtitle-partial"
            prog["subtitle"] += 1
            prog["partial"].append({"id": v["id"], "title": v["title"], "url": v["url"]})
        if not text:
            reason = "无字幕" + ("" if use_asr else "（未开 FunASR）") + (f"：{why}" if why else "") + (f"；{asr_err}" if use_asr and asr_err else "")
            prog["failed"].append({"id": v["id"], "title": v["title"], "url": v["url"], "why": reason})
            save_progress(prog); continue
        p = write_md(v, text, source)
        print(f"  💾 {p.name}", flush=True)
        prog["done"] += 1; save_progress(prog)
    prog["status"] = "finished"; prog["current"] = None; prog["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_progress(prog)
    print(f"\n✅ 导入 {prog['done']}（字幕 {prog['subtitle']} / FunASR {prog['asr']}），失败 {len(prog['failed'])}")
    for f in prog["failed"]:
        print(f"   ❌ {f['title'][:50]} — {f['why']}  {f['url']}")
    if prog["partial"]:
        print(f"⚠️ {len(prog['partial'])} 条只有部分字幕（已标 subtitle-partial），装好 FunASR 后删掉对应 md 重跑可补全：")
        for f in prog["partial"]:
            print(f"   {f['title'][:50]}  {f['url']}")
    print(f"📁 {RAW}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-asr", action="store_true")
    ap.add_argument("--list-only", action="store_true")
    ap.add_argument("--check-env", action="store_true")
    ap.add_argument("--background", action="store_true")
    ap.add_argument("--progress", action="store_true")
    a = ap.parse_args()

    if a.check_env:
        print("🔍 环境检查")
        probs = check_env()
        print("✅ 齐全，可以转录" if not probs else f"⚠️ 缺：{probs}")
        return
    if a.progress:
        show_progress(); return
    if not a.url:
        ap.error("要 --url")
    for d in [RAW, MEDIA, SUBS]:
        d.mkdir(parents=True, exist_ok=True)
    if not shutil.which("yt-dlp"):
        sys.exit("yt-dlp 没装，先跑 --check-env")
    if a.background:
        argv = [x for x in sys.argv[1:] if x != "--background"]
        with open(LOG, "w") as log:
            proc = subprocess.Popen([sys.executable, __file__] + argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        print(f"🚀 后台转录已启动（PID {proc.pid}）。看进度：python3 {__file__} --progress")
        return
    reexec_in_venv_if_needed(a)
    run(a)


if __name__ == "__main__":
    main()
