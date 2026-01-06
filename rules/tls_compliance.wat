(module
    ;; Import WASI fd_write
    (import "wasi_snapshot_preview1" "fd_write" (func $fd_write (param i32 i32 i32 i32) (result i32)))
    
    (memory (export "memory") 1)
    
    ;; Data: Output JSON
    ;; {"findings": [{"kind": "compliance_violation", "severity": "high", "message": "Weak crypto algo detected (Simulated)", "refs": []}]}
    ;; Length: 132 approx. Let's make it exact.
    (data (i32.const 100) "{\"findings\":[{\"kind\":\"compliance_violation\",\"severity\":\"high\",\"message\":\"Weak crypto algo detected (Simulated)\",\"refs\":[]}]}")
    
    (func (export "_start")
        ;; Setup IOVec at offset 0
        ;; iov.base = 100 (data start)
        (i32.store (i32.const 0) (i32.const 100))
        ;; iov.len = 124
        (i32.store (i32.const 4) (i32.const 124))
        
        ;; Call fd_write(1 [stdout], 0 [iov ptr], 1 [iov count], 200 [written_ptr])
        (call $fd_write
            (i32.const 1)
            (i32.const 0)
            (i32.const 1)
            (i32.const 200)
        )
        (drop) ;; drop result
    )
)
