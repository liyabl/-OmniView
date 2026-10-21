import importlib.util, os, shutil, json, zipfile, sysconfig
ROOT=r"F:\DeepSeek默认\OmniView3"
SITE=os.path.join(ROOT,"build_plugins"); SP=sysconfig.get_paths()["purelib"]
shutil.rmtree(SITE, ignore_errors=True); os.makedirs(SITE, exist_ok=True)
PKGS={
 "ebook":["mobi","loguru","imghdr","unidecode"],
 "data":["h5py","onnx","google","ml_dtypes","tflite","flatbuffers","dbf","aenum","access_parser","construct","tabulate","extract_msg","olefile","tzlocal","compressed_rtf","ebcdic","bs4","RTFDE","red_black_dict_mod","red_black_set_mod","chardet"],
 "pro":["ezdxf","pyparsing","shapefile","fontTools","pefile","elftools","macholib","altgraph","rpmfile","zstandard"],
 "raw":["rawpy","psd_tools","attrs"],
}
FORMATS={
 "ebook":["epub","mobi","azw3"],
 "data":["mdb","accdb","dbf","h5","hdf5","onnx","pt","pth","pkl","tflite","pb","msg","pst","ost","mbox"],
 "pro":["stl","obj","glb","gltf","3mf","fbx","usdz","dxf","dwg","shp","shx","prj","kml","kmz","geojson","gpx","exe","dll","so","dylib","sys","ttf","otf","woff","woff2","step","stp"],
 "raw":["psd","psb","ai","raw","cr2","cr3","nef","arw","dng","orf","rw2","raf","pef","srw"],
}
NAMES={"ebook":"电子书","data":"数据与模型","pro":"3D / CAD / GIS","raw":"RAW / PSD"}

def copy_name(name, site):
    spec=importlib.util.find_spec(name)
    if spec and spec.origin:
        if spec.submodule_search_locations:
            src=os.path.dirname(spec.origin); dst=os.path.join(site,name); shutil.copytree(src,dst,dirs_exist_ok=True); return True
        shutil.copy2(spec.origin,os.path.join(site,os.path.basename(spec.origin))); return True
    for cand in (os.path.join(SP,name), os.path.join(SP,name+".py")):
        if os.path.isdir(cand):
            shutil.copytree(cand,os.path.join(site,os.path.basename(cand)),dirs_exist_ok=True); return True
        if os.path.isfile(cand):
            shutil.copy2(cand,os.path.join(site,os.path.basename(cand))); return True
    return False

for pid,pkgs in PKGS.items():
    d=os.path.join(SITE,pid); site=os.path.join(d,"site-packages"); os.makedirs(site,exist_ok=True)
    missing=[]
    for name in pkgs:
        if not copy_name(name,site): missing.append(name)
    # native sidecar dirs if present
    for side in ("rawpy.libs","psd_tools.libs","h5py.libs"):
        src=os.path.join(SP,side)
        if os.path.isdir(src):
            shutil.copytree(src,os.path.join(site,side),dirs_exist_ok=True)
    if pid == "data" and not os.path.isdir(os.path.join(site, "google")):
        for base in sys.path:
            src = os.path.join(base, "google")
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(site, "google"))
                break
    json.dump({"id":pid,"name":NAMES[pid],"version":"0.3.0","formats":FORMATS[pid],"entry":""},open(os.path.join(d,"plugin.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    out=os.path.join(ROOT,"plugins",pid+".ovp")
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for base,dirs,files in os.walk(d):
            for f in files:
                p=os.path.join(base,f); z.write(p,os.path.relpath(p,d))
    print(pid,"missing",missing,"size",round(os.path.getsize(out)/1024/1024,1),"MB")
