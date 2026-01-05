import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

const API_BASE = "http://127.0.0.1:8000"; // CNS FastAPI server

let labelInput: HTMLInputElement | null;
let hopsInput: HTMLInputElement | null;
let limitInput: HTMLInputElement | null;
let asofInput: HTMLInputElement | null;
let loadButton: HTMLButtonElement | null;
let statusEl: HTMLElement | null;
let canvasContainer: HTMLDivElement | null;
let predicateFilterInput: HTMLInputElement | null;
let debugNodesEl: HTMLElement | null;
let debugEdgesEl: HTMLElement | null;
let debugEdgesEl: HTMLElement | null;
let debugModeSelect: HTMLSelectElement | null;

// Details Panel Elements
let detailsPanel: HTMLElement | null;
let detailIdEl: HTMLElement | null;
let detailLabelEl: HTMLElement | null;
let detailKindEl: HTMLElement | null;
let closeDetailsBtn: HTMLElement | null;
let findSimilarBtn: HTMLButtonElement | null;
let similarStatusEl: HTMLElement | null;
let similarResultsEl: HTMLElement | null;

// State
let selectedNodeId: number | null = null;
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

let scene: THREE.Scene | null = null;
let camera: THREE.PerspectiveCamera | null = null;
let renderer: THREE.WebGLRenderer | null = null;
let controls: OrbitControls | null = null;
let nodeGroup: THREE.Group | null = null;
let edgeGroup: THREE.Group | null = null;

function initScene() {
  if (!canvasContainer) return;

  const width = canvasContainer.clientWidth || 800;
  const height = canvasContainer.clientHeight || 600;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x020617);

  camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
  camera.position.set(0, 0, 40);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  canvasContainer.innerHTML = "";
  canvasContainer.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  const ambient = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambient);
  const dir = new THREE.DirectionalLight(0xffffff, 0.8);
  dir.position.set(10, 10, 20);
  scene.add(dir);

  nodeGroup = new THREE.Group();
  edgeGroup = new THREE.Group();
  scene.add(nodeGroup);
  scene.add(edgeGroup);

  animate();
}

function animate() {
}
}

function onCanvasClick(event: MouseEvent) {
  if (!nodeGroup || !camera || !renderer) return;

  // Calculate mouse position in normalized device coordinates
  // (-1 to +1) for both components
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);

  // Raycast against node meshes
  const intersects = raycaster.intersectObjects(nodeGroup.children);

  if (intersects.length > 0) {
    // Select the first one
    const mesh = intersects[0].object as THREE.Mesh;
    // We need to map mesh back to node ID. 
    // We can store ID in userData during render.
    const id = mesh.userData.id;
    if (typeof id === 'number') {
      selectNode(id);
    }
  } else {
    // Deselect if clicked background
    // closeDetails(); // Optional: maybe keep it open
  }
}

function selectNode(id: number) {
  selectedNodeId = id;
  // Highlight? (Could change material color)

  // Find node data (we have NeighborhoodResponse data... wait, we need access to current data)
  // Let's modify renderGraph to store current data globally or look it up from specific nodes.
  // Or we passed data to renderGraph. Let's make `currentData` global or retrieve from DOM/userData.
  // Best: Store full node data in userData.

  // Actually, we can't easily access the Mesh userData here without finding the mesh again.
  // Let's iterate nodeGroup to find the mesh with this ID.
  const mesh = nodeGroup?.children.find((c) => c.userData.id === id);
  const nodeData = mesh?.userData.node as NeighborhoodNode | undefined;

  if (nodeData && detailsPanel) {
    detailsPanel.classList.remove('hidden');
    if (detailIdEl) detailIdEl.textContent = String(nodeData.id);
    if (detailLabelEl) detailLabelEl.textContent = nodeData.label;
    if (detailKindEl) detailKindEl.textContent = nodeData.kind || "N/A";

    // Reset Similar section
    if (similarResultsEl) similarResultsEl.innerHTML = "";
    if (similarStatusEl) similarStatusEl.textContent = "";
  }
}

