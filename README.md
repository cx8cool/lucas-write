# lucas-write

Lucas 专属口播稿 skill（Codex）。流程：seed → write → title → qa，外加 train / transcribe / status。

- 引擎在这个仓库，装到 `~/.agents/skills/lucas-write/`
- Lucas 的数据在 `~/lucas-write/`，不进仓库
- 安装、准备清单、常见问题见 `docs/给Lucas的说明.md`
- 设计思路见 `docs/设计说明.md`

更新：`git -C ~/.agents/skills/lucas-write pull`

## 给新电脑做装机包

`bash make-bundle.sh` 会在桌面生成 `新Mac装机包/` 和同名 zip，AirDrop 过去双击 `装机.command` 或按 `看我.txt` 操作即可，不用 GitHub 下载。
