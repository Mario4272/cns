use serde::{Deserialize, Serialize};
use std::io::{self, Read, Write};

// Input Contract
#[derive(Deserialize)]
struct InputClaim {
    subject_ids: Vec<String>,
    facts: Vec<Fact>,
    context: Option<Context>,
}

#[derive(Deserialize)]
struct Fact {
    predicate: String,
    object: String,
}

#[derive(Deserialize)]
struct Context {
    trigger: Option<String>,
}

// Output Contract
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
    // 1. Read Input JSON from Stdin
    let mut buffer = String::new();
    if let Err(_) = io::stdin().read_to_string(&mut buffer) {
        return; // Fail silently or log? WASI has no easy log.
    }

    let input: InputClaim = match serde_json::from_str(&buffer) {
        Ok(v) => v,
        Err(_) => return, // Invalid input
    };
    
    // 2. Logic: Check for weak TLS
    let mut findings = Vec::new();
    
    for fact in &input.facts {
        if fact.predicate == "uses_algo" && (fact.object == "tls1.0" || fact.object == "tls1.1" || fact.object == "tls1.2") {
            findings.push(Finding {
                kind: "compliance_violation".to_string(),
                severity: "high".to_string(),
                message: format!("Weak crypto algo detected: {}", fact.object),
                refs: input.subject_ids.clone(),
            });
        }
    }
    
    // 3. Write Output JSON
    let output = OutputFindings { findings };
    let json_out = serde_json::to_string(&output).unwrap();
    
    io::stdout().write_all(json_out.as_bytes()).unwrap();
}
