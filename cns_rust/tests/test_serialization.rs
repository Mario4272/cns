use cns_rust::domain::{Atom, Fiber, Aspect};
use serde_json::json;

#[test]
fn test_atom_serialization() {
    let atom = Atom {
        id: 1,
        kind: "Entity".to_string(),
        label: "Test".to_string(),
        text: None,
    };
    let json = serde_json::to_string(&atom).unwrap();
    assert_eq!(json, r#"{"id":1,"kind":"Entity","label":"Test","text":null}"#);
}

#[test]
fn test_fiber_serialization() {
    let fiber = Fiber {
        id: 10,
        src: 1,
        dst: 2,
        predicate: "relates_to".to_string(),
    };
    let json = serde_json::to_string(&fiber).unwrap();
    assert_eq!(json, r#"{"id":10,"src":1,"dst":2,"predicate":"relates_to"}"#);
}
