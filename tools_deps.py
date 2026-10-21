from importlib.metadata import requires, version, PackageNotFoundError
names=['mobi','h5py','onnx','tflite','dbf','access-parser','extract-msg','ezdxf','pyshp','fonttools','pefile','pyelftools','macholib','rpmfile','rawpy','psd-tools','lxml']
for n in names:
    try: print(n, version(n), requires(n))
    except Exception as e: print(n, 'ERR', e)
