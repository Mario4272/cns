(module
    (import "wasi_snapshot_preview1" "fd_write" (func $fd_write (param i32 i32 i32 i32) (result i32)))
    (memory (export "memory") 1)
    
    ;; Data: Output JSON
    (data (i32.const 100) "{\"findings\":[{\"kind\":\"contradiction\",\"severity\":\"medium\",\"message\":\"Contradiction detected (Simulated)\",\"refs\":[]}]}")
    
    (func (export "_start")
        (i32.store (i32.const 0) (i32.const 100))
        (i32.store (i32.const 4) (i32.const 116))
        
        (call $fd_write
            (i32.const 1)
            (i32.const 0)
            (i32.const 1)
            (i32.const 200)
        )
        (drop)
    )
)
