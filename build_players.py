#!/usr/bin/env python3
"""GitHub/Streamlit 專案的一鍵球員資料更新入口。"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).with_name("espn_bulk_collect.py")
    raise SystemExit(subprocess.call([sys.executable, str(script), *sys.argv[1:]]))
