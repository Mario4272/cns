# CNS Visualization: IB Explorer

## Vision

**IB Explorer** transforms the CNS intelligence substrate into a navigable, multi-dimensional space. Unlike traditional database UIs that show tables and rows, IB Explorer reveals the **structure of intelligence** itself.

Think: **Google Earth for knowledge graphs** meets **galaxy visualization** meets **time travel**.

---

## Core Metaphor: Intelligence as Cosmos

### Atoms = Stars
- **Visual**: Glowing points in 3D space
- **Color coding**:
  - 🔵 Blue: Entities (people, organizations, systems)
  - 🟢 Green: Concepts (protocols, standards, ideas)
  - 🟡 Yellow: Rules (logic, constraints, policies)
  - 🔴 Red: Programs (executable code, learners)
- **Size**: Proportional to connection count (degree centrality)
- **Brightness**: Proportional to belief/confidence

### Fibers = Edges
- **Visual**: Glowing lines connecting atoms
- **Thickness**: Proportional to belief strength
- **Animation**: Pulse effect based on recency (fresh data pulses faster)
- **Color**: Inherits from source atom, fades toward destination
- **Style**:
  - Solid: High confidence (belief ≥ 0.8)
  - Dashed: Medium confidence (0.5 ≤ belief < 0.8)
  - Dotted: Low confidence (belief < 0.5)

### Contradictions = Lightning
- **Visual**: Jagged red/orange arcs between conflicting atoms
- **Animation**: Spark/flash effect to draw attention
- **Interaction**: Click to see contradiction details panel

### Clusters = Constellations
- **Visual**: At high zoom levels, related atoms form named constellations
- **Labels**: Semantic cluster names (e.g., "Security Protocols", "Legal Framework")
- **Boundaries**: Subtle glow outline around cluster regions

---

## Navigation Modes

### 1. Spatial Navigation (Default)
- **Zoom out**: See the full intelligence landscape as constellations
- **Zoom in**: Dive into individual atoms and their immediate neighborhoods
- **Pan**: Drag to explore different regions
- **Rotate**: 3D rotation for better perspective

### 2. Time Travel Mode
- **Time slider**: Scrub through temporal dimension
- **Effects**:
  - Atoms/fibers fade in when they become valid
  - Atoms/fibers fade out when they expire
  - Belief values animate (color/brightness changes)
  - Contradictions appear/disappear based on temporal overlap
- **Playback**: Auto-play to watch evolution over time
- **Bookmarks**: Save interesting temporal snapshots

### 3. Provenance Mode
- **Filter by source**: Show only atoms/fibers from specific sources
- **Color by source**: Different colors for different data sources
- **Citation trails**: Highlight provenance chains (derived from → original)
- **Signature verification**: Visual indicator for signed vs unsigned data

### 4. Query Mode
- **CQL input**: Type queries directly
- **Result highlighting**: Matching atoms glow brighter
- **Path visualization**: Show traversal paths for graph queries
- **Explain overlay**: Visualize query execution plan

### 5. Contradiction Explorer
- **Filter**: Show only contradicting atoms/fibers
- **Highlight**: Contradictions flash with lightning effect
- **Panel**: Side panel shows contradiction details, belief scores, sources
- **Resolution**: UI to mark contradictions as resolved or accept one version

---

## UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  CNS IB Explorer                    [Mode: Spatial ▼]  [⚙️]  │
├─────────────────────────────────────────────────────────────┤
│  🔍 Search/CQL: [MATCH (e:Entity) WHERE...]          [▶️]   │
├──────────────────────┬──────────────────────────────────────┤
│                      │                                      │
│   📊 Filters         │                                      │
│   ☐ Entities         │         🌌 Main Canvas              │
│   ☐ Concepts         │      (WebGL/Three.js)               │
│   ☐ Rules            │                                      │
│   ☐ Programs         │     [Interactive 3D visualization]   │
│                      │                                      │
│   🎚️ Belief          │                                      │
│   [====●====] ≥0.5   │                                      │
│                      │                                      │
│   📅 Time Range      │                                      │
│   [2020 ●────● 2025] │                                      │
│                      │                                      │
│   📌 Sources         │                                      │
│   ☑ Source A         │                                      │
│   ☐ Source B         │                                      │
│                      │                                      │
├──────────────────────┴──────────────────────────────────────┤
│  ⏮️ ⏸️ ⏯️ ⏭️  Time: 2025-01-15 [━━━━●━━━━━━━━━━━━━━━━━━━]  │
└─────────────────────────────────────────────────────────────┘
```

### Detail Panel (appears on click)
```
┌─────────────────────────────────────┐
│  Atom: FrameworkX                   │
│  Kind: Entity                       │
│  Belief: 0.94 ⭐⭐⭐⭐⭐              │
├─────────────────────────────────────┤
│  📝 Text:                           │
│  "Enterprise security framework..." │
│                                     │
│  🔗 Fibers (5):                     │
│  → supports_tls: TLS1.3 (0.98)     │
│  → requires: Authentication (0.92)  │
│  → documented_in: RFC9999 (0.85)   │
│  ...                                │
│                                     │
│  📚 Provenance (3):                 │
│  • source_id: doc_12345            │
│    uri: https://example.com/...    │
│    fetched: 2025-01-10             │
│  • source_id: manual_entry_42      │
│    ...                              │
│                                     │
│  ⚡ Contradictions (1):             │
│  • Conflicts with FrameworkY on    │
│    "supports_tls" during           │
│    2024-12-01 to 2025-01-01        │
│    [View Details]                   │
└─────────────────────────────────────┘
```

---

## Technical Implementation

### Stack
- **Frontend**: React + TypeScript
- **3D Engine**: Three.js + react-three-fiber
- **Layout**: Force-directed graph (d3-force-3d) or UMAP projection
- **Performance**:
  - Level-of-detail (LOD): Simplified rendering at distance
  - Instancing: Efficient rendering of thousands of atoms
  - Frustum culling: Only render visible objects
  - Web Workers: Offload layout computation

### Data Pipeline
```
CNS Backend (Postgres)
    ↓
