import os
import sys

sys.path.append(os.getcwd())

try:
    import cns_py.wasm
    print("cns_py.wasm imported successfully")
    print("dir(cns_py.wasm):", dir(cns_py.wasm))
    from cns_py.wasm import WasmSandbox, execute_binary
    print("Target names imported successfully")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
