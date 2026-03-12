@echo off
REM ============================================
REM  DiagramEditor - Build Executable (Windows)
REM ============================================
REM
REM Prerequisites:
REM   1. Python 3.10+ installed (with tkinter)
REM   2. Run once: pip install pyinstaller python-pptx Pillow
REM
REM Usage: double-click this file or run from command prompt
REM

echo ============================================
echo  Installing dependencies...
echo ============================================
pip install pyinstaller python-pptx Pillow

echo.
echo ============================================
echo  Building DiagramEditor.exe ...
echo ============================================

pyinstaller --onefile --windowed --name DiagramEditor ^
  --hidden-import PIL --hidden-import PIL._tkinter_finder ^
  --hidden-import PIL.Image --hidden-import PIL.ImageDraw ^
  --hidden-import PIL.ImageFont --hidden-import PIL.ImageTk ^
  --hidden-import pptx --hidden-import pptx.util ^
  --hidden-import pptx.enum.shapes --hidden-import pptx.enum.text ^
  --hidden-import pptx.dml.color --hidden-import pptx.oxml.ns ^
  --hidden-import lxml --hidden-import lxml.etree ^
  --hidden-import lxml._elementpath ^
  --noconfirm --clean ^
  diagram.py

if exist dist\DiagramEditor.exe (
    echo.
    echo ============================================
    echo  BUILD SUCCESS!
    echo  Output: dist\DiagramEditor.exe
    echo ============================================
    echo.
    echo You can now copy DiagramEditor.exe anywhere and run it.
) else (
    echo.
    echo BUILD FAILED! Check the error messages above.
)

pause
