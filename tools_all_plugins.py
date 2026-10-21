import sys
from PySide6.QtWidgets import QApplication
sys.path.insert(0,r"F:\DeepSeek默认\OmniView3")
from omniview import i18n
from omniview.ui.theme import apply_theme
from omniview.ui.plugin_manager_dialog import PluginManagerDialog
app=QApplication([]); apply_theme(app); i18n.set_language("zh")
d=PluginManagerDialog(); d.show()
for _ in range(10): app.processEvents()
d.grab().save(r"F:\DeepSeek默认\OmniView3\test-evidence\15_all_plugins.png"); d.close(); app.quit()
print("ok")
