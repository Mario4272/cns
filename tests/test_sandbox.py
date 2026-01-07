"""
Tests for WASM Sandbox using raw WAT (WebAssembly Text).
"""

import pytest

from cns_py.wasm import WasmSandbox, execute_rule

# A minimal valid WASM module that defines _start and memory.
# This verifies we can instantiate and run code.
# Testing complex WASI I/O via raw WAT is too brittle without a compiler.
WASI_NOOP_WAT = """
(module
    (memory (export "memory") 1)
    (func (export "_start")
        (nop)
    )
)
"""


def test_sandbox_initialization():
    """Verify engine startup."""
    sandbox = WasmSandbox()
    assert sandbox.engine is not None
    assert sandbox.linker is not None


def test_hello_world_execution():
    """Verify WASM can write to stdout (Hello)."""
    # Writes "{}" to stdout (1 byte brace + 1 byte brace)
    # Hex: 7b 7d
    # Decimal: 123 125
    wat = """
(module
    (import "wasi_snapshot_preview1" "fd_write" 
        (func $fd_write (param i32 i32 i32 i32) (result i32))
    )
    (memory 1)
    (export "memory" (memory 0))
    
    (func (export "_start")
        ;; {
        (i32.store8 (i32.const 100) (i32.const 123))
        ;; }
        (i32.store8 (i32.const 101) (i32.const 125))

        ;; IOVec
        (i32.store (i32.const 0) (i32.const 100))
        (i32.store (i32.const 4) (i32.const 2))
        
        (call $fd_write
            (i32.const 1)
            (i32.const 0)
            (i32.const 1)
            (i32.const 200)
        )
        (drop)
    )
)
"""
    result = execute_rule(wat.encode("utf-8"), {})
    assert result == {}


def test_execute_malformed_wasm():
    """Verify invalid WASM raises error."""
    # Module() raises WasmtimeError if invalid
    with pytest.raises(Exception):
        execute_rule(b"not a wasm binary", {})


WASI_LOOP_WAT = """
(module
    (func (export "_start")
        (loop
            (br 0)
        )
    )
)
"""


def test_fuel_limit_traps():
    """Verify infinite loop is terminated by fuel limit."""
    # Instantiation with low fuel
    sandbox = WasmSandbox(max_fuel=100)

    loop_bytes = WASI_LOOP_WAT.encode("utf-8")

    # Should raise generic Error/Trap
    with pytest.raises(Exception) as excinfo:
        from cns_py.wasm import execute_rule

        execute_rule(loop_bytes, {}, sandbox_instance=sandbox)

    # We might want to inspect if it says "fuel" but Exception is enough for now
    assert "fuel" in str(excinfo.value).lower() or "trap" in str(excinfo.value).lower()


def test_config_initialization():
    """Verify custom config setup."""
    sandbox = WasmSandbox(max_memory_pages=10, max_fuel=1000)
    assert sandbox.max_fuel == 1000
    # Attributes might be hidden in binding
    assert sandbox.config is not None
