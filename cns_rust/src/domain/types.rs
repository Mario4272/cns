use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Atom {
    pub id: u64,
    pub kind: String,
    pub label: String,
    pub text: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Fiber {
    pub id: u64,
    pub src: u64,
    pub dst: u64,
    pub predicate: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Aspect {
    pub id: u64,
    pub subject_kind: String, // "atom" | "fiber"
    pub subject_id: u64,
    pub belief: f64,
    pub valid_from: Option<chrono::DateTime<chrono::Utc>>,
    pub valid_to: Option<chrono::DateTime<chrono::Utc>>,
    pub observed_at: chrono::DateTime<chrono::Utc>,
}
