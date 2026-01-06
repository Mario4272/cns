"""
WASM Sandbox using Wasmtime.
Uses WASI (stdin/stdout) for JSON-in/JSON-out communication.
"""

import json
import os
import tempfile
from typing import Any, Dict, Optional

from wasmtime import Engine, Linker, Module, Store, WasiConfig


class WasmSandbox:
    def __init__(self, max_memory_pages: int = 160, max_fuel: Optional[int] = None):
        """
        Args:
            max_memory_pages: Max linear memory pages (64KB each). Default ~10MB.
            max_fuel: Max instructions to execute (if None, unlimited).
        """
        from wasmtime import Config

        self.config = Config()
        if max_fuel is not None:
            self.config.consume_fuel = True

        self.engine = Engine(self.config)
        self.linker = Linker(self.engine)
        self.linker.define_wasi()

        self.max_fuel = max_fuel

    def execute(self, wasm_bytes: bytes, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a WASM binary with the given input data.
        """
        # Windows-safe approach: Create named temp files, close them, pass paths to WASI.
        # Wasmtime needs to open them itself.

        stdin_fd, stdin_path = tempfile.mkstemp()
        stdout_fd, stdout_path = tempfile.mkstemp()

        try:
            # Prepare Input
            input_json = json.dumps(input_data).encode("utf-8")
            os.write(stdin_fd, input_json)
            os.close(stdin_fd)  # Close handle so WASM can open it
            os.close(stdout_fd)  # Close handle so WASM can open it (and we read later)

            # Configure WASI
            wasi = WasiConfig()
            wasi.stdin_file = stdin_path
            wasi.stdout_file = stdout_path
            wasi.inherit_stderr()  # Useful for debug

            store = Store(self.engine)
            store.set_wasi(wasi)

            if self.max_fuel is not None:
                store.add_fuel(self.max_fuel)

            # Instantiate
            module = Module(self.engine, wasm_bytes)
            instance = self.linker.instantiate(store, module)

            # Execute
            start = instance.exports(store).get("_start")
            if start is None:
                raise RuntimeError("WASM module must export '_start'")

            error = None
            try:
                start(store)
            except Exception as e:
                # Wasmtime raises Trap for any WASI exit(1), but exit(0)
                # might also look like exception?
                error = e

            # Read Output
            with open(stdout_path, "rb") as f:
                output_bytes = f.read()

            if error:
                # If we have output (e.g. partial write before crash?)
                pass

        finally:
            # Cleanup
            if os.path.exists(stdin_path):
                try:
                    os.unlink(stdin_path)
                except OSError:
                    pass
            if os.path.exists(stdout_path):
                try:
                    os.unlink(stdout_path)
                except OSError:
                    pass

        if not output_bytes:
            return {}

        try:
            return json.loads(output_bytes.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"WASM returned invalid JSON: {output_bytes.decode('utf-8', errors='replace')}"
            ) from e


# Default instance (unlimited by default)
_SANDBOX = WasmSandbox()


def execute_rule(
    wasm_bytes: bytes, input_data: Dict[str, Any], sandbox_instance: Optional[WasmSandbox] = None
) -> Dict[str, Any]:
    sandbox = sandbox_instance if sandbox_instance else _SANDBOX
    return sandbox.execute(wasm_bytes, input_data)


# Alias for compatibility
execute_binary = execute_rule
