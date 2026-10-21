import os
from omniview import plugin_manager
root=r"F:\DeepSeek默认\OmniView3\plugins"
for name in ("office","ebook","data","pro","raw","hello"):
    p=os.path.join(root,name+".ovp")
    if not os.path.exists(p): print("skip",name); continue
    try:
        m=plugin_manager.install_zip(None,p); print("installed",name,m["id"],len(m.get("formats",[])))
    except Exception as e: print("FAIL",name,e)
