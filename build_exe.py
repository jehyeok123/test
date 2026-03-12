#!/usr/bin/env python
"""
Build diagram.py into a standalone executable.

Prerequisites (install once):
    pip install pyinstaller python-pptx Pillow

Usage:
    python build_exe.py

Output:
    dist/DiagramEditor.exe   (Windows)
    dist/DiagramEditor       (Linux/macOS)

The resulting executable can be distributed and run without
Python installed. Double-click to open with a new empty diagram,
or drag an input.json onto the exe to open it.
"""

import subprocess
import sys
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN_SCRIPT = HERE / "diagram.py"
DIST_DIR = HERE / "dist"
BUILD_DIR = HERE / "build"

def main():
    # Verify dependencies
    for mod in ("PIL", "pptx", "tkinter"):
        try:
            __import__(mod)
        except ImportError:
            print(f"ERROR: '{mod}' not found. Install it first:")
            if mod == "tkinter":
                print("  - Windows: comes with Python installer (check 'tcl/tk' during install)")
                print("  - Ubuntu/Debian: sudo apt install python3-tk")
                print("  - macOS: brew install python-tk")
            else:
                pkg = {"PIL": "Pillow", "pptx": "python-pptx"}[mod]
                print(f"  pip install {pkg}")
            sys.exit(1)

    try:
        import PyInstaller
    except ImportError:
        print("ERROR: PyInstaller not found. Install it:")
        print("  pip install pyinstaller")
        sys.exit(1)

    print("=" * 60)
    print("  Building DiagramEditor executable...")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                     # Single exe file
        "--windowed",                    # No console window (GUI app)
        "--name", "DiagramEditor",       # Output name
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--noconfirm",
        "--clean",
        # Hidden imports for all dependencies
        "--hidden-import", "PIL",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageDraw",
        "--hidden-import", "PIL.ImageFont",
        "--hidden-import", "PIL.ImageTk",
        "--hidden-import", "pptx",
        "--hidden-import", "pptx.util",
        "--hidden-import", "pptx.enum.shapes",
        "--hidden-import", "pptx.enum.text",
        "--hidden-import", "pptx.dml.color",
        "--hidden-import", "pptx.oxml.ns",
        "--hidden-import", "lxml",
        "--hidden-import", "lxml.etree",
        "--hidden-import", "lxml._elementpath",
        str(MAIN_SCRIPT),
    ]

    print(f"\nRunning: {' '.join(cmd[-5:])}\n")
    result = subprocess.run(cmd, cwd=str(HERE))
    if result.returncode != 0:
        print("\nBuild FAILED!")
        sys.exit(1)

    # Find the output
    exe_name = "DiagramEditor.exe" if sys.platform == "win32" else "DiagramEditor"
    exe_path = DIST_DIR / exe_name
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 60)
        print(f"  BUILD SUCCESS!")
        print(f"  Output: {exe_path}")
        print(f"  Size:   {size_mb:.1f} MB")
        print("=" * 60)
        print(f"\nYou can now distribute '{exe_name}'.")
        print("Double-click to start with an empty diagram,")
        print("or run from command line: DiagramEditor [input.json] [output.png]")
    else:
        print(f"\nWARNING: Expected output not found at {exe_path}")
        print("Check the dist/ directory for the built file.")


if __name__ == "__main__":
    main()