function closeDetails() {
  if (detailsPanel) detailsPanel.classList.add('hidden');
  selectedNodeId = null;
}

async function findSimilar() {
  if (selectedNodeId == null) return;
  if (!similarStatusEl || !similarResultsEl) return;

  similarStatusEl.textContent = "Searching...";
  similarResultsEl.innerHTML = "";

  try {
    const payload = {
      atom_id: String(selectedNodeId),
      k: 10
    };

    const resp = await fetch(`${API_BASE}/graph/similar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      statusEl!.textContent = "Search failed.";
      similarStatusEl.textContent = "Error " + resp.status;
      return;
    }

    const data = await resp.json();
    const results = data.results || [];

    if (results.length === 0) {
      similarStatusEl.textContent = "No matches.";
      return;
    }

    similarStatusEl.textContent = `Found ${results.length}`;

    // Render
    const frag = document.createDocumentFragment();
    results.forEach((res: any) => {
      const li = document.createElement("li");
      li.className = "similar-item";

      // Header (Label + Score)
      const header = document.createElement("div");
      header.className = "sim-header";

      const labelSpan = document.createElement("span");
      labelSpan.textContent = res.label || res.id;

      const scoreSpan = document.createElement("span");
      scoreSpan.className = "sim-score";
      scoreSpan.textContent = res.score.toFixed(3);

      header.appendChild(labelSpan);
      header.appendChild(scoreSpan);
      li.appendChild(header);

      // Meta (Kind)
      if (res.kind) {
        const meta = document.createElement("div");
        meta.className = "sim-meta";
        meta.textContent = res.kind;
        li.appendChild(meta);
      }

      li.onclick = () => {
        // Navigate to this node
        if (labelInput && res.label) {
          labelInput.value = res.label;
          loadNeighborhood();
        }
      };

      frag.appendChild(li);
    });

    similarResultsEl.appendChild(frag);

  } catch (err) {
    console.error(err);
    similarStatusEl.textContent = "Error";
  }
}

type NeighborhoodNode = {
  id: number;
  label: string;
  kind?: string | null;
  belief?: number | null;
  x?: number | null;
  y?: number | null;
  z?: number | null;
};
type NeighborhoodEdge = {
  id: number;
  src_id: number;
  dst_id: number;
  predicate: string;
  belief?: number | null;
};
type NeighborhoodResponse = {
  center_node_id: number | null;
  hops: number;
  asof: string | null;
  truncated: boolean;
  nodes: NeighborhoodNode[];
  edges: NeighborhoodEdge[];
};

function layoutNodes(nodes: NeighborhoodNode[], centerId: number | null) {
  const positions = new Map<number, THREE.Vector3>();
  const n = nodes.length;
  const radius = Math.max(10, 4 + n * 0.5);

  const central =
    centerId != null
      ? nodes.find((node) => node.id === centerId) ?? null
      : null;
  if (central) {
    positions.set(central.id, new THREE.Vector3(0, 0, 0));
  }

  let angleIdx = 0;
  for (const node of nodes) {
    if (positions.has(node.id)) continue;
    if (node.x != null && node.y != null && node.z != null) {
      positions.set(node.id, new THREE.Vector3(node.x, node.y, node.z));
      continue;
    }

    const angle = (angleIdx / Math.max(1, n - 1)) * Math.PI * 2;
    const x = radius * Math.cos(angle);
    const y = radius * Math.sin(angle);
    const z = (Math.random() - 0.5) * radius * 0.3;
    positions.set(node.id, new THREE.Vector3(x, y, z));
    angleIdx += 1;
  }
  return positions;
}

function renderGraph(data: NeighborhoodResponse) {
  if (!nodeGroup || !edgeGroup || !statusEl) return;

  nodeGroup.clear();
  edgeGroup.clear();

  const nodes = data.nodes || [];
  const edges = data.edges || [];
  if (!nodes.length) {
    statusEl.textContent = "No nodes returned.";
    return;
  }

  const positions = layoutNodes(nodes, data.center_node_id);

  const sphereGeom = new THREE.SphereGeometry(0.6, 16, 16);
  const matCentral = new THREE.MeshStandardMaterial({ color: 0x38bdf8 });
  const matOther = new THREE.MeshStandardMaterial({ color: 0x6366f1 });

  for (const node of nodes) {
    const pos = positions.get(node.id) || new THREE.Vector3();
    const isCentral = data.center_node_id != null && node.id === data.center_node_id;
    const mesh = new THREE.Mesh(sphereGeom, isCentral ? matCentral : matOther);
    mesh.position.copy(pos);
    mesh.userData = { id: node.id, node: node }; // Store data for raycasting
    nodeGroup.add(mesh);
  }

  // Collapse multi-edges by (src_id, dst_id) for rendering clarity.
  const edgeGroups = new Map<string, { src_id: number; dst_id: number; count: number; maxConf: number }>();
  for (const e of edges) {
    const key = `${e.src_id}|${e.dst_id}`;
    const conf = e.belief ?? 0.5;
    const existing = edgeGroups.get(key);
    if (existing) {
      existing.count += 1;
      existing.maxConf = Math.max(existing.maxConf, conf);
    } else {
      edgeGroups.set(key, { src_id: e.src_id, dst_id: e.dst_id, count: 1, maxConf: conf });
    }
  }

  const edgeMat = new THREE.LineBasicMaterial({ color: 0x4b5563, linewidth: 1, transparent: true });
  for (const group of edgeGroups.values()) {
    const srcPos = positions.get(group.src_id);
    const dstPos = positions.get(group.dst_id);
    if (!srcPos || !dstPos) continue;

    // Adjust opacity based on confidence
    const opacity = Math.max(0.2, group.maxConf);
    const mat = edgeMat.clone();
    mat.opacity = opacity;

    const geom = new THREE.BufferGeometry().setFromPoints([srcPos, dstPos]);
    const line = new THREE.Line(geom, mat);
    edgeGroup.add(line);
  }

  const truncatedSuffix = data.truncated ? " (truncated)" : "";
  const centerInfo =
    data.center_node_id != null ? `, center_id=${data.center_node_id}` : "";
  const predicateFilter = predicateFilterInput?.value.trim() ?? "";
  const predicateInfo = predicateFilter ? `, predicate=${predicateFilter}` : "";
  statusEl.textContent = `Rendered ${nodes.length} nodes, ${edgeGroups.size} edge groups (${edges.length} edges)${centerInfo}${predicateInfo}${truncatedSuffix}.`;

  renderDebugPanel(data);
}

function renderDebugPanel(data: NeighborhoodResponse) {
  if (!debugNodesEl || !debugEdgesEl) return;

  const nodes = data.nodes || [];
  const edges = data.edges || [];
  const labelById = new Map<number, string>();
  for (const n of nodes) {
    labelById.set(n.id, n.label);
  }

  debugNodesEl.textContent = nodes
    .map((n) => `${n.id}: ${n.label}`)
    .join("\n");

  const predicateFilter = predicateFilterInput?.value.trim() ?? "";
  const mode = debugModeSelect?.value ?? "unique";
  const maxRows = 200;

  if (mode === "raw") {
    const rows: string[] = [];
    for (const e of edges) {
      if (predicateFilter && e.predicate !== predicateFilter) {
        continue;
      }
      const srcLabel = labelById.get(e.src_id) ?? String(e.src_id);
      const dstLabel = labelById.get(e.dst_id) ?? String(e.dst_id);
      rows.push(`${srcLabel} --${e.predicate}--> ${dstLabel}`);
      if (rows.length >= maxRows) {
        rows.push("… (truncated in debug panel)");
        break;
      }
    }

    debugEdgesEl.textContent = rows.length
      ? rows.join("\n")
      : "<no edges match filter>";
    return;
  }

  // Unique mode: aggregate by signature and show counts.
  type EdgeAgg = { srcLabel: string; predicate: string; dstLabel: string; count: number };
  const counts = new Map<string, EdgeAgg>();
  for (const e of edges) {
    if (predicateFilter && e.predicate !== predicateFilter) {
      continue;
    }
    const srcLabel = labelById.get(e.src_id) ?? String(e.src_id);
    const dstLabel = labelById.get(e.dst_id) ?? String(e.dst_id);
    const sig = `${srcLabel}||${e.predicate}||${dstLabel}`;
    const existing = counts.get(sig);
    if (existing) {
      existing.count += 1;
    } else {
      counts.set(sig, { srcLabel, predicate: e.predicate, dstLabel, count: 1 });
    }
  }

  const aggs = Array.from(counts.values());
  aggs.sort((a, b) => {
    if (b.count !== a.count) return b.count - a.count;
    const sa = `${a.srcLabel}--${a.predicate}-->${a.dstLabel}`;
    const sb = `${b.srcLabel}--${b.predicate}-->${b.dstLabel}`;
    return sa.localeCompare(sb);
  });

  const lines: string[] = [];
  for (const a of aggs) {
    lines.push(`${a.srcLabel} --${a.predicate}--> ${a.dstLabel} (x${a.count})`);
    if (lines.length >= maxRows) {
      lines.push("… (truncated in debug panel)");
      break;
    }
  }

  debugEdgesEl.textContent = lines.length
    ? lines.join("\n")
    : "<no edges match filter>";
}

async function loadNeighborhood() {
  if (!labelInput || !hopsInput || !limitInput || !statusEl) return;

  const label = labelInput.value.trim();
  const hops = parseInt(hopsInput.value || "1", 10) || 1;
  const limit = parseInt(limitInput.value || "100", 10) || 100;
  const asofRaw = asofInput?.value.trim() ?? "";

  if (!label) {
    statusEl.textContent = "Enter a label first.";
    return;
  }

  statusEl.textContent = "Loading neighborhood…";

  try {
    const params = new URLSearchParams();
    params.set("label", label);
    params.set("hops", String(hops));
    params.set("limit", String(limit));
    if (asofRaw) {
      params.set("asof", asofRaw);
    }

    const resp = await fetch(`${API_BASE}/graph/neighborhood?${params.toString()}`);
    if (!resp.ok) {
      const detail = await resp.json().catch(() => ({}));
      statusEl.textContent = `Error ${resp.status}: ${detail.detail || "request failed"}`;
      return;
    }
    const data = (await resp.json()) as NeighborhoodResponse;
    renderGraph(data);
  } catch (err) {
    console.error(err);
    statusEl.textContent = "Network or server error; see console.";
  }
}

window.addEventListener("DOMContentLoaded", () => {
  labelInput = document.querySelector("#label-input");
  hopsInput = document.querySelector("#hops-input");
  limitInput = document.querySelector("#limit-input");
  asofInput = document.querySelector("#asof-input");
  loadButton = document.querySelector("#load-btn");
  statusEl = document.querySelector("#status");
  canvasContainer = document.querySelector("#scene-container");
  predicateFilterInput = document.querySelector("#predicate-filter");
  debugNodesEl = document.querySelector("#debug-nodes");
  debugEdgesEl = document.querySelector("#debug-edges");
  debugModeSelect = document.querySelector("#debug-mode");

  // Details UI
  detailsPanel = document.querySelector("#details-panel");
  detailIdEl = document.querySelector("#detail-id");
  detailLabelEl = document.querySelector("#detail-label");
  detailKindEl = document.querySelector("#detail-kind");
  closeDetailsBtn = document.querySelector("#close-details-btn");
  findSimilarBtn = document.querySelector("#find-similar-btn");
  similarStatusEl = document.querySelector("#similar-status");
  similarResultsEl = document.querySelector("#similar-results");

  initScene();

  // Event Listeners
  canvasContainer?.addEventListener('click', onCanvasClick);

  closeDetailsBtn?.addEventListener('click', closeDetails);

  findSimilarBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    findSimilar();
  });

  loadButton?.addEventListener("click", (e) => {
    e.preventDefault();
    loadNeighborhood();
  });
});
