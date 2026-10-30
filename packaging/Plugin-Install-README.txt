OmniView 0.3 plugin installation

1. Install the core
   Run OmniView-Setup.exe. It extracts to:
   %LOCALAPPDATA%\OmniView\0.3

2. Install all plugins
   Double-click Install-All-Plugins.cmd.
   It closes any running OmniView and installs every .ovp next to it:
   office.ovp  DOCX/XLSX/PPTX/ODT/ODP/RTF
   ebook.ovp   EPUB/MOBI/AZW3
   data.ovp    Access/DBF/HDF5/ONNX/PT/PKL/TFLite/mail stores
   pro.ovp     STL/OBJ/GLB/DXF/SHP/KML/GPX/EXE/ELF/fonts
   raw.ovp     PSD/AI/camera RAW
   hello.ovp   example user plugin (.hello)

3. Install a single plugin
   Help -> Plugin Manager... -> Install .ovp...
   Or drag an .ovp into the window
   Or OmniView.exe --install-plugin path\to\plugin.ovp

4. Verify
   %LOCALAPPDATA%\OmniView\plugins\<id>\plugin.json

5. Make your own .ovp
   python build_ovp.py --template plugins/hello
   python build_ovp.py --source plugins/hello --out plugins/hello.ovp
   Format reference: PLUGIN_FORMAT.md.

Notes:
- .ovp packages execute Python code. Only install packages you trust.
- Parse failures open a red error tab with the full traceback.
- Office can also be installed alone with Install-Office-Plugin.cmd.