Arrow Flight / gRPC
    ↓
Frontend State (Redux/Zustand)
    ↓
Three.js Scene Graph
    ↓
WebGL Renderer
```

### Performance Targets
- **60 FPS** on 10,000 atoms + 50,000 fibers (laptop GPU)
- **< 100ms** detail panel load on atom click
- **< 500ms** time slider scrub response
- **< 1s** CQL query → visualization update

### Optimizations
1. **Spatial indexing**: Octree for fast neighbor queries
2. **Texture atlases**: Batch similar atoms into single draw call
3. **Shader-based effects**: GPU-accelerated glow, pulse, lightning
4. **Progressive loading**: Load visible region first, stream rest
5. **Caching**: Cache layout positions, recompute only on data change

---

## Interaction Patterns

### Mouse/Touch
- **Left-click**: Select atom (show detail panel)
- **Right-click**: Context menu (expand neighbors, hide, bookmark)
- **Drag**: Pan camera
- **Scroll**: Zoom in/out
- **Shift+drag**: Rotate camera
- **Double-click**: Focus on atom (zoom + center)

### Keyboard
- **Space**: Toggle time playback
- **Arrow keys**: Navigate time slider
- **F**: Focus on selected atom
- **H**: Toggle help overlay
- **Esc**: Clear selection
- **Ctrl+F**: Focus search bar
- **1-4**: Switch atom kind filters

---

## Future Enhancements (Phase 6+)

### XR Integration
- **VR Mode**: Walk through your intelligence base in VR
- **Hand tracking**: Grab and manipulate atoms/fibers
- **Spatial audio**: Contradictions emit warning sounds
- **Immersive time travel**: Step through time physically

### Collaborative Features
- **Multi-user**: See other users' cursors and selections
- **Annotations**: Leave notes on atoms/fibers
- **Shared views**: Save and share camera positions + filters
- **Live updates**: Real-time sync as new data arrives

### AI Assistance
- **Guided tours**: AI suggests interesting patterns to explore
- **Anomaly detection**: Highlight unusual structures
- **Query suggestions**: Auto-complete CQL based on visible data
- **Narrative generation**: AI explains what you're looking at

### Advanced Visualizations
- **Heatmaps**: Overlay belief density, contradiction density
- **Flow animations**: Show data propagation through provenance chains
- **Diff mode**: Compare two temporal snapshots side-by-side
- **Multi-space view**: Split screen for different embedding spaces

---

## Demo Scenarios

### 1. TLS Evolution Demo
- Load demo data (TLS 1.2 → 1.3 supersession)
- Zoom to FrameworkX atom
- Scrub time slider from 2024 to 2025
- Watch fiber change from TLS1.2 to TLS1.3
- Click to see provenance and belief scores

### 2. Contradiction Discovery
- Load data with known contradictions
- Switch to Contradiction Explorer mode
- See lightning arcs between conflicting atoms
- Click contradiction to see details
- Use time slider to see when contradiction emerged

### 3. Provenance Audit
- Switch to Provenance Mode
- Filter by specific source
- See citation trails (derived → original)
- Verify signatures (green checkmark for valid)
- Trace back to original documents

---

## Success Metrics

- **Engagement**: Users spend > 5 min exploring (vs < 1 min in table UI)
- **Discovery**: Users find contradictions 3x faster than SQL queries
- **Comprehension**: Users correctly answer "what changed when" questions 80%+ accuracy
- **Performance**: Maintains 60 FPS on target hardware
- **Adoption**: 50%+ of CNS users prefer IB Explorer over raw CQL

---

## References

- Three.js: https://threejs.org/
- react-three-fiber: https://docs.pmnd.rs/react-three-fiber
- d3-force-3d: https://github.com/vasturiano/d3-force-3d
- WebGL best practices: https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/WebGL_best_practices
