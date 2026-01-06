import sys
import os

print(f"CWD: {os.getcwd()}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
print(f"sys.path: {sys.path}")

try:
    import cns_py
    print(f"cns_py file: {cns_py.__file__}")
    import cns_py.wasm
    print(f"cns_py.wasm file: {cns_py.wasm.__file__}")
    from cns_py.wasm import execute_binary
    print("Imported execute_binary successfully")
    import cns_py.api.server
    print("Imported server successfully")
except Exception as e:
    print(f"Error: {e}")
