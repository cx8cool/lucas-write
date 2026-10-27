#!/bin/bash
# Lucas 新 Mac 一键装机：Homebrew → 常用软件 → Codex → Lucas-write 写稿工具 → FunASR
# 用法（终端里粘贴）：
#   curl -fsSL https://raw.githubusercontent.com/cx8cool/lucas-write/master/setup-mac.sh | bash
# 或者下载后：bash setup-mac.sh
# 可重复运行，装过的会跳过。设 DRY_RUN=1 只打印不执行。

set -u
DRY_RUN="${DRY_RUN:-0}"
REPO="https://github.com/cx8cool/lucas-write.git"
SKILL_DIR="$HOME/.agents/skills/lucas-write"
LOG="$HOME/Desktop/lucas-setup.log"

# ====== 要装的东西（不想装的删掉那一行即可）======
FORMULAE=(git python@3.12 yt-dlp ffmpeg codex)
CASKS=(warp chatgpt claude obsidian)
INSTALL_OH_MY_ZSH=1
INSTALL_FUNASR=1          # 转录视频用，下载 1-2 GB，放最后
# ================================================

say()  { printf "\n\033[1;34m==> %s\033[0m\n" "$*"; }
ok()   { printf "   \033[32m✓ %s\033[0m\n" "$*"; }
warn() { printf "   \033[33m! %s\033[0m\n" "$*"; }
run()  { if [ "$DRY_RUN" = "1" ]; then echo "   [dry] $*"; else "$@"; fi; }

exec > >(tee -a "$LOG") 2>&1
echo "Lucas 装机脚本 $(date '+%Y-%m-%d %H:%M')  日志：$LOG"

if [ "$(uname)" != "Darwin" ]; then echo "只支持 macOS"; exit 1; fi
ARCH=$(uname -m)
BREW_BIN=/opt/homebrew/bin/brew; [ "$ARCH" = "x86_64" ] && BREW_BIN=/usr/local/bin/brew

# ---------- 1. Xcode Command Line Tools（git 在里面）----------
say "1/7 Xcode 命令行工具"
if xcode-select -p >/dev/null 2>&1; then ok "已装"
else
  warn "会弹一个窗口，点「安装」，装完再回来按回车"
  run xcode-select --install
  if [ "$DRY_RUN" != "1" ]; then
    until xcode-select -p >/dev/null 2>&1; do sleep 10; done
  fi
  ok "装好了"
fi

# ---------- 2. Homebrew ----------
say "2/7 Homebrew（Mac 的软件安装器）"
if [ -x "$BREW_BIN" ]; then ok "已装"
else
  if ! groups "$USER" | grep -qw admin; then
    echo "   你的账户不是管理员，装不了。去 系统设置 → 用户与群组，把 $USER 改成「管理员」，注销再登录后重跑。"; exit 1
  fi
  warn "现在输 Mac 开机密码（输入时屏幕不显示，输完回车）"
  if [ "$DRY_RUN" != "1" ]; then
    sudo -v < /dev/tty || { echo "   密码不对或没权限，重跑一遍再试。"; exit 1; }
    ( while true; do sudo -n true; sleep 50; kill -0 "$$" 2>/dev/null || exit; done ) 2>/dev/null &
    /bin/bash -c "NONINTERACTIVE=1 $(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" < /dev/tty
  else echo "   [dry] 安装 Homebrew"; fi
fi
if [ -x "$BREW_BIN" ]; then
  eval "$("$BREW_BIN" shellenv)"
  grep -q 'brew shellenv' "$HOME/.zprofile" 2>/dev/null || echo "eval \"\$($BREW_BIN shellenv)\"" >> "$HOME/.zprofile"
  ok "brew 可用：$(brew --version | head -1)"
elif [ "$DRY_RUN" != "1" ]; then
  echo "Homebrew 没装上，把 $LOG 发给 Christine"; exit 1
fi

# ---------- 3. 命令行工具 ----------
say "3/7 命令行工具：${FORMULAE[*]}"
for f in "${FORMULAE[@]}"; do
  if brew list --formula "$f" >/dev/null 2>&1; then ok "$f 已装"
  else run brew install "$f" && ok "$f"; fi
done

# ---------- 4. 桌面软件 ----------
say "4/7 桌面软件：${CASKS[*]}"
for c in "${CASKS[@]}"; do
  if brew list --cask "$c" >/dev/null 2>&1 || ls /Applications 2>/dev/null | grep -qi "^${c}"; then ok "$c 已装"
  else run brew install --cask "$c" && ok "$c"; fi
done

# ---------- 5. oh-my-zsh ----------
say "5/7 终端美化 oh-my-zsh"
if [ "$INSTALL_OH_MY_ZSH" = "1" ]; then
  if [ -d "$HOME/.oh-my-zsh" ]; then ok "已装"
  else run sh -c "RUNZSH=no CHSH=no $(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" && ok "装好了"; fi
else warn "跳过"; fi

# ---------- 6. Codex 配置 + Lucas-write ----------
say "6/7 Codex 配置 + Lucas-write 写稿工具"
mkdir -p "$HOME/.codex" "$HOME/.agents/skills"
CFG="$HOME/.codex/config.toml"
touch "$CFG"
grep -q '^web_search' "$CFG" || { [ "$DRY_RUN" = "1" ] || printf '\nweb_search = "live"\n' >> "$CFG"; ok "config.toml: web_search = live"; }
grep -q 'sandbox_workspace_write' "$CFG" || { [ "$DRY_RUN" = "1" ] || printf '\n[sandbox_workspace_write]\nnetwork_access = true\n' >> "$CFG"; ok "config.toml: 沙盒联网"; }

if [ -d "$SKILL_DIR/.git" ]; then
  run git -C "$SKILL_DIR" pull -q && ok "lucas-write 已更新"
else
  if run git clone -q "$REPO" "$SKILL_DIR"; then ok "lucas-write 装到 $SKILL_DIR"
  else warn "下载 lucas-write 失败（仓库可能是私有的）。把你的 GitHub 用户名发给 Christine，加权限后重跑这个脚本。"; fi
fi

# ---------- 7. FunASR（转录视频用）----------
say "7/7 语音转录 FunASR（下载 1-2 GB，几分钟）"
if [ "$INSTALL_FUNASR" = "1" ] && [ -f "$SKILL_DIR/scripts/transcribe.py" ]; then
  run python3 "$SKILL_DIR/scripts/transcribe.py" --check-env
else warn "跳过（没装 lucas-write 或已关闭）"; fi

# ---------- 收尾 ----------
say "装完了。接下来："
cat <<'TXT'
   1. 打开「Warp」（在 应用程序 里，以后终端都用它）
   2. 输入  codex login   回车，按提示用 ChatGPT 账号登录（只需一次）
   3. 输入  cd ~   回车，再输入  codex   回车
   4. 在 Codex 里输入  $lucas-write   回车，开始第 1 轮
   ChatGPT / Claude / Obsidian 都在 应用程序 里，打开登录一下就行。
TXT
echo "   日志在 ${LOG} ，出问题把它发给 Christine。"
