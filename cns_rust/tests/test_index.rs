use cns_rust::domain::index::{FlatIndex, VectorIndex};

#[test]
fn test_flat_index_exact_match() {
    let mut index = FlatIndex::new();
    
    // Insert orthogonal vectors
    index.upsert(1, vec![1.0, 0.0]).unwrap();
    index.upsert(2, vec![0.0, 1.0]).unwrap();
    
    assert_eq!(index.len(), 2);
    
    // Query exact match for ID 1
    let results = index.search(&[1.0, 0.0], 1).unwrap();
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].0, 1);
    assert!((results[0].1 - 1.0).abs() < f32::EPSILON); // Cosine sim should be 1.0
}

#[test]
fn test_flat_index_nearest_neighbor() {
    let mut index = FlatIndex::new();
    
    // ID 1: [1, 0]
    // ID 2: [0.707, 0.707] (45 deg)
    // ID 3: [0, 1]
    index.upsert(1, vec![1.0, 0.0]).unwrap();
    index.upsert(2, vec![0.707106, 0.707106]).unwrap();
    index.upsert(3, vec![0.0, 1.0]).unwrap();
    
    // Query near ID 2
    let results = index.search(&[0.7, 0.7], 3).unwrap();
    
    // Top result should be ID 2
    assert_eq!(results[0].0, 2);
    
    // ID 1 and 3 should be roughly equidistant, but less than ID 2
    assert!(results[0].1 > results[1].1);
    assert!(results[0].1 > results[2].1);
}

#[test]
fn test_delete() {
    let mut index = FlatIndex::new();
    index.upsert(1, vec![1.0, 0.0]).unwrap();
    index.delete(1).unwrap();
    assert_eq!(index.len(), 0);
    
    let results = index.search(&[1.0, 0.0], 1).unwrap();
    assert!(results.is_empty());
}
