import * as THREE from "three";

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
let debugModeSelect: HTMLSelectElement | null;

let scene: THREE.Scene | null = null;
let camera: THREE.PerspectiveCamera | null = null;
let renderer: THREE.WebGLRenderer | null = null;
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
  requestAnimationFrame(animate);
  if (renderer && scene && camera) {
    renderer.render(scene, camera);
  }
}

type NeighborhoodNode = { id: number; label: string; kind?: string | null };
type NeighborhoodEdge = { src_id: number; dst_id: number; predicate: string };
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
    nodeGroup.add(mesh);
  }

  // Collapse multi-edges by (src_id, dst_id) for rendering clarity.
  const edgeGroups = new Map<string, { src_id: number; dst_id: number; count: number }>();
  for (const e of edges) {
    const key = `${e.src_id}|${e.dst_id}`;
    const existing = edgeGroups.get(key);
    if (existing) {
      existing.count += 1;
    } else {
      edgeGroups.set(key, { src_id: e.src_id, dst_id: e.dst_id, count: 1 });
    }
  }

  const edgeMat = new THREE.LineBasicMaterial({ color: 0x4b5563, linewidth: 1 });
  for (const group of edgeGroups.values()) {
    const srcPos = positions.get(group.src_id);
    const dstPos = positions.get(group.dst_id);
    if (!srcPos || !dstPos) continue;
    const geom = new THREE.BufferGeometry().setFromPoints([srcPos, dstPos]);
    const line = new THREE.Line(geom, edgeMat);
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

  initScene();

  loadButton?.addEventListener("click", (e) => {
    e.preventDefault();
    loadNeighborhood();
  });
});
