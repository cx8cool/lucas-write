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

## 流程
1. 先 `--check-env`。FunASR 首次要下几百 MB 模型，提前说。装不上 → 加 `--no-asr` 只拿字幕，拿不到字幕的视频列给他让他贴稿。
2. 视频 > 5 个时后台跑：`nohup python3 ... > WS/.transcribe/log.txt 2>&1 &`，告诉他可以关掉去忙，回来说"看转录进度"你就读 progress.json。等进程真正结束再汇报（`while kill -0 PID; do sleep 30; done`），不要以 launcher 退出当完成。
3. 跑完 `python3 SKILL_DIR/scripts/lw.py samples`，汇报：导入 N 篇、字幕 N / FunASR N、失败清单。
4. 从 train 第 2 轮进来的，回到第 2 轮继续提炼。
