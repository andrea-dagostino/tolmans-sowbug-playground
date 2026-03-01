// main.js — Schematic Sowbug frontend
const canvas = document.getElementById("grid-canvas");
const ctx = canvas.getContext("2d");

const GRID_SIZE = 20;
const CELL_SIZE = canvas.width / GRID_SIZE;

const COLORS = {
    food: "#4CAF50",
    water: "#2196F3",
    light: "#FFEB3B",
    heat: "#F44336",
    obstacle: "#424242",
    agent: "#FF9800",
    background: "#FAFAFA",
    gridLine: "#E0E0E0",
    cogmapEdge: "#9C27B0",
    perceptionRadius: "#FF9800",
    visited: "#B0BEC5",
};

let ws = null;
let latestState = null;
let showCognitiveMap = true;
let showPerception = true;

function connectWebSocket() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onmessage = (event) => {
        latestState = JSON.parse(event.data);
        render(latestState);
        updateDashboard(latestState);
    };

    ws.onclose = () => {
        setTimeout(connectWebSocket, 2000);
    };
}

function send(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

// --- Overlay rendering ---

function renderCognitiveMap(state) {
    if (!state.agents || state.agents.length === 0) return;
    const agent = state.agents[0];
    if (!agent.cognitive_map_edges && !agent.cognitive_map) return;

    // Edges
    if (agent.cognitive_map_edges) {
        for (const edge of agent.cognitive_map_edges) {
            const [fx, fy] = edge.from;
            const [tx, ty] = edge.to;
            const fromCx = fx * CELL_SIZE + CELL_SIZE / 2;
            const fromCy = fy * CELL_SIZE + CELL_SIZE / 2;
            const toCx = tx * CELL_SIZE + CELL_SIZE / 2;
            const toCy = ty * CELL_SIZE + CELL_SIZE / 2;
            const width = Math.min(1 + edge.count * 0.5, 5);
            ctx.strokeStyle = COLORS.cogmapEdge;
            ctx.globalAlpha = 0.25;
            ctx.lineWidth = width;
            ctx.beginPath();
            ctx.moveTo(fromCx, fromCy);
            ctx.lineTo(toCx, toCy);
            ctx.stroke();
        }
        ctx.globalAlpha = 1.0;
    }

    // Visited cells (small gray circles, skip cells with cognitive_map entries)
    if (agent.visited_cells) {
        const cogKeys = agent.cognitive_map ? new Set(Object.keys(agent.cognitive_map)) : new Set();
        for (const [key, familiarity] of Object.entries(agent.visited_cells)) {
            if (cogKeys.has(key)) continue;
            const [gx, gy] = key.split(",").map(Number);
            const cx = gx * CELL_SIZE + CELL_SIZE / 2;
            const cy = gy * CELL_SIZE + CELL_SIZE / 2;
            const r = CELL_SIZE / 5;
            ctx.globalAlpha = Math.max(0.1, familiarity * 0.5);
            ctx.fillStyle = COLORS.visited;
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.globalAlpha = 1.0;
    }

    // Nodes (diamonds)
    if (agent.cognitive_map) {
        for (const [key, entries] of Object.entries(agent.cognitive_map)) {
            const [gx, gy] = key.split(",").map(Number);
            const cx = gx * CELL_SIZE + CELL_SIZE / 2;
            const cy = gy * CELL_SIZE + CELL_SIZE / 2;
            const halfSize = CELL_SIZE / 3;

            // Use the strongest entry's type for color, and max strength for opacity
            let maxStrength = 0;
            let dominantType = "food";
            for (const entry of entries) {
                if (entry.strength > maxStrength) {
                    maxStrength = entry.strength;
                    dominantType = entry.stimulus_type;
                }
            }

            const color = COLORS[dominantType] || "#999";
            ctx.globalAlpha = Math.max(0.15, maxStrength * 0.7);
            ctx.fillStyle = color;

            // Draw diamond
            ctx.beginPath();
            ctx.moveTo(cx, cy - halfSize);
            ctx.lineTo(cx + halfSize, cy);
            ctx.lineTo(cx, cy + halfSize);
            ctx.lineTo(cx - halfSize, cy);
            ctx.closePath();
            ctx.fill();

            // Dashed outline
            ctx.setLineDash([3, 3]);
            ctx.strokeStyle = color;
            ctx.lineWidth = 1;
            ctx.stroke();
            ctx.setLineDash([]);
        }
        ctx.globalAlpha = 1.0;
    }
}

function renderPerceptionRadius(state) {
    if (!state.agents || state.agents.length === 0) return;
    const agent = state.agents[0];
    const radius = agent.perception_radius;
    if (!radius) return;

    const [ax, ay] = agent.position;
    const cx = ax * CELL_SIZE + CELL_SIZE / 2;
    const cy = ay * CELL_SIZE + CELL_SIZE / 2;
    const pixelRadius = radius * CELL_SIZE;

    // Faint filled circle
    ctx.globalAlpha = 0.05;
    ctx.fillStyle = COLORS.perceptionRadius;
    ctx.beginPath();
    ctx.arc(cx, cy, pixelRadius, 0, Math.PI * 2);
    ctx.fill();

    // Dashed outline
    ctx.globalAlpha = 0.3;
    ctx.strokeStyle = COLORS.perceptionRadius;
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.arc(cx, cy, pixelRadius, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1.0;
}

function renderPerceptionLines(state) {
    if (!state.agents || state.agents.length === 0) return;
    const agent = state.agents[0];
    if (!agent.perceptions) return;

    const [ax, ay] = agent.position;
    const agentCx = ax * CELL_SIZE + CELL_SIZE / 2;
    const agentCy = ay * CELL_SIZE + CELL_SIZE / 2;

    for (const p of agent.perceptions) {
        const [sx, sy] = p.stimulus_position;
        const stimCx = sx * CELL_SIZE + CELL_SIZE / 2;
        const stimCy = sy * CELL_SIZE + CELL_SIZE / 2;
        const color = COLORS[p.stimulus_type] || "#999";

        ctx.globalAlpha = Math.max(0.2, p.perceived_intensity * 0.8);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(agentCx, agentCy);
        ctx.lineTo(stimCx, stimCy);
        ctx.stroke();
        ctx.setLineDash([]);
    }
    ctx.globalAlpha = 1.0;
}

// --- Main render ---

function render(state) {
    ctx.fillStyle = COLORS.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 1. Grid lines
    ctx.strokeStyle = COLORS.gridLine;
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= GRID_SIZE; i++) {
        ctx.beginPath();
        ctx.moveTo(i * CELL_SIZE, 0);
        ctx.lineTo(i * CELL_SIZE, canvas.height);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, i * CELL_SIZE);
        ctx.lineTo(canvas.width, i * CELL_SIZE);
        ctx.stroke();
    }

    // 2. Cognitive map (edges + nodes)
    if (showCognitiveMap) {
        renderCognitiveMap(state);
    }

    // 3. Perception radius
    if (showPerception) {
        renderPerceptionRadius(state);
    }

    // 4. Stimuli
    if (state.stimuli) {
        for (const stim of state.stimuli) {
            const [x, y] = stim.position;
            ctx.fillStyle = COLORS[stim.type] || "#999";
            ctx.globalAlpha = Math.max(0.3, stim.intensity);
            ctx.fillRect(x * CELL_SIZE + 1, y * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2);
            ctx.globalAlpha = 1.0;
        }
    }

    // 5. Perception lines
    if (showPerception) {
        renderPerceptionLines(state);
    }

    // 6. Agents
    if (state.agents) {
        for (const agent of state.agents) {
            const [x, y] = agent.position;
            const cx = x * CELL_SIZE + CELL_SIZE / 2;
            const cy = y * CELL_SIZE + CELL_SIZE / 2;
            const r = CELL_SIZE / 2.5;

            ctx.fillStyle = COLORS.agent;
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.fill();

            // Orientation indicator
            const orientMap = { NORTH: [0, -1], SOUTH: [0, 1], EAST: [1, 0], WEST: [-1, 0] };
            const dir = orientMap[agent.orientation] || [0, 0];
            ctx.strokeStyle = "#BF360C";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + dir[0] * r, cy + dir[1] * r);
            ctx.stroke();
        }
    }

    // Tick counter
    document.getElementById("tick-counter").textContent = `Tick: ${state.tick}`;
}

