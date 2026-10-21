import os
from PySide6.QtWidgets import QApplication
app=QApplication([])
from omniview.ui.main_window import MainWindow
w=MainWindow()
files=["示例电子书.epub","科学数据.h5","演示模型.onnx","权重.pt","对象.pkl","城市点位.dbf","邮件归档.mbox","示例图层.psd","球体.glb","示例图纸.dxf","城市点位.shp","示例地图.kml","示例模型.step","示例邮件.eml"]
for f in files:
    p=os.path.join(r"samples",f)
    try:
        v=w.create_viewer(p); print(f, type(v).__name__, getattr(v,"info",{}).get("状态",""))
    except Exception as e: print(f,"ERR",repr(e))
