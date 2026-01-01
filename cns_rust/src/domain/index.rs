use anyhow::Result;
use std::collections::HashMap;

/// simple Cosine Similarity: (A . B) / (|A| * |B|)
fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    let dot_product: f32 = a.iter().zip(b).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    
    dot_product / (norm_a * norm_b)
}

// Using async-trait likely not needed for simple impl, but keeping async fn for future compatibility
pub trait VectorIndex {
    fn upsert(&mut self, id: u64, vector: Vec<f32>) -> Result<()>;
    fn search(&self, query: &[f32], k: usize) -> Result<Vec<(u64, f32)>>;
    fn delete(&mut self, id: u64) -> Result<()>;
    fn len(&self) -> usize;
}

/// Naive Flat Index (In-Memory)
/// Stores vectors in a HashMap and performs full scan for search.
pub struct FlatIndex {
    storage: HashMap<u64, Vec<f32>>,
}

impl FlatIndex {
    pub fn new() -> Self {
        Self {
            storage: HashMap::new(),
        }
    }
}

impl VectorIndex for FlatIndex {
    fn upsert(&mut self, id: u64, vector: Vec<f32>) -> Result<()> {
        self.storage.insert(id, vector);
        Ok(())
    }

    fn search(&self, query: &[f32], k: usize) -> Result<Vec<(u64, f32)>> {
        let mut scores: Vec<(u64, f32)> = self.storage
            .iter()
            .map(|(id, vec)| (*id, cosine_similarity(query, vec)))
            .collect();

        // Sort by score descending
        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        
        // Take top k
        Ok(scores.into_iter().take(k).collect())
    }

    fn delete(&mut self, id: u64) -> Result<()> {
        self.storage.remove(&id);
        Ok(())
    }
    
    fn len(&self) -> usize {
        self.storage.len()
    }
}