// --- Dashboard updates ---

function updatePerceptionList(agent) {
    const container = document.getElementById("perception-list");
    if (!agent.perceptions || agent.perceptions.length === 0) {
        container.innerHTML = '<p class="empty-state">No perceptions</p>';
        return;
    }

    const sorted = [...agent.perceptions].sort(
        (a, b) => b.perceived_intensity - a.perceived_intensity
    );

    container.innerHTML = sorted.map((p) => {
        const color = COLORS[p.stimulus_type] || "#999";
        const pct = (p.perceived_intensity * 100).toFixed(0);
        const dist = p.distance.toFixed(1);
        return `<div class="perception-item">
            <span class="dot" style="background:${color}"></span>
            <span class="type-label">${p.stimulus_type}</span>
            <span class="intensity">${pct}%</span>
            <span class="distance">${dist}</span>
        </div>`;
    }).join("");
}

function updateMemorySummary(agent) {
    const cogMap = agent.cognitive_map || {};
    const edges = agent.cognitive_map_edges || [];

    const locationCount = Object.keys(cogMap).length;
    const edgeCount = edges.length;

    let totalStrength = 0;
    let entryCount = 0;
    for (const entries of Object.values(cogMap)) {
        for (const entry of entries) {
            totalStrength += entry.strength;
            entryCount++;
        }
    }
    const avgStrength = entryCount > 0 ? totalStrength / entryCount : 0;

    const visitedCells = agent.visited_cells || {};
    const visitedCount = Object.keys(visitedCells).length;

    document.getElementById("mem-locations").textContent = locationCount;
    document.getElementById("mem-edges").textContent = edgeCount;
    document.getElementById("mem-visited").textContent = visitedCount;
    document.getElementById("mem-strength").textContent = avgStrength.toFixed(2);
}

