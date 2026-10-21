import sys, os, shutil
ROOT=r"F:\DeepSeek默认\OmniView3"; site=os.path.join(ROOT,"build_plugins","data","site-packages")
for base in sys.path:
    src=os.path.join(base,"google")
    if os.path.isdir(src) and not os.path.isdir(os.path.join(site,"google")):
        shutil.copytree(src,os.path.join(site,"google")); print("copied",src); break
else: print("not found")
