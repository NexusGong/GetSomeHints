#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清除 MediaCrawler 保存的登录态（浏览器数据目录），便于重新扫码/验证。

使用方式（在项目根目录或 backend 目录执行）：
  python backend/scripts/clear_mc_login.py
  python backend/scripts/clear_mc_login.py --platform dy
  python backend/scripts/clear_mc_login.py --platform xhs
  python backend/scripts/clear_mc_login.py --all
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="清除 MC 登录态（browser_data）")
    parser.add_argument(
        "--platform",
        choices=["dy", "xhs"],
        help="只清除指定平台（dy=抖音, xhs=小红书）",
    )
    parser.add_argument("--all", action="store_true", help="清除所有平台的登录数据")
    args = parser.parse_args()

    if not args.platform and not args.all:
        parser.error("请指定 --platform dy|xhs 或 --all")

    backend = Path(__file__).resolve().parent.parent
    browser_data = backend / "mediacrawler_bundle" / "browser_data"
    if not browser_data.is_dir():
        print(f"目录不存在（无需清除）: {browser_data}")
        return

    to_remove: list[Path] = []
    if args.all:
        for d in browser_data.iterdir():
            if d.is_dir():
                to_remove.append(d)
    else:
        name = "dy_user_data_dir" if args.platform == "dy" else "xhs_user_data_dir"
        d = browser_data / name
        if d.is_dir():
            to_remove.append(d)

    if not to_remove:
        print("未找到对应平台的登录数据目录，无需清除")
        return

    for d in to_remove:
        try:
            shutil.rmtree(d)
            print(f"已删除: {d}")
        except Exception as e:
            print(f"删除失败 {d}: {e}", file=sys.stderr)
            sys.exit(1)
    print("清除完成。下次运行爬虫将重新打开登录/验证流程。")


if __name__ == "__main__":
    main()