function updateDashboard(state) {
    if (!state.agents || state.agents.length === 0) return;
    const agent = state.agents[0];
    const drives = agent.drive_levels || {};

    for (const [name, key] of [["hunger", "hunger"], ["thirst", "thirst"], ["temperature", "temperature"]]) {
        let val = 0;
        for (const [k, v] of Object.entries(drives)) {
            if (k.toLowerCase().includes(name)) {
                val = v;
                break;
            }
        }
        const bar = document.getElementById(`bar-${name}`);
        const valEl = document.getElementById(`val-${name}`);
        if (bar) bar.style.width = `${val * 100}%`;
        if (valEl) valEl.textContent = val.toFixed(2);
    }

    document.getElementById("agent-pos").textContent =
        `(${agent.position[0]}, ${agent.position[1]})`;
    document.getElementById("agent-orient").textContent = agent.orientation;

    updatePerceptionList(agent);
    updateMemorySummary(agent);
}

// --- Controls ---
document.getElementById("btn-play").onclick = () => send({ action: "play" });
document.getElementById("btn-pause").onclick = () => send({ action: "pause" });
document.getElementById("btn-step").onclick = () => send({ action: "step" });
document.getElementById("btn-reset").onclick = () => send({ action: "reset" });

const speedSlider = document.getElementById("speed-slider");
const speedVal = document.getElementById("speed-val");
speedSlider.oninput = () => {
    speedVal.textContent = speedSlider.value;
    send({ action: "speed", value: parseInt(speedSlider.value) });
};

// Overlay toggles
document.getElementById("toggle-cogmap").onchange = (e) => {
    showCognitiveMap = e.target.checked;
    if (latestState) render(latestState);
};
document.getElementById("toggle-perception").onchange = (e) => {
    showPerception = e.target.checked;
    if (latestState) render(latestState);
};

// Click to place stimulus
canvas.onclick = (e) => {
    const rect = canvas.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / CELL_SIZE);
    const y = Math.floor((e.clientY - rect.top) / CELL_SIZE);
    const stimType = document.getElementById("stim-type").value;
    send({
        action: "add_stimulus",
        stimulus_type: stimType,
        position: [x, y],
        intensity: 1.0,
        radius: 5.0,
    });
};

// Start
connectWebSocket();
