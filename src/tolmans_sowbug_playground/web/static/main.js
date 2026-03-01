// main.js — Schematic Sowbug frontend
const canvas = document.getElementById("grid-canvas");
const ctx = canvas.getContext("2d");

const MAX_CANVAS_PX = 600;
let gridWidth = 20;
let gridHeight = 20;
let cellSize = MAX_CANVAS_PX / 20;

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
let resourceHistory = [];
let lastRecordedTick = -1;
let driveHistory = [];
let positionHistory = [];
let showCognitiveMap = true;
let showPerception = true;
let showDensityField = true;
let showVTE = true;
let showLegend = true;
let driveChartHoverX = null;
let resourceChartHoverX = null;
let eventLog = [];
let _lastDrives = { hunger: 0, thirst: 0, temperature: 0 };
let _firstDeliberation = false;
let hoveredStimulus = null;
let hoverPixel = { x: 0, y: 0 };

function updateCanvasSize(w, h) {
    gridWidth = w;
    gridHeight = h;
    cellSize = Math.floor(Math.min(MAX_CANVAS_PX / gridWidth, MAX_CANVAS_PX / gridHeight));
    canvas.width = cellSize * gridWidth;
    canvas.height = cellSize * gridHeight;
}

function connectWebSocket() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        // Handle preset_saved response
        if (msg.preset_saved) {
            const sel = document.getElementById("preset-select");
            // Rebuild options: Custom + all presets from server
            const presets = msg.presets || [];
            sel.innerHTML = '<option value="">Custom</option>' +
                presets.map(p => `<option value="${p}">${p}</option>`).join("");
            sel.value = msg.preset_saved;
            return;
        }

        latestState = msg;
        if (latestState.grid_width && latestState.grid_height) {
            if (latestState.grid_width !== gridWidth || latestState.grid_height !== gridHeight) {
                updateCanvasSize(latestState.grid_width, latestState.grid_height);
                document.getElementById("grid-width").value = gridWidth;
                document.getElementById("grid-height").value = gridHeight;
            }
        }

        // Track resource gathering history
        const tick = latestState.tick || 0;
        if (tick <= lastRecordedTick) {
            resourceHistory = [];
            driveHistory = [];
            positionHistory = [];
            eventLog = [];
            _lastDrives = { hunger: 0, thirst: 0, temperature: 0 };
            _firstDeliberation = false;
        }
        lastRecordedTick = tick;
        if (latestState.agents && latestState.agents.length > 0) {
            const agent = latestState.agents[0];
            const consumptions = agent.resource_consumptions != null ? agent.resource_consumptions : 0;
            resourceHistory.push({ tick, consumptions });

            // Track drive levels
            const drives = agent.drive_levels || {};
            const entry = { tick, hunger: 0, thirst: 0, temperature: 0 };
            for (const [k, v] of Object.entries(drives)) {
                const kl = k.toLowerCase();
                if (kl.includes("hunger")) entry.hunger = v;
                else if (kl.includes("thirst")) entry.thirst = v;
                else if (kl.includes("temperature")) entry.temperature = v;
            }
            driveHistory.push(entry);

            // Track position for trajectory chart
            const [px, py] = agent.position;
            positionHistory.push({ tick, x: px, y: py });

            // Detect events for chart annotations
            if (driveHistory.length > 1) {
                const prev = _lastDrives;
                const DROP_THRESHOLD = 0.15;
                if (prev.hunger - entry.hunger > DROP_THRESHOLD) {
                    const exists = eventLog.some(e => e.label === "Food found" && Math.abs(e.tick - tick) < 3);
                    if (!exists) eventLog.push({ tick, label: "Food found" });
                }
                if (prev.thirst - entry.thirst > DROP_THRESHOLD) {
                    const exists = eventLog.some(e => e.label === "Water found" && Math.abs(e.tick - tick) < 3);
                    if (!exists) eventLog.push({ tick, label: "Water found" });
                }
                if (prev.temperature - entry.temperature > DROP_THRESHOLD) {
                    const exists = eventLog.some(e => e.label === "Heat found" && Math.abs(e.tick - tick) < 3);
                    if (!exists) eventLog.push({ tick, label: "Heat found" });
                }
            }
            _lastDrives = { hunger: entry.hunger, thirst: entry.thirst, temperature: entry.temperature };

            if (!_firstDeliberation && agent.vte && agent.vte.is_deliberating) {
                _firstDeliberation = true;
                eventLog.push({ tick, label: "First VTE" });
            }
        }
        renderChart();
        renderDriveChart();
        renderTrajectoryChart();

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

function densityColor(value) {
    const r = Math.round(128 + 127 * value);
    const g = Math.round(200 * value * value);
    const b = Math.round(180 * (1 - value));
    return `rgb(${r},${g},${b})`;
}

function renderDensityField(state) {
    if (!state.agents || state.agents.length === 0) return;
    const agent = state.agents[0];
    if (!agent.density_field) return;

    for (const [key, density] of Object.entries(agent.density_field)) {
        const [gx, gy] = key.split(",").map(Number);
        ctx.globalAlpha = Math.min(density * 0.45, 0.45);
        ctx.fillStyle = densityColor(density);
        ctx.fillRect(gx * cellSize, gy * cellSize, cellSize, cellSize);
    }
    ctx.globalAlpha = 1.0;
}

