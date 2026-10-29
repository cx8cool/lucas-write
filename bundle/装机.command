#!/bin/bash
# 双击我开始装机（会在终端里跑 setup-mac.sh，用旁边自带的 lucas-write）
cd "$(dirname "$0")" || exit 1
LOCAL_REPO="$PWD/lucas-write" bash ./setup-mac.sh
echo
echo "可以关掉这个窗口了。"
