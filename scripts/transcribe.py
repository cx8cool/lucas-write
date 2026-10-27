#!/usr/bin/env python3
"""把视频（单条 / 播放列表 / 频道，任何 yt-dlp 支持的网站）转成 ~/lucas-write/samples/raw/*.md。

三级降级：官方字幕 → 自动字幕 → FunASR 本地转录（中文专用）。幂等，已导入的 video_id 跳过。

用法:
  transcribe.py --check-env
  transcribe.py --url URL [--url URL ...] [--limit 30] [--no-asr] [--list-only]
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
SUB_LANGS = "zh-Hans,zh-Hant,zh-CN,zh,zh-TW"
MIN_DENSITY = 2.0  # 中文口播约 4-5 字/秒，低于 2 视为部分字幕

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E0-\U0001F1FF\U0000FE00-\U0000FE0F\U00002B50-\U00002B55]+")


def check_env(auto_install=True):
    problems = []
    for name, pkg in [("yt-dlp", "yt-dlp"), ("ffmpeg", "ffmpeg")]:
        if shutil.which(name):
            print(f"  ✅ {name}")
            continue
        if auto_install and sys.platform == "darwin" and shutil.which("brew"):
            print(f"  📦 brew install {pkg}")
            subprocess.run(["brew", "install", pkg])
        if shutil.which(name):
            print(f"  ✅ {name} 装好了")
        else:
            print(f"  ❌ {name} 缺失，手动装：brew install {pkg}")
            problems.append(name)
    try:
        import funasr  # noqa
        print("  ✅ funasr")
    except Exception as e:
        if auto_install:
            print("  📦 pip install funasr modelscope（首次较慢）")
            subprocess.run([sys.executable, "-m", "pip", "install", "-U", "funasr", "modelscope"])
        try:
            import funasr  # noqa
            print("  ✅ funasr 装好了")
        except Exception as e2:
            print(f"  ⚠️ funasr 不可用（{e2}）。只能拿字幕，跑的时候加 --no-asr")
            problems.append("funasr")
    return problems


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


def list_videos(urls, limit):
    videos = []
    for url in urls:
        extra = ["--playlist-end", str(limit)] if limit else []
        entries, err = ytdlp_json(["--flat-playlist", "--dump-json"] + extra + [url])
        if not entries:
            print(f"❌ {url} 没拿到任何视频。{err[-300:]}")
            continue
        for e in entries:
            vid = e.get("id")
            if not vid:
                continue
            videos.append({"id": vid, "title": e.get("title") or "", "url": e.get("url") or e.get("webpage_url") or url,
                           "upload_date": e.get("upload_date") or "", "duration": e.get("duration") or 0,
                           "view_count": e.get("view_count") or 0})
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


def get_subs(v):
    existing = list(SUBS.glob(f"{v['id']}*.vtt")) + list(SUBS.glob(f"{v['id']}*.srt"))
    if not existing:
        subprocess.run(["yt-dlp", "--write-sub", "--write-auto-sub", "--sub-lang", SUB_LANGS, "--skip-download",
                        "--no-warnings", "--ignore-errors", "-o", str(SUBS / "%(id)s.%(ext)s"), v["url"]], capture_output=True, text=True)
        existing = list(SUBS.glob(f"{v['id']}*.vtt")) + list(SUBS.glob(f"{v['id']}*.srt"))
    if not existing:
        return None, None
    f = existing[0]
    text = f.read_text(encoding="utf-8", errors="ignore")
    return (clean_vtt(text) if f.suffix == ".vtt" else clean_srt(text)), "subtitle"


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


_model = None


def asr(v):
    global _model
    mp3 = MEDIA / f"{v['id']}.mp3"
    if not mp3.exists():
        subprocess.run(["yt-dlp", "--extract-audio", "--audio-format", "mp3", "--no-warnings", "--ignore-errors",
                        "-o", str(MEDIA / "%(id)s.%(ext)s"), v["url"]], capture_output=True, text=True)
    if not mp3.exists():
        return None
    if _model is None:
        from funasr import AutoModel
        print("  ⏳ 加载 FunASR 模型（首次会下载几百 MB）")
        _model = AutoModel(model="paraformer-zh", vad_model="fsmn-vad", punc_model="ct-punc", disable_update=True)
    res = _model.generate(input=str(mp3), batch_size_s=300)
    text = res[0]["text"] if res else ""
    if not text.strip():
        return None
    sents = re.split(r"(?<=[。！？])", text)
    sents = [s for s in sents if s.strip()]
    return "\n\n".join("".join(sents[i:i + 6]) for i in range(0, len(sents), 6))


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
          f"imported: {datetime.now().strftime('%Y-%m-%d')}\n---\n")
    path = RAW / f"{d}_{slug(v['title'])}.md"
    i = 1
    while path.exists():
        path = RAW / f"{d}_{slug(v['title'])}_{i}.md"; i += 1
    path.write_text(fm + f"\n# {v['title']}\n\n{text}\n", encoding="utf-8")
    return path


def save_progress(p):
    PROGRESS.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-asr", action="store_true")
    ap.add_argument("--list-only", action="store_true")
    ap.add_argument("--check-env", action="store_true")
    a = ap.parse_args()

    if a.check_env:
        print("🔍 环境检查")
        probs = check_env()
        print("✅ 齐全" if not probs else f"⚠️ 缺：{probs}")
        return
    if not a.url:
        ap.error("要 --url")
    for d in [RAW, MEDIA, SUBS]:
        d.mkdir(parents=True, exist_ok=True)
    if not shutil.which("yt-dlp"):
        sys.exit("yt-dlp 没装，先跑 --check-env")

    print("📡 拉清单…")
    videos = list_videos(a.url, a.limit)
    done = imported_ids()
    todo = [v for v in videos if v["id"] not in done]
    print(f"共 {len(videos)} 条，已导入 {len(videos) - len(todo)}，待处理 {len(todo)}")
    with open(WORK / "video_list.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "title", "upload_date", "duration", "view_count", "url"])
        w.writeheader(); w.writerows(videos)
    if a.list_only:
        for v in videos:
            print(f"  {v['upload_date'] or '????????'} | {v['title'][:60]} | {v['url']}")
        return

    prog = {"started": datetime.now().strftime("%Y-%m-%d %H:%M"), "total": len(todo), "done": 0, "subtitle": 0, "asr": 0,
            "failed": [], "status": "running", "finished": None}
    save_progress(prog)
    for i, v in enumerate(todo, 1):
        v = fill_meta(v)
        print(f"[{i}/{len(todo)}] {v['title'][:50]}")
        text, source = get_subs(v)
        if text and v["duration"] and len(text) / v["duration"] < MIN_DENSITY and not a.no_asr:
            print(f"  ⚠️ 字幕太稀（{len(text)} 字 / {v['duration']} 秒），可能是部分字幕，改用 FunASR")
            partial = text
            text = None
        else:
            partial = None
        if text:
            print(f"  ✅ 字幕（{len(text)} 字）")
            prog["subtitle"] += 1
        elif a.no_asr:
            print("  ⚠️ 无字幕，--no-asr 跳过")
            prog["failed"].append({"id": v["id"], "title": v["title"], "url": v["url"], "why": "无字幕"})
            save_progress(prog); continue
        else:
            try:
                text = asr(v); source = "funasr"
            except Exception as e:
                text = None; print(f"  ❌ FunASR 失败：{e}")
            if text:
                print(f"  ✅ FunASR（{len(text)} 字）")
                prog["asr"] += 1
            elif partial:
                text, source = partial, "subtitle-partial"
                print("  ⚠️ FunASR 失败，保留部分字幕")
                prog["subtitle"] += 1
            else:
                prog["failed"].append({"id": v["id"], "title": v["title"], "url": v["url"], "why": "无字幕且转录失败/为空"})
                save_progress(prog); continue
        p = write_md(v, text, source)
        print(f"  💾 {p.name}")
        prog["done"] += 1
        save_progress(prog)
    prog["status"] = "finished"; prog["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_progress(prog)
    print(f"\n✅ 导入 {prog['done']}（字幕 {prog['subtitle']} / FunASR {prog['asr']}），失败 {len(prog['failed'])}")
    for f in prog["failed"]:
        print(f"   ❌ {f['title'][:50]} — {f['why']}  {f['url']}")
    print(f"📁 {RAW}")


if __name__ == "__main__":
    main()
