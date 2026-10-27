# transcribe 模式 · 视频转录导入

把他的视频变成 `WS/samples/raw/*.md`。纯中文口播。三级降级：官方字幕 → 自动字幕 → FunASR 本地转录。

## 命令
```
python3 SKILL_DIR/scripts/transcribe.py --check-env            # 第一次先跑，缺什么自动装
python3 SKILL_DIR/scripts/transcribe.py --url <视频/播放列表/频道链接> [--url ...] [--limit 30]
python3 SKILL_DIR/scripts/transcribe.py --list-only --url <频道链接>   # 只看清单不下载
```
- 任何 yt-dlp 支持的网站都行，单视频和频道同一条命令
- 幂等：已导入的 video_id 自动跳过，可以反复加
- 进度在 `WS/.transcribe/progress.json`，中间文件在 `WS/.transcribe/`

```
python3 SKILL_DIR/scripts/transcribe.py --url ... --background   # 后台跑，立刻返回
python3 SKILL_DIR/scripts/transcribe.py --progress               # 看进度
```

## 流程
0. 脚本报"连不上网"→ 是沙盒禁网。请求提升权限重跑这条命令；并告诉他在 `~/.codex/config.toml` 加 `[sandbox_workspace_write]` `network_access = true` 后重启，以后就不用每次批。
1. 先 `--check-env`。FunASR 装在 `WS/.venv`，首次装要下 1-2 GB，再加几百 MB 模型，提前说要几分钟。装不上 → 加 `--no-asr` 只拿字幕，拿不到字幕的视频会列在失败清单里，让他贴稿。
2. 视频 ≤ 3 个直接前台跑。> 3 个用 `--background`，告诉他可以关掉 Codex 去忙，回来说"看转录进度"你就跑 `--progress`。进度 `status=finished` 才算完。
3. 跑完 `python3 SKILL_DIR/scripts/lw.py samples`，汇报：导入 N 篇、字幕 N / FunASR N、失败清单（带链接）。
4. 从 train 第 2 轮进来的，回到第 2 轮继续提炼。