function renderCognitiveMap(state) {
    if (!state.agents || state.agents.length === 0) return;
    const agent = state.agents[0];
    if (!agent.cognitive_map_edges && !agent.cognitive_map) return;

    // Edges
    if (agent.cognitive_map_edges) {
        for (const edge of agent.cognitive_map_edges) {
            const [fx, fy] = edge.from;
            const [tx, ty] = edge.to;
            const fromCx = fx * cellSize + cellSize / 2;
            const fromCy = fy * cellSize + cellSize / 2;
            const toCx = tx * cellSize + cellSize / 2;
            const toCy = ty * cellSize + cellSize / 2;
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
            const cx = gx * cellSize + cellSize / 2;
            const cy = gy * cellSize + cellSize / 2;
            const r = cellSize / 5;
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
            const cx = gx * cellSize + cellSize / 2;
            const cy = gy * cellSize + cellSize / 2;
            const halfSize = cellSize / 3;

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

            ctx.beginPath();
            ctx.moveTo(cx, cy - halfSize);
            ctx.lineTo(cx + halfSize, cy);
            ctx.lineTo(cx, cy + halfSize);
            ctx.lineTo(cx - halfSize, cy);
            ctx.closePath();
            ctx.fill();

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
    const cx = ax * cellSize + cellSize / 2;
    const cy = ay * cellSize + cellSize / 2;
    const pixelRadius = radius * cellSize;

    ctx.globalAlpha = 0.05;
    ctx.fillStyle = COLORS.perceptionRadius;
    ctx.beginPath();
    ctx.arc(cx, cy, pixelRadius, 0, Math.PI * 2);
    ctx.fill();

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
    const agentCx = ax * cellSize + cellSize / 2;
    const agentCy = ay * cellSize + cellSize / 2;

    for (const p of agent.perceptions) {
        const [sx, sy] = p.stimulus_position;
        const stimCx = sx * cellSize + cellSize / 2;
        const stimCy = sy * cellSize + cellSize / 2;
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

function renderVTE(state) {
    if (!state.agents || state.agents.length === 0) return;
    const agent = state.agents[0];
    const vte = agent.vte;
    if (!vte || !vte.candidates || vte.candidates.length === 0) return;

    const [ax, ay] = agent.position;
    const cx = ax * cellSize + cellSize / 2;
    const cy = ay * cellSize + cellSize / 2;

    const maxVal = Math.max(...vte.candidates.map(c => c.value), 0.001);

    const dirDeltas = { NORTH: [0, -1], SOUTH: [0, 1], EAST: [1, 0], WEST: [-1, 0] };
    for (const candidate of vte.candidates) {
        const delta = dirDeltas[candidate.direction];
        if (!delta || candidate.value <= 0) continue;

        const norm = candidate.value / maxVal;
        const arrowLen = cellSize * (0.4 + norm * 0.6);
        const endX = cx + delta[0] * arrowLen;
        const endY = cy + delta[1] * arrowLen;

        ctx.globalAlpha = 0.3 + norm * 0.5;
        ctx.strokeStyle = vte.is_deliberating ? "#E040FB" : "#7C4DFF";
        ctx.lineWidth = 1.5 + norm * 2.5;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(endX, endY);
        ctx.stroke();

        const headLen = 4 + norm * 4;
        const angle = Math.atan2(delta[1], delta[0]);
        ctx.beginPath();
        ctx.moveTo(endX, endY);
        ctx.lineTo(
            endX - headLen * Math.cos(angle - Math.PI / 6),
            endY - headLen * Math.sin(angle - Math.PI / 6)
        );
        ctx.moveTo(endX, endY);
        ctx.lineTo(
            endX - headLen * Math.cos(angle + Math.PI / 6),
            endY - headLen * Math.sin(angle + Math.PI / 6)
        );
        ctx.stroke();
    }
    ctx.globalAlpha = 1.0;

    if (vte.hesitated) {
        const pulse = 0.4 + 0.3 * Math.sin(Date.now() / 150);
        ctx.globalAlpha = pulse;
        ctx.strokeStyle = "#E040FB";
        ctx.lineWidth = 2;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.arc(cx, cy, cellSize / 2 + 3, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1.0;
    }
}

// --- Resource gathering chart ---

function renderChart() {
    const chartCanvas = document.getElementById("coverage-chart-canvas");
    if (!chartCanvas) return;
    const cCtx = chartCanvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const rect = chartCanvas.getBoundingClientRect();
    chartCanvas.width = rect.width * dpr;
    chartCanvas.height = rect.height * dpr;
    cCtx.scale(dpr, dpr);
    const W = rect.width;
    const H = rect.height;

    cCtx.fillStyle = "#fff";
    cCtx.fillRect(0, 0, W, H);

    const pad = { top: 8, right: 40, bottom: 20, left: 36 };
    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    if (resourceHistory.length < 2) {
        // Y-axis label
        cCtx.save();
        cCtx.fillStyle = "#888";
        cCtx.font = "9px sans-serif";
        cCtx.textAlign = "center";
        cCtx.textBaseline = "top";
        cCtx.translate(8, pad.top + plotH / 2);
        cCtx.rotate(-Math.PI / 2);
        cCtx.fillText("Consumptions", 0, 0);
        cCtx.restore();

        // X-axis label
        cCtx.textAlign = "center";
        cCtx.textBaseline = "top";
        cCtx.fillStyle = "#aaa";
        cCtx.font = "9px monospace";
        cCtx.fillText("tick", pad.left + plotW / 2, H - 10);

        // Axis frame only
        cCtx.strokeStyle = "#ccc";
        cCtx.lineWidth = 1;
        cCtx.beginPath();
        cCtx.moveTo(pad.left, pad.top);
        cCtx.lineTo(pad.left, pad.top + plotH);
        cCtx.lineTo(pad.left + plotW, pad.top + plotH);
        cCtx.stroke();
        return;
    }

    const minTick = resourceHistory[0].tick;
    const maxTick = resourceHistory[resourceHistory.length - 1].tick;
    const tickRange = maxTick - minTick || 1;

    // Compute max cumulative value for Y scale
    const maxCumulative = resourceHistory[resourceHistory.length - 1].consumptions;
    const yMax = Math.max(1, maxCumulative);

    // Compute rolling rate (consumptions per window of 20 ticks)
    const WINDOW = 20;
    const rollingRate = [];
    for (let i = 0; i < resourceHistory.length; i++) {
        const current = resourceHistory[i].consumptions;
        // Find the entry ~WINDOW ticks ago
        let pastIdx = i;
        while (pastIdx > 0 && resourceHistory[i].tick - resourceHistory[pastIdx].tick < WINDOW) {
            pastIdx--;
        }
        const past = resourceHistory[pastIdx].consumptions;
        const dt = resourceHistory[i].tick - resourceHistory[pastIdx].tick;
        rollingRate.push(dt > 0 ? (current - past) / dt * WINDOW : 0);
    }
    const maxRate = Math.max(1, ...rollingRate);

    // Grid lines & Y-axis labels (left axis — cumulative)
    cCtx.strokeStyle = "#eee";
    cCtx.lineWidth = 1;
    cCtx.fillStyle = "#aaa";
    cCtx.font = "9px monospace";
    cCtx.textAlign = "right";
    cCtx.textBaseline = "middle";
    const ySteps = 4;
    for (let i = 0; i <= ySteps; i++) {
        const frac = i / ySteps;
        const y = pad.top + plotH - frac * plotH;
        cCtx.beginPath();
        cCtx.moveTo(pad.left, y);
        cCtx.lineTo(pad.left + plotW, y);
        cCtx.stroke();
        cCtx.fillStyle = "#00897B";
        cCtx.fillText(Math.round(frac * yMax), pad.left - 4, y);
    }

    // Right Y-axis labels (rolling rate)
    cCtx.textAlign = "left";
    for (let i = 0; i <= ySteps; i++) {
        const frac = i / ySteps;
        const y = pad.top + plotH - frac * plotH;
        cCtx.fillStyle = "#FF9800";
        cCtx.fillText((frac * maxRate).toFixed(1), pad.left + plotW + 4, y);
    }

    // Rotated Y-axis label (left)
    cCtx.save();
    cCtx.fillStyle = "#00897B";
    cCtx.font = "9px sans-serif";
    cCtx.textAlign = "center";
    cCtx.textBaseline = "top";
    cCtx.translate(8, pad.top + plotH / 2);
    cCtx.rotate(-Math.PI / 2);
    cCtx.fillText("Consumptions", 0, 0);
    cCtx.restore();

    // Rotated Y-axis label (right)
    cCtx.save();
    cCtx.fillStyle = "#FF9800";
    cCtx.font = "9px sans-serif";
    cCtx.textAlign = "center";
    cCtx.textBaseline = "bottom";
    cCtx.translate(W - 4, pad.top + plotH / 2);
    cCtx.rotate(-Math.PI / 2);
    cCtx.fillText("Rate / 20t", 0, 0);
    cCtx.restore();

    // X-axis label
    cCtx.textAlign = "center";
    cCtx.textBaseline = "top";
    cCtx.fillStyle = "#aaa";
    cCtx.font = "9px monospace";
    cCtx.fillText("tick", pad.left + plotW / 2, H - 10);

    // X-axis tick labels
    cCtx.fillStyle = "#aaa";
    cCtx.textBaseline = "top";
    cCtx.textAlign = "center";
    const tickStep = Math.max(1, Math.ceil(tickRange / 5));
    for (let t = minTick; t <= maxTick; t += tickStep) {
        const x = pad.left + ((t - minTick) / tickRange) * plotW;
        cCtx.fillText(t, x, pad.top + plotH + 3);
    }

    // Axis frame
    cCtx.strokeStyle = "#ccc";
    cCtx.lineWidth = 1;
    cCtx.beginPath();
    cCtx.moveTo(pad.left, pad.top);
    cCtx.lineTo(pad.left, pad.top + plotH);
    cCtx.lineTo(pad.left + plotW, pad.top + plotH);
    cCtx.lineTo(pad.left + plotW, pad.top);
    cCtx.stroke();

    // Rolling rate line (faded, behind)
    cCtx.strokeStyle = "rgba(255, 152, 0, 0.5)";
    cCtx.lineWidth = 1.5;
    cCtx.beginPath();
    for (let i = 0; i < resourceHistory.length; i++) {
        const d = resourceHistory[i];
        const x = pad.left + ((d.tick - minTick) / tickRange) * plotW;
        const y = pad.top + plotH - (rollingRate[i] / maxRate) * plotH;
        if (i === 0) cCtx.moveTo(x, y);
        else cCtx.lineTo(x, y);
    }
    cCtx.stroke();

    // Cumulative line (solid, on top)
    cCtx.strokeStyle = "#00897B";
    cCtx.lineWidth = 2;
    cCtx.beginPath();
    for (let i = 0; i < resourceHistory.length; i++) {
        const d = resourceHistory[i];
        const x = pad.left + ((d.tick - minTick) / tickRange) * plotW;
        const y = pad.top + plotH - (d.consumptions / yMax) * plotH;
        if (i === 0) cCtx.moveTo(x, y);
        else cCtx.lineTo(x, y);
    }
    cCtx.stroke();

    // Fill under cumulative line
    const last = resourceHistory[resourceHistory.length - 1];
    const lastX = pad.left + ((last.tick - minTick) / tickRange) * plotW;
    cCtx.lineTo(lastX, pad.top + plotH);
    cCtx.lineTo(pad.left, pad.top + plotH);
    cCtx.closePath();
    cCtx.fillStyle = "rgba(0, 137, 123, 0.08)";
    cCtx.fill();

    // Event annotations
    for (const evt of eventLog) {
        const ex = pad.left + ((evt.tick - minTick) / tickRange) * plotW;
        if (ex < pad.left || ex > pad.left + plotW) continue;
        cCtx.strokeStyle = "rgba(0,0,0,0.15)";
        cCtx.lineWidth = 1;
        cCtx.setLineDash([3, 3]);
        cCtx.beginPath();
        cCtx.moveTo(ex, pad.top);
        cCtx.lineTo(ex, pad.top + plotH);
        cCtx.stroke();
        cCtx.setLineDash([]);
    }

    // Hover crosshair and tooltip
    if (resourceChartHoverX !== null) {
        const hx = resourceChartHoverX;
        if (hx >= pad.left && hx <= pad.left + plotW) {
            cCtx.strokeStyle = "rgba(0,0,0,0.3)";
            cCtx.lineWidth = 1;
            cCtx.setLineDash([2, 2]);
            cCtx.beginPath();
            cCtx.moveTo(hx, pad.top);
            cCtx.lineTo(hx, pad.top + plotH);
            cCtx.stroke();
            cCtx.setLineDash([]);

            const hoverTick = minTick + ((hx - pad.left) / plotW) * tickRange;
            let closest = resourceHistory[0];
            let closestIdx = 0;
            let minDist = Infinity;
            for (let i = 0; i < resourceHistory.length; i++) {
                const dist = Math.abs(resourceHistory[i].tick - hoverTick);
                if (dist < minDist) { minDist = dist; closest = resourceHistory[i]; closestIdx = i; }
            }

            const tooltipW = 120;
            const tooltipH = 40;
            let tx = hx + 8;
            if (tx + tooltipW > pad.left + plotW) tx = hx - tooltipW - 8;
            let ty = pad.top + 4;

            cCtx.fillStyle = "rgba(255,255,255,0.92)";
            cCtx.strokeStyle = "#ccc";
            cCtx.lineWidth = 1;
            cCtx.beginPath();
            cCtx.roundRect(tx, ty, tooltipW, tooltipH, 3);
            cCtx.fill();
            cCtx.stroke();

            cCtx.font = "9px monospace";
            cCtx.textAlign = "left";
            cCtx.textBaseline = "top";
            cCtx.fillStyle = "#333";
            cCtx.fillText(`Tick: ${closest.tick}`, tx + 4, ty + 4);
            cCtx.fillStyle = "#00897B";
            cCtx.fillText(`Total: ${closest.consumptions}`, tx + 4, ty + 16);
            cCtx.fillStyle = "#FF9800";
            cCtx.fillText(`Rate: ${rollingRate[closestIdx].toFixed(1)}/20t`, tx + 4, ty + 28);
        }
    }
}

// --- Drive monitoring chart ---

function renderDriveChart() {
    const chartCanvas = document.getElementById("drive-chart-canvas");
    if (!chartCanvas) return;
    const cCtx = chartCanvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const rect = chartCanvas.getBoundingClientRect();
    chartCanvas.width = rect.width * dpr;
    chartCanvas.height = rect.height * dpr;
    cCtx.scale(dpr, dpr);
    const W = rect.width;
    const H = rect.height;

    cCtx.fillStyle = "#fff";
    cCtx.fillRect(0, 0, W, H);

    const pad = { top: 10, right: 12, bottom: 22, left: 32 };
    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    // Y-axis grid & labels (0.0 – 1.0)
    cCtx.strokeStyle = "#eee";
    cCtx.lineWidth = 1;
    cCtx.fillStyle = "#aaa";
    cCtx.font = "9px monospace";
    cCtx.textAlign = "right";
    cCtx.textBaseline = "middle";
    for (let v = 0; v <= 1.0; v += 0.25) {
        const y = pad.top + plotH - v * plotH;
        cCtx.beginPath();
        cCtx.moveTo(pad.left, y);
        cCtx.lineTo(pad.left + plotW, y);
        cCtx.stroke();
        cCtx.fillText(v.toFixed(2), pad.left - 4, y);
    }

    // X-axis label
    cCtx.textAlign = "center";
    cCtx.textBaseline = "top";
    cCtx.fillText("tick", pad.left + plotW / 2, H - 10);

    // Axis frame
    cCtx.strokeStyle = "#ccc";
    cCtx.lineWidth = 1;
    cCtx.beginPath();
    cCtx.moveTo(pad.left, pad.top);
    cCtx.lineTo(pad.left, pad.top + plotH);
    cCtx.lineTo(pad.left + plotW, pad.top + plotH);
    cCtx.stroke();

    if (driveHistory.length < 2) return;

    const minTick = driveHistory[0].tick;
    const maxTick = driveHistory[driveHistory.length - 1].tick;
    const tickRange = maxTick - minTick || 1;

    // X-axis tick labels
    cCtx.fillStyle = "#aaa";
    cCtx.textBaseline = "top";
    cCtx.textAlign = "center";
    const tickStep = Math.max(1, Math.ceil(tickRange / 5));
    for (let t = minTick; t <= maxTick; t += tickStep) {
        const x = pad.left + ((t - minTick) / tickRange) * plotW;
        cCtx.fillText(t, x, pad.top + plotH + 3);
    }

    // Draw a line series
    const series = [
        { key: "hunger",      color: "#4CAF50", label: "Hunger",      dash: [] },
        { key: "thirst",      color: "#2196F3", label: "Thirst",      dash: [6, 3] },
        { key: "temperature", color: "#F44336", label: "Temperature", dash: [2, 2] },
    ];

    for (const s of series) {
        cCtx.strokeStyle = s.color;
        cCtx.lineWidth = 2;
        cCtx.setLineDash(s.dash);
        cCtx.beginPath();
        for (let i = 0; i < driveHistory.length; i++) {
            const d = driveHistory[i];
            const x = pad.left + ((d.tick - minTick) / tickRange) * plotW;
            const y = pad.top + plotH - Math.min(d[s.key], 1.0) * plotH;
            if (i === 0) cCtx.moveTo(x, y);
            else cCtx.lineTo(x, y);
        }
        cCtx.stroke();
        cCtx.setLineDash([]);
    }

    // Legend
    const legendY = pad.top + 2;
    let legendX = pad.left + 4;
    cCtx.font = "10px sans-serif";
    cCtx.textAlign = "left";
    cCtx.textBaseline = "top";
    for (const s of series) {
        cCtx.strokeStyle = s.color;
        cCtx.lineWidth = 2;
        cCtx.setLineDash(s.dash);
        cCtx.beginPath();
        cCtx.moveTo(legendX, legendY + 2);
        cCtx.lineTo(legendX + 14, legendY + 2);
        cCtx.stroke();
        cCtx.setLineDash([]);
        cCtx.fillStyle = "#555";
        cCtx.fillText(s.label, legendX + 17, legendY - 1);
        legendX += cCtx.measureText(s.label).width + 26;
    }

    // Event annotations
    for (const evt of eventLog) {
        const ex = pad.left + ((evt.tick - minTick) / tickRange) * plotW;
        if (ex < pad.left || ex > pad.left + plotW) continue;
        cCtx.strokeStyle = "rgba(0,0,0,0.2)";
        cCtx.lineWidth = 1;
        cCtx.setLineDash([3, 3]);
        cCtx.beginPath();
        cCtx.moveTo(ex, pad.top);
        cCtx.lineTo(ex, pad.top + plotH);
        cCtx.stroke();
        cCtx.setLineDash([]);
        cCtx.save();
        cCtx.fillStyle = "#888";
        cCtx.font = "8px sans-serif";
        cCtx.textAlign = "left";
        cCtx.translate(ex + 2, pad.top + 2);
        cCtx.rotate(-Math.PI / 4);
        cCtx.fillText(evt.label, 0, 0);
        cCtx.restore();
    }

    // Hover crosshair and tooltip
    if (driveChartHoverX !== null) {
        const hx = driveChartHoverX;
        if (hx >= pad.left && hx <= pad.left + plotW) {
            cCtx.strokeStyle = "rgba(0,0,0,0.3)";
            cCtx.lineWidth = 1;
            cCtx.setLineDash([2, 2]);
            cCtx.beginPath();
            cCtx.moveTo(hx, pad.top);
            cCtx.lineTo(hx, pad.top + plotH);
            cCtx.stroke();
            cCtx.setLineDash([]);

            const hoverTick = minTick + ((hx - pad.left) / plotW) * tickRange;
            let closest = driveHistory[0];
            let minDist = Infinity;
            for (const d of driveHistory) {
                const dist = Math.abs(d.tick - hoverTick);
                if (dist < minDist) { minDist = dist; closest = d; }
            }

            const tooltipW = 110;
            const tooltipH = 48;
            let tx = hx + 8;
            if (tx + tooltipW > pad.left + plotW) tx = hx - tooltipW - 8;
            let ty = pad.top + 4;

            cCtx.fillStyle = "rgba(255,255,255,0.92)";
            cCtx.strokeStyle = "#ccc";
            cCtx.lineWidth = 1;
            cCtx.beginPath();
            cCtx.roundRect(tx, ty, tooltipW, tooltipH, 3);
            cCtx.fill();
            cCtx.stroke();

            cCtx.font = "9px monospace";
            cCtx.textAlign = "left";
            cCtx.textBaseline = "top";
            cCtx.fillStyle = "#333";
            cCtx.fillText(`Tick: ${closest.tick}`, tx + 4, ty + 4);
            cCtx.fillStyle = "#4CAF50";
            cCtx.fillText(`H: ${closest.hunger.toFixed(2)}`, tx + 4, ty + 16);
            cCtx.fillStyle = "#2196F3";
            cCtx.fillText(`T: ${closest.thirst.toFixed(2)}`, tx + 4, ty + 28);
            cCtx.fillStyle = "#F44336";
            cCtx.fillText(`Tp: ${closest.temperature.toFixed(2)}`, tx + 4, ty + 38);
        }
    }
}

function renderTrajectoryChart() {
    const cv = document.getElementById("trajectory-canvas");
    if (!cv) return;
    const c = cv.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const cssW = cv.clientWidth;
    const cssH = cv.clientHeight;
    cv.width = cssW * dpr;
    cv.height = cssH * dpr;
    c.scale(dpr, dpr);

    const pad = { top: 16, right: 16, bottom: 24, left: 30 };
    const plotW = cssW - pad.left - pad.right;
    const plotH = cssH - pad.top - pad.bottom;

    // Background
    c.fillStyle = "#fff";
    c.fillRect(0, 0, cssW, cssH);

    if (positionHistory.length < 1) {
        c.fillStyle = "#bbb";
        c.font = "11px sans-serif";
        c.textAlign = "center";
        c.textBaseline = "middle";
        c.fillText("No trajectory data", cssW / 2, cssH / 2);
        return;
    }

    // Use the full grid as the spatial extent (not just visited cells)
    const extMinX = -0.5;
    const extMaxX = gridWidth - 0.5;
    const extMinY = -0.5;
    const extMaxY = gridHeight - 0.5;
    const extW = extMaxX - extMinX;
    const extH = extMaxY - extMinY;

    // Square aspect ratio
    const scaleXY = Math.min(plotW / extW, plotH / extH);
    const drawW = extW * scaleXY;
    const drawH = extH * scaleXY;
    const ox = pad.left + (plotW - drawW) / 2;
    const oy = pad.top + (plotH - drawH) / 2;

    // KDE on a pixel-resolution grid (sample every ~3px for speed)
    const SAMPLE = 3;
    const cols = Math.max(4, Math.floor(drawW / SAMPLE));
    const rows = Math.max(4, Math.floor(drawH / SAMPLE));
    const cellW = drawW / cols;
    const cellH = drawH / rows;

    // Bandwidth in grid-cell units — adaptive to grid size
    const bw = Math.max(1.0, Math.min(gridWidth, gridHeight) * 0.08);
    const bwPx = bw * scaleXY;
    const bw2 = 2 * bwPx * bwPx;
    // Precompute cutoff radius in sample cells
    const cutoffPx = bwPx * 3;
    const cutoffCells = Math.ceil(cutoffPx / Math.min(cellW, cellH));

    // Build density grid
    const density = new Float32Array(cols * rows);

    // Convert positions to screen coords once
    const pts = new Float32Array(positionHistory.length * 2);
    for (let i = 0; i < positionHistory.length; i++) {
        const p = positionHistory[i];
        pts[i * 2]     = ox + (p.x - extMinX) / extW * drawW;
        pts[i * 2 + 1] = oy + (p.y - extMinY) / extH * drawH;
    }

    // Accumulate Gaussian kernel contributions
    for (let pi = 0; pi < positionHistory.length; pi++) {
        const px = pts[pi * 2];
        const py = pts[pi * 2 + 1];
        // Determine affected sample cells
        const ci = Math.round((px - ox) / cellW);
        const ri = Math.round((py - oy) / cellH);
        const r0 = Math.max(0, ri - cutoffCells);
        const r1 = Math.min(rows - 1, ri + cutoffCells);
        const c0 = Math.max(0, ci - cutoffCells);
        const c1 = Math.min(cols - 1, ci + cutoffCells);
        for (let r = r0; r <= r1; r++) {
            const sy = oy + (r + 0.5) * cellH;
            const dy = sy - py;
            const dy2 = dy * dy;
            for (let col = c0; col <= c1; col++) {
                const sx = ox + (col + 0.5) * cellW;
                const dx = sx - px;
                const dist2 = dx * dx + dy2;
                if (dist2 < cutoffPx * cutoffPx) {
                    density[r * cols + col] += Math.exp(-dist2 / bw2);
                }
            }
        }
    }

    // Find peak for normalization
    let peak = 0;
    for (let i = 0; i < density.length; i++) {
        if (density[i] > peak) peak = density[i];
    }

    // Draw KDE heatmap (warm orange palette, transparent where empty)
    if (peak > 0) {
        for (let r = 0; r < rows; r++) {
            for (let col = 0; col < cols; col++) {
                const v = density[r * cols + col] / peak;
                if (v < 0.01) continue;
                // Cool-to-warm: transparent → blue-ish → orange → bright yellow
                let cr, cg, cb;
                if (v < 0.33) {
                    const t = v / 0.33;
                    cr = Math.round(30 + 50 * t);
                    cg = Math.round(60 + 80 * t);
                    cb = Math.round(120 + 80 * t);
                } else if (v < 0.66) {
                    const t = (v - 0.33) / 0.33;
                    cr = Math.round(80 + 175 * t);
                    cg = Math.round(140 + 12 * t);
                    cb = Math.round(200 - 200 * t);
                } else {
                    const t = (v - 0.66) / 0.34;
                    cr = 255;
                    cg = Math.round(152 + 103 * t);
                    cb = Math.round(0 + 50 * t);
                }
                c.globalAlpha = Math.min(1, 0.15 + 0.75 * v);
                c.fillStyle = `rgb(${cr},${cg},${cb})`;
                c.fillRect(ox + col * cellW, oy + r * cellH, cellW + 0.5, cellH + 0.5);
            }
        }
        c.globalAlpha = 1.0;
    }

    // Cardinal labels
    c.font = "bold 9px sans-serif";
    c.fillStyle = "#999";
    c.textAlign = "center";
    c.textBaseline = "bottom";
    c.fillText("N", ox + drawW / 2, oy - 3);
    c.textBaseline = "top";
    c.fillText("S", ox + drawW / 2, oy + drawH + 3);
    c.textAlign = "right";
    c.textBaseline = "middle";
    c.fillText("W", ox - 5, oy + drawH / 2);
    c.textAlign = "left";
    c.fillText("E", ox + drawW + 5, oy + drawH / 2);

    // Border
    c.strokeStyle = "#ddd";
    c.lineWidth = 0.5;
    c.strokeRect(ox, oy, drawW, drawH);

    // Start marker (green ring)
    const p0 = positionHistory[0];
    const s0x = ox + (p0.x - extMinX) / extW * drawW;
    const s0y = oy + (p0.y - extMinY) / extH * drawH;
    c.strokeStyle = "#4CAF50";
    c.lineWidth = 1.5;
    c.beginPath();
    c.arc(s0x, s0y, 4, 0, Math.PI * 2);
    c.stroke();

    // Current position marker (orange dot)
    const pN = positionHistory[positionHistory.length - 1];
    const sNx = ox + (pN.x - extMinX) / extW * drawW;
    const sNy = oy + (pN.y - extMinY) / extH * drawH;
    c.fillStyle = COLORS.agent;
    c.beginPath();
    c.arc(sNx, sNy, 3.5, 0, Math.PI * 2);
    c.fill();
}

function renderLegend() {
    if (!showLegend) return;
    const items = [
        { label: "Food", color: COLORS.food, icon: "\u{1F33F}" },
        { label: "Water", color: COLORS.water, icon: "\u{1F4A7}" },
        { label: "Light", color: COLORS.light, icon: "\u2600" },
        { label: "Heat", color: COLORS.heat, icon: "\u{1F525}" },
        { label: "Obstacle", color: COLORS.obstacle, icon: "\u25A0" },
        { label: "Agent", color: COLORS.agent, icon: null },
    ];
    const lineH = 16;
    const legendW = 78;
    const legendH = items.length * lineH + 8;
    const lx = canvas.width - legendW - 6;
    const ly = 6;

    ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
    ctx.strokeStyle = "#ccc";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(lx, ly, legendW, legendH, 4);
    ctx.fill();
    ctx.stroke();

    ctx.font = "10px sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        const iy = ly + 8 + i * lineH + lineH / 2;

        if (item.icon) {
            ctx.font = "10px sans-serif";
            ctx.fillText(item.icon, lx + 6, iy);
        } else {
            // Agent circle
            ctx.fillStyle = item.color;
            ctx.beginPath();
            ctx.arc(lx + 11, iy, 4, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.fillStyle = "#555";
        ctx.font = "10px sans-serif";
        ctx.fillText(item.label, lx + 24, iy);
    }
}

// --- Main render ---

function render(state) {
    ctx.fillStyle = COLORS.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Grid lines
    ctx.strokeStyle = COLORS.gridLine;
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= gridWidth; i++) {
        ctx.beginPath();
        ctx.moveTo(i * cellSize, 0);
        ctx.lineTo(i * cellSize, canvas.height);
        ctx.stroke();
    }
    for (let i = 0; i <= gridHeight; i++) {
        ctx.beginPath();
        ctx.moveTo(0, i * cellSize);
        ctx.lineTo(canvas.width, i * cellSize);
        ctx.stroke();
    }

    if (showDensityField) renderDensityField(state);
    if (showCognitiveMap) renderCognitiveMap(state);
    if (showPerception) renderPerceptionRadius(state);
    if (showVTE) renderVTE(state);

    // Stimuli
    const STIM_ICONS = { food: "\u{1F33F}", water: "\u{1F4A7}", light: "\u2600", heat: "\u{1F525}", obstacle: "\u25A0" };
    if (state.stimuli) {
        for (const stim of state.stimuli) {
            const [x, y] = stim.position;
            ctx.fillStyle = COLORS[stim.type] || "#999";
            ctx.globalAlpha = Math.max(0.3, stim.intensity);
            ctx.fillRect(x * cellSize + 1, y * cellSize + 1, cellSize - 2, cellSize - 2);
            ctx.globalAlpha = 1.0;

            // Icon
            const icon = STIM_ICONS[stim.type];
            if (icon) {
                const iconSize = Math.max(8, cellSize * 0.45);
                ctx.font = `${iconSize}px sans-serif`;
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(icon, x * cellSize + cellSize / 2, y * cellSize + cellSize / 2);
            }
        }
    }

    if (showPerception) renderPerceptionLines(state);

    // Agents
    if (state.agents) {
        for (const agent of state.agents) {
            const [x, y] = agent.position;
            const cx = x * cellSize + cellSize / 2;
            const cy = y * cellSize + cellSize / 2;
            const r = cellSize / 2.5;

            // Glow ring
            const pulse = 0.08 + 0.07 * Math.sin(Date.now() / 600);
            const glowR = r * 1.5;
            const gradient = ctx.createRadialGradient(cx, cy, r, cx, cy, glowR);
            gradient.addColorStop(0, `rgba(255, 152, 0, ${pulse})`);
            gradient.addColorStop(1, "rgba(255, 152, 0, 0)");
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(cx, cy, glowR, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = COLORS.agent;
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.fill();

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

    renderLegend();
    renderTooltip();

    document.getElementById("tick-counter").textContent = `Tick: ${state.tick}`;
}

function renderTooltip() {
    if (!hoveredStimulus) return;
    const s = hoveredStimulus;

    const lines = [
        `Type: ${s.type.charAt(0).toUpperCase() + s.type.slice(1)}`,
        `Intensity: ${(s.intensity * 100).toFixed(0)}%`,
        `Quantity: ${s.quantity != null ? s.quantity.toFixed(1) : "Infinite"}`,
        `Radius: ${s.radius != null ? s.radius.toFixed(1) : "-"}`,
    ];

    ctx.font = "11px monospace";
    const lineH = 16;
    const padX = 8;
    const padY = 6;
    const textW = Math.max(...lines.map(l => ctx.measureText(l).width));
    const tooltipW = textW + padX * 2;
    const tooltipH = lines.length * lineH + padY * 2;
    const offset = 12;

    // Position: prefer right/below cursor, flip if near edges
    let tx = hoverPixel.x + offset;
    let ty = hoverPixel.y + offset;
    if (tx + tooltipW > canvas.width) tx = hoverPixel.x - tooltipW - offset;
    if (ty + tooltipH > canvas.height) ty = hoverPixel.y - tooltipH - offset;
    tx = Math.max(0, tx);
    ty = Math.max(0, ty);

    // Background
    ctx.fillStyle = "rgba(255, 255, 255, 0.94)";
    ctx.strokeStyle = "#bbb";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(tx, ty, tooltipW, tooltipH, 4);
    ctx.fill();
    ctx.stroke();

    // Text
    ctx.fillStyle = "#333";
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    for (let i = 0; i < lines.length; i++) {
        ctx.fillText(lines[i], tx + padX, ty + padY + i * lineH);
    }
}

// --- Dashboard updates ---

function updatePerceptionList(agent) {
    const types = ["food", "water", "light", "heat", "obstacle"];
    // Build best perception per type (highest intensity, closest distance)
    const best = {};
    for (const t of types) best[t] = { intensity: 0, distance: null };
    if (agent.perceptions) {
        for (const p of agent.perceptions) {
            const t = p.stimulus_type;
            if (!(t in best)) continue;
            if (p.perceived_intensity > best[t].intensity) {
                best[t].intensity = p.perceived_intensity;
            }
            if (best[t].distance === null || p.distance < best[t].distance) {
                best[t].distance = p.distance;
            }
        }
    }
    for (const t of types) {
        const intEl = document.getElementById(`perc-${t}`);
        const distEl = document.getElementById(`perc-${t}-dist`);
        if (intEl) intEl.textContent = `${(best[t].intensity * 100).toFixed(0)}%`;
        if (distEl) distEl.textContent = best[t].distance !== null ? best[t].distance.toFixed(1) : "-";
    }
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

    const densityField = agent.density_field || {};
    const densityValues = Object.values(densityField);
    const densityPeak = densityValues.length > 0 ? Math.max(...densityValues) : 0;
    document.getElementById("mem-density-peak").textContent = densityPeak.toFixed(2);
}

function urgencyColor(value) {
    if (value < 0.3) return "#4CAF50";       // green
    if (value < 0.6) return "#FFC107";       // yellow
    if (value < 0.8) return "#FF9800";       // orange
    return "#F44336";                         // red
}

function updateDashboard(state) {
    if (!state.agents || state.agents.length === 0) return;
    const agent = state.agents[0];
    const drives = agent.drive_levels || {};

    for (const [name] of [["hunger"], ["thirst"], ["temperature"]]) {
        let val = 0;
        for (const [k, v] of Object.entries(drives)) {
            if (k.toLowerCase().includes(name)) {
                val = v;
                break;
            }
        }
        const bar = document.getElementById(`bar-${name}`);
        const valEl = document.getElementById(`val-${name}`);
        const color = urgencyColor(val);
        if (bar) {
            bar.style.width = `${val * 100}%`;
            bar.style.background = color;
        }
        if (valEl) {
            valEl.textContent = val.toFixed(2);
            valEl.style.color = color;
        }
        const barBg = bar ? bar.parentElement : null;
        if (barBg && barBg.hasAttribute("aria-valuenow")) {
            barBg.setAttribute("aria-valuenow", val.toFixed(2));
        }
    }

    const satiety = agent.satiety_levels || {};
    for (const [name] of [["hunger"], ["thirst"], ["temperature"]]) {
        let sat = 0;
        for (const [k, v] of Object.entries(satiety)) {
            if (k.toLowerCase().includes(name)) {
                sat = v;
                break;
            }
        }
        const satBar = document.getElementById(`satiety-${name}`);
        if (satBar) {
            satBar.style.width = `${sat * 100}%`;
        }
    }

    document.getElementById("agent-pos").textContent =
        `(${agent.position[0]}, ${agent.position[1]})`;
    document.getElementById("agent-orient").textContent = agent.orientation;

    updatePerceptionList(agent);
    updateMemorySummary(agent);
    updateVTESummary(agent);
    updateA11yLiveRegion(state);
}

function updateVTESummary(agent) {
    const vte = agent.vte;
    const container = document.getElementById("vte-status");
    if (!container) return;

    if (!vte || !vte.candidates || vte.candidates.length === 0) {
        container.innerHTML = '<p class="empty-state">No deliberation</p>';
        return;
    }

    const status = vte.hesitated ? "Hesitating" :
                   vte.is_deliberating ? "Deliberating" : "Decided";
    const statusClass = vte.hesitated ? "vte-hesitating" :
                        vte.is_deliberating ? "vte-deliberating" : "vte-decided";

    const candidateRows = vte.candidates.map(c => {
        const pct = vte.candidates[0].value > 0
            ? (c.value / vte.candidates[0].value * 100).toFixed(0)
            : "0";
        const chosen = c.direction === vte.chosen ? " chosen" : "";
        return `<div class="vte-candidate${chosen}">
            <span class="dir-label">${c.direction}</span>
            <div class="bar-bg"><div class="bar-fill vte-bar" style="width:${pct}%"></div></div>
            <span class="vte-val">${c.value.toFixed(3)}</span>
        </div>`;
    }).join("");

    container.innerHTML = `<div class="vte-header ${statusClass}">${status}</div>${candidateRows}`;
}

// --- Controls ---
document.getElementById("btn-play").onclick = () => {
    send({ action: "play" });
    document.getElementById("place-section").classList.add("editing-disabled");
    document.getElementById("edit-hint").textContent = "Pause to edit";
};
document.getElementById("btn-pause").onclick = () => {
    send({ action: "pause" });
    document.getElementById("place-section").classList.remove("editing-disabled");
    document.getElementById("edit-hint").textContent = "L-click place / R-click remove";
};
document.getElementById("btn-step").onclick = () => send({ action: "step" });
document.getElementById("btn-reset").onclick = () => send({ action: "reset" });

const speedSlider = document.getElementById("speed-slider");
const speedVal = document.getElementById("speed-val");
speedSlider.oninput = () => {
    speedVal.textContent = speedSlider.value;
    send({ action: "speed", value: parseInt(speedSlider.value) });
};

// Preset selector
const presetSelect = document.getElementById("preset-select");
presetSelect.onchange = () => {
    if (presetSelect.value) {
        send({ action: "load_preset", preset: presetSelect.value });
    }
};

// Grid resize
document.getElementById("btn-regenerate").onclick = () => {
    const w = parseInt(document.getElementById("grid-width").value) || 20;
    const h = parseInt(document.getElementById("grid-height").value) || 20;
    presetSelect.value = "";
    send({ action: "resize", width: w, height: h });
};

// Reset preset dropdown on manual width/height changes
document.getElementById("grid-width").oninput = () => { presetSelect.value = ""; };
document.getElementById("grid-height").oninput = () => { presetSelect.value = ""; };

// Save current environment as a preset
document.getElementById("btn-save-preset").onclick = () => {
    const name = prompt("Preset name:");
    if (name && name.trim()) {
        send({ action: "save_preset", name: name.trim() });
    }
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
document.getElementById("toggle-density").onchange = (e) => {
    showDensityField = e.target.checked;
    if (latestState) render(latestState);
};
document.getElementById("toggle-vte").onchange = (e) => {
    showVTE = e.target.checked;
    if (latestState) render(latestState);
};
document.getElementById("toggle-legend").onchange = (e) => {
    showLegend = e.target.checked;
    if (latestState) render(latestState);
};

// --- Canvas drag-to-paint & right-click remove ---
let _painting = false;
let _lastPaintCell = null;

function canvasToGrid(e) {
    const rect = canvas.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / (rect.width / gridWidth));
    const y = Math.floor((e.clientY - rect.top) / (rect.height / gridHeight));
    return [
        Math.max(0, Math.min(gridWidth - 1, x)),
        Math.max(0, Math.min(gridHeight - 1, y)),
    ];
}

function placeStimulus(x, y) {
    const key = `${x},${y}`;
    if (_lastPaintCell === key) return;  // skip duplicate
    _lastPaintCell = key;
    const stimType = document.getElementById("stim-type").value;
    const msg = {
        action: "add_stimulus",
        stimulus_type: stimType,
        position: [x, y],
        intensity: 1.0,
        radius: 5.0,
    };
    if (stimType === "food" || stimType === "water") {
        msg.quantity = 5.0;
    }
    send(msg);
}

canvas.addEventListener("mousedown", (e) => {
    if (e.button === 0) {  // left button
        _painting = true;
        _lastPaintCell = null;
        const [x, y] = canvasToGrid(e);
        placeStimulus(x, y);
    }
});

canvas.addEventListener("mousemove", (e) => {
    const [gx, gy] = canvasToGrid(e);
    if (_painting) {
        placeStimulus(gx, gy);
    }
    // Hover detection for stimulus tooltip
    const rect = canvas.getBoundingClientRect();
    hoverPixel.x = e.clientX - rect.left;
    hoverPixel.y = e.clientY - rect.top;
    let found = null;
    if (latestState && latestState.stimuli) {
        for (const stim of latestState.stimuli) {
            if (stim.position[0] === gx && stim.position[1] === gy) {
                found = stim;
                break;
            }
        }
    }
    if (found !== hoveredStimulus) {
        hoveredStimulus = found;
        if (latestState) render(latestState);
    }
});

canvas.addEventListener("mouseup", () => { _painting = false; });
canvas.addEventListener("mouseleave", () => {
    _painting = false;
    if (hoveredStimulus) {
        hoveredStimulus = null;
        if (latestState) render(latestState);
    }
});

// Right-click to remove stimulus
canvas.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    const [x, y] = canvasToGrid(e);
    send({ action: "remove_stimulus", position: [x, y] });
});

// --- Chart hover events ---
const driveChartCanvas = document.getElementById("drive-chart-canvas");
const coverageChartCanvas = document.getElementById("coverage-chart-canvas");

driveChartCanvas.addEventListener("mousemove", (e) => {
    const rect = driveChartCanvas.getBoundingClientRect();
    driveChartHoverX = e.clientX - rect.left;
    renderDriveChart();
});
driveChartCanvas.addEventListener("mouseleave", () => {
    driveChartHoverX = null;
    renderDriveChart();
});

coverageChartCanvas.addEventListener("mousemove", (e) => {
    const rect = coverageChartCanvas.getBoundingClientRect();
    resourceChartHoverX = e.clientX - rect.left;
    renderChart();
});
coverageChartCanvas.addEventListener("mouseleave", () => {
    resourceChartHoverX = null;
    renderChart();
});

// --- Keyboard shortcuts ---
document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT" || e.target.tagName === "TEXTAREA") return;
    if (e.code === "Space") {
        e.preventDefault();
        const placeSection = document.getElementById("place-section");
        if (placeSection.classList.contains("editing-disabled")) {
            document.getElementById("btn-pause").click();
        } else {
            document.getElementById("btn-play").click();
        }
    }
});

// --- Accessibility: periodic live region update ---
let _a11yTick = 0;
function updateA11yLiveRegion(state) {
    if (!state.agents || state.agents.length === 0) return;
    const tick = state.tick || 0;
    if (tick - _a11yTick < 5) return;
    _a11yTick = tick;
    const agent = state.agents[0];
    const drives = agent.drive_levels || {};
    let summary = `Tick ${tick}. Position ${agent.position[0]},${agent.position[1]}.`;
    for (const [k, v] of Object.entries(drives)) {
        summary += ` ${k}: ${v.toFixed(2)}.`;
    }
    const el = document.getElementById("a11y-live");
    if (el) el.textContent = summary;
}

// Start
connectWebSocket();
