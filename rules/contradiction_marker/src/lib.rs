use serde::{Deserialize, Serialize};
use std::io::{self, Read, Write};

#[derive(Deserialize)]
struct InputClaim {
    subject_ids: Vec<String>,
    // Contradictions might be explicitly passed in 'context' or 'facts'
    // For Slice 10.2, let's assume `context.contradictions_count` > 0 triggers it.
    context: Option<Context>,
}

#[derive(Deserialize)]
struct Context {
    contradictions_count: Option<u32>,
}

#[derive(Serialize)]
struct OutputFindings {
    findings: Vec<Finding>,
}

#[derive(Serialize)]
struct Finding {
    kind: String,
    severity: String,
    message: String,
    refs: Vec<String>,
}

#[no_mangle]
pub extern "C" fn _start() {
    let mut buffer = String::new();
    if let Err(_) = io::stdin().read_to_string(&mut buffer) {
        return;
    }

    let input: InputClaim = match serde_json::from_str(&buffer) {
        Ok(v) => v,
        Err(_) => return,
    };
    
    let mut findings = Vec::new();
    
    if let Some(ctx) = input.context {
        if let Some(count) = ctx.contradictions_count {
            if count > 0 {
                findings.push(Finding {
                    kind: "contradiction".to_string(),
                    severity: "medium".to_string(),
                    message: format!("Found {} contradictions for subject", count),
                    refs: input.subject_ids.clone(),
                });
            }
        }
    }
    
    let output = OutputFindings { findings };
    let json_out = serde_json::to_string(&output).unwrap();
    io::stdout().write_all(json_out.as_bytes()).unwrap();
}
