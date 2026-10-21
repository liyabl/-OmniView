$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "== OmniView 0.3 core (onedir) ==" -ForegroundColor Cyan
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }

$excludes = @(
  "mammoth", "cobble", "docx", "openpyxl", "et_xmlfile", "pptx", "odf", "striprtf", "lxml",
  "h5py", "onnx", "tflite", "flatbuffers", "dbf", "access_parser", "rawpy", "psd_tools",
  "ezdxf", "shapefile", "fontTools", "pefile", "elftools", "macholib", "rpmfile",
  "extract_msg", "mobi", "torch", "pandas", "cv2", "matplotlib", "scipy", "sklearn", "tensorflow",
  "numba", "llvmlite", "IPython", "notebook", "jupyter", "tkinter",
  "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
  "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DLogic",
  "PySide6.Qt3DExtras", "PySide6.QtCharts", "PySide6.QtQuick", "PySide6.QtQml",
  "PySide6.QtQuick3D", "PySide6.QtDataVisualization", "PySide6.QtGraphs"
)
$args = @(
  "--noconfirm", "--clean", "--onedir", "--windowed",
  "--name", "OmniView",
  "--icon", "assets\app.ico",
  "--add-data", "assets;assets",
  "--add-data", "omniview\locales;omniview\locales",
  "--add-data", "docs;docs",
  "--paths", ".",
  "--hidden-import", "PySide6.QtPdf",
  "--hidden-import", "PySide6.QtPdfWidgets",
  "--hidden-import", "PySide6.QtMultimedia",
  "--hidden-import", "PySide6.QtMultimediaWidgets",
  "--hidden-import", "configparser",
  "--hidden-import", "uuid",
  "--hidden-import", "timeit",
  "--hidden-import", "colorsys",
  "--hidden-import", "decimal",
  "--hidden-import", "fractions",
  "--hidden-import", "statistics",
  "--hidden-import", "cProfile",
  "--hidden-import", "pstats",
  "--hidden-import", "doctest",
  "--hidden-import", "unittest",
  "--hidden-import", "tarfile",
  "--hidden-import", "gzip",
  "--hidden-import", "bz2",
  "--hidden-import", "lzma",
  "--hidden-import", "plistlib",
  "--hidden-import", "shelve",
  "--hidden-import", "dbm",
  "--hidden-import", "sqlite3",
  "--hidden-import", "csv"
)
foreach ($e in $excludes) { $args += @("--exclude-module", $e) }
$args += "app.py"

python -m PyInstaller @args
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
$size = [math]::Round(((Get-ChildItem "dist\OmniView" -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), 1)
Write-Host "core directory: dist\OmniView ($size MB)" -ForegroundColor Green


