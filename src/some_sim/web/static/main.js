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
};

let ws = null;
let latestState = null;

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

function render(state) {
    ctx.fillStyle = COLORS.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Grid lines
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

    // Stimuli
    if (state.stimuli) {
        for (const stim of state.stimuli) {
            const [x, y] = stim.position;
            ctx.fillStyle = COLORS[stim.type] || "#999";
            ctx.globalAlpha = Math.max(0.3, stim.intensity);
            ctx.fillRect(x * CELL_SIZE + 1, y * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2);
            ctx.globalAlpha = 1.0;
        }
    }

    // Agents
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
}

// Controls
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
