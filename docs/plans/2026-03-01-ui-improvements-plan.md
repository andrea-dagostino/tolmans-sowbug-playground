# UI Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve the Schematic Sowbug Simulation UI across 7 priority areas: drive urgency coloring, chart interactivity, canvas legend/icons, sidebar grouping, toolbar separation, visual polish, and responsiveness/accessibility.

**Architecture:** All changes are in-place edits to the three existing frontend files (`index.html`, `style.css`, `main.js`). No new dependencies or files. Pure canvas for chart interactivity. The server (`server.py`) is unchanged.

**Tech Stack:** Vanilla HTML/CSS/JS, Canvas 2D API

**Files:**
- Modify: `src/tolmans_sowbug_playground/web/static/style.css`
- Modify: `src/tolmans_sowbug_playground/web/static/index.html`
- Modify: `src/tolmans_sowbug_playground/web/static/main.js`

**Verification:** Since this is a pure-frontend project with no JS test framework, each task is verified by launching the web server (`uv run python -m tolmans_sowbug_playground serve --config configs/sowbug_basic.yaml`) and visually confirming the changes in a browser.

---

### Task 1: Drive Bar Urgency Coloring + Thresholds

**Files:**
- Modify: `src/tolmans_sowbug_playground/web/static/style.css:190-198`
- Modify: `src/tolmans_sowbug_playground/web/static/main.js:674-691`
- Modify: `src/tolmans_sowbug_playground/web/static/index.html:79-93`

**Step 1: Update CSS for urgency-aware drive bars**

In `style.css`, replace lines 190-198:

```css
/* ---- Drives ---- */
.drive-bar { display: flex; align-items: center; gap: 0.3rem; margin-bottom: 0.25rem; }
.drive-bar label { width: 68px; font-size: 0.75rem; color: #555; flex-shrink: 0; }
.bar-bg { flex: 1; height: 10px; background: #eee; border-radius: 3px; overflow: hidden; position: relative; }
.bar-fill { height: 100%; border-radius: 3px; transition: width 0.2s, background-color 0.3s; }
.bar-fill.hunger { background: #4CAF50; }
.bar-fill.thirst { background: #2196F3; }
.bar-fill.temperature { background: #F44336; }
.bar-bg .threshold-marker {
    position: absolute;
    top: 0;
    left: 80%;
    width: 2px;
    height: 100%;
    background: rgba(0, 0, 0, 0.25);
    pointer-events: none;
}
.drive-bar span:last-child { width: 30px; font-size: 0.7rem; font-family: monospace; text-align: right; color: #666; transition: color 0.3s; }
```

**Step 2: Add threshold markers to HTML drive bars**

In `index.html`, replace each drive bar's `bar-bg` div to include a threshold marker. Replace lines 79-93:

```html
                    <div class="drive-bar">
                        <label>Hunger</label>
                        <div class="bar-bg"><div id="bar-hunger" class="bar-fill hunger"></div><div class="threshold-marker"></div></div>
                        <span id="val-hunger">0.00</span>
                    </div>
                    <div class="drive-bar">
                        <label>Thirst</label>
                        <div class="bar-bg"><div id="bar-thirst" class="bar-fill thirst"></div><div class="threshold-marker"></div></div>
                        <span id="val-thirst">0.00</span>
                    </div>
                    <div class="drive-bar">
                        <label>Temperature</label>
                        <div class="bar-bg"><div id="bar-temperature" class="bar-fill temperature"></div><div class="threshold-marker"></div></div>
                        <span id="val-temperature">0.00</span>
                    </div>
```

**Step 3: Add urgency color function and update dashboard JS**

In `main.js`, add urgency color function before `updateDashboard` (before line 674):

```javascript
function urgencyColor(value) {
    if (value < 0.3) return "#4CAF50";       // green
    if (value < 0.6) return "#FFC107";       // yellow
    if (value < 0.8) return "#FF9800";       // orange
    return "#F44336";                         // red
}
```

Then update the drive bar loop inside `updateDashboard` (replace lines 679-691):

```javascript
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
        if (bar) {
            bar.style.width = `${val * 100}%`;
            bar.style.background = urgencyColor(val);
        }
        if (valEl) {
            valEl.textContent = val.toFixed(2);
            valEl.style.color = urgencyColor(val);
        }
    }
```

**Step 4: Verify**

Run: `uv run python -m tolmans_sowbug_playground serve --config configs/sowbug_basic.yaml`

Expected: Drive bars change color as values increase. Threshold marker visible at 80%. Value text color matches bar color.

**Step 5: Commit**

```bash
git add src/tolmans_sowbug_playground/web/static/style.css src/tolmans_sowbug_playground/web/static/index.html src/tolmans_sowbug_playground/web/static/main.js
git commit -m "feat(ui): add drive bar urgency coloring and threshold markers"
```

---

### Task 2: Chart Hover Tooltips + Event Annotations

**Files:**
- Modify: `src/tolmans_sowbug_playground/web/static/main.js:24-31` (add state vars)
- Modify: `src/tolmans_sowbug_playground/web/static/main.js:335-444` (renderChart)
- Modify: `src/tolmans_sowbug_playground/web/static/main.js:448-547` (renderDriveChart)
- Modify: `src/tolmans_sowbug_playground/web/static/main.js` (add event listeners at bottom)

**Step 1: Add state variables for hover and events**

In `main.js`, after line 32 (`let showVTE = true;`), add:

```javascript
let showLegend = true;
let driveChartHoverX = null;
let accuracyChartHoverX = null;
let eventLog = [];
let _lastDrives = { hunger: 0, thirst: 0, temperature: 0 };
let _firstDeliberation = false;
```

**Step 2: Add event detection to the WebSocket onmessage handler**

In `main.js`, inside `ws.onmessage`, after the `driveHistory.push(entry)` line (after line 90), add event detection:

```javascript
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
```

Also, in the reset detection block (where `accuracyHistory = []` on tick reset, around line 72-74), add:

```javascript
            eventLog = [];
            _lastDrives = { hunger: 0, thirst: 0, temperature: 0 };
            _firstDeliberation = false;
```

**Step 3: Add crosshair/tooltip rendering to renderDriveChart**

At the end of `renderDriveChart()`, before the closing `}`, add:

```javascript
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
```

**Step 4: Add crosshair/tooltip rendering to renderChart (accuracy)**

At the end of `renderChart()`, before the closing `}`, after the `cCtx.fill()` line (fill under line), add:

```javascript
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
    if (accuracyChartHoverX !== null) {
        const hx = accuracyChartHoverX;
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
            let closest = accuracyHistory[0];
            let minDist = Infinity;
            for (const d of accuracyHistory) {
                const dist = Math.abs(d.tick - hoverTick);
                if (dist < minDist) { minDist = dist; closest = d; }
            }

            const tooltipW = 100;
            const tooltipH = 28;
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
            cCtx.fillText(`Acc: ${(closest.accuracy * 100).toFixed(1)}%`, tx + 4, ty + 16);
        }
    }
```

**Step 5: Add mouse event listeners for chart canvases**

At the bottom of `main.js`, before `connectWebSocket()`, add:

```javascript
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
    accuracyChartHoverX = e.clientX - rect.left;
    renderChart();
});
coverageChartCanvas.addEventListener("mouseleave", () => {
    accuracyChartHoverX = null;
    renderChart();
});
```

**Step 6: Verify**

Run the server, play the simulation for ~50 ticks. Hover over charts to see crosshair + tooltip. Wait for a drive drop to see event annotation lines.

**Step 7: Commit**

```bash
git add src/tolmans_sowbug_playground/web/static/main.js
git commit -m "feat(ui): add chart hover tooltips and event annotations"
```

---

### Task 3: Canvas Legend + Resource Icons

**Files:**
- Modify: `src/tolmans_sowbug_playground/web/static/main.js:576-585` (stimuli rendering)
- Modify: `src/tolmans_sowbug_playground/web/static/main.js:551-614` (render function)
- Modify: `src/tolmans_sowbug_playground/web/static/index.html:124-127` (add legend toggle)

**Step 1: Add legend toggle to HTML**

In `index.html`, after the VTE Arrows toggle (line 127), add:

```html
                    <label class="toggle-label">
                        <input type="checkbox" id="toggle-legend" checked>
                        Legend
                    </label>
```

**Step 2: Add resource icons to stimulus rendering**

In `main.js`, replace the stimuli rendering block (the `if (state.stimuli)` block around lines 577-585):

```javascript
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
```

**Step 3: Add renderLegend function**

In `main.js`, add this function before the `render` function:

```javascript
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
```

**Step 4: Call renderLegend at the end of render()**

In `main.js`, in the `render()` function, after the agents rendering block and before the tick counter update (before line 613), add:

```javascript
    renderLegend();
```

**Step 5: Add legend toggle event listener**

At the bottom of `main.js` with the other overlay toggles, add:

```javascript
document.getElementById("toggle-legend").onchange = (e) => {
    showLegend = e.target.checked;
    if (latestState) render(latestState);
};
```

**Step 6: Verify**

Run the server. Confirm icons appear on resource tiles. Confirm legend is visible in the top-right corner of the canvas and can be toggled off.

**Step 7: Commit**

```bash
git add src/tolmans_sowbug_playground/web/static/main.js src/tolmans_sowbug_playground/web/static/index.html
git commit -m "feat(ui): add canvas resource icons and floating legend"
```

---

### Task 4: Sidebar Grouping + Panel Tooltips

**Files:**
- Modify: `src/tolmans_sowbug_playground/web/static/index.html:62-248`
- Modify: `src/tolmans_sowbug_playground/web/static/style.css:142-151`

**Step 1: Restructure sidebar HTML into groups**

In `index.html`, replace the entire `<aside id="sidebar">` block (lines 62-248) with:

```html
            <!-- Right column: Config, Params & Tracing -->
            <aside id="sidebar">
                <div class="sidebar-group">
                    <div class="sidebar-group-label">Controls</div>
                    <div class="panel" id="controls">
                        <h2>Controls</h2>
                        <div id="btn-group">
                            <button id="btn-play" aria-label="Play simulation">Play</button>
                            <button id="btn-pause" aria-label="Pause simulation">Pause</button>
                            <button id="btn-step" aria-label="Step one tick">Step</button>
                            <button id="btn-reset" aria-label="Reset simulation">Reset</button>
                        </div>
                        <div id="speed-control">
                            <label>Speed: <span id="speed-val">5</span> tps
                                <input type="range" id="speed-slider" min="1" max="30" value="5" aria-label="Simulation speed">
                            </label>
                        </div>
                    </div>
                    <div class="panel" id="overlays">
                        <h2>Overlays</h2>
                        <label class="toggle-label">
                            <input type="checkbox" id="toggle-cogmap" checked>
                            Cognitive Map
                        </label>
                        <label class="toggle-label">
                            <input type="checkbox" id="toggle-perception" checked>
                            Perception
                        </label>
                        <label class="toggle-label">
                            <input type="checkbox" id="toggle-density" checked>
                            Density Field
                        </label>
                        <label class="toggle-label">
                            <input type="checkbox" id="toggle-vte" checked>
                            VTE Arrows
                        </label>
                        <label class="toggle-label">
                            <input type="checkbox" id="toggle-legend" checked>
                            Legend
                        </label>
                        <details class="panel-help">
                            <summary>?</summary>
                            <dl>
                                <dt>Cognitive Map</dt>
                                <dd>Diamond markers at remembered stimulus locations, connected by purple edge lines. Opacity reflects memory strength.</dd>
                                <dt>Perception</dt>
                                <dd>Dashed sensory radius circle and lines to detected stimuli, colored by type.</dd>
                                <dt>Density Field</dt>
                                <dd>KDE heatmap of reward-weighted experience. Brighter cells have more accumulated value.</dd>
                                <dt>VTE Arrows</dt>
                                <dd>Directional arrows showing simulated reward per direction. Purple = decided, magenta = deliberating. Arrow length = relative value.</dd>
                            </dl>
                        </details>
                    </div>
                </div>
                <div class="sidebar-group">
                    <div class="sidebar-group-label">Status</div>
                    <div class="panel" id="drives">
                        <h2>Drives</h2>
                        <div class="drive-bar">
                            <label>Hunger</label>
                            <div class="bar-bg" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="1" aria-label="Hunger level"><div id="bar-hunger" class="bar-fill hunger"></div><div class="threshold-marker"></div></div>
                            <span id="val-hunger">0.00</span>
                        </div>
                        <div class="drive-bar">
                            <label>Thirst</label>
                            <div class="bar-bg" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="1" aria-label="Thirst level"><div id="bar-thirst" class="bar-fill thirst"></div><div class="threshold-marker"></div></div>
                            <span id="val-thirst">0.00</span>
                        </div>
                        <div class="drive-bar">
                            <label>Temperature</label>
                            <div class="bar-bg" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="1" aria-label="Temperature level"><div id="bar-temperature" class="bar-fill temperature"></div><div class="threshold-marker"></div></div>
                            <span id="val-temperature">0.00</span>
                        </div>
                        <details class="panel-help">
                            <summary>?</summary>
                            <dl>
                                <dt>Drives</dt>
                                <dd>Internal motivational states that rise each tick at a fixed rate and bias the agent toward relevant stimuli.</dd>
                                <dt>Hunger</dt>
                                <dd>Satisfied by food. The most urgent drive determines which stimulus the agent seeks.</dd>
                                <dt>Thirst</dt>
                                <dd>Satisfied by water. Same priority logic as hunger.</dd>
                                <dt>Temperature</dt>
                                <dd>Satisfied by heat sources. Rises at a slower default rate.</dd>
                                <dt>Phototaxis</dt>
                                <dd>When drives are low, the agent is drawn toward light. High drives suppress this tendency.</dd>
                            </dl>
                        </details>
                    </div>
                    <div class="panel" id="perceptions">
                        <h2>Perceptions</h2>
                        <div id="perception-list">
                            <div class="perception-header">
                                <span class="dot-placeholder"></span>
                                <span class="type-label">Type</span>
                                <span class="intensity">Intens.</span>
                                <span class="distance">Dist.</span>
                            </div>
                            <div class="perception-item" data-stim="food">
                                <span class="dot" style="background:#4CAF50"></span>
                                <span class="type-label">food</span>
                                <span class="intensity" id="perc-food">0%</span>
                                <span class="distance" id="perc-food-dist">-</span>
                            </div>
                            <div class="perception-item" data-stim="water">
                                <span class="dot" style="background:#2196F3"></span>
                                <span class="type-label">water</span>
                                <span class="intensity" id="perc-water">0%</span>
                                <span class="distance" id="perc-water-dist">-</span>
                            </div>
                            <div class="perception-item" data-stim="light">
                                <span class="dot" style="background:#FFEB3B"></span>
                                <span class="type-label">light</span>
                                <span class="intensity" id="perc-light">0%</span>
                                <span class="distance" id="perc-light-dist">-</span>
                            </div>
                            <div class="perception-item" data-stim="heat">
                                <span class="dot" style="background:#F44336"></span>
                                <span class="type-label">heat</span>
                                <span class="intensity" id="perc-heat">0%</span>
                                <span class="distance" id="perc-heat-dist">-</span>
                            </div>
                            <div class="perception-item" data-stim="obstacle">
                                <span class="dot" style="background:#424242"></span>
                                <span class="type-label">obstacle</span>
                                <span class="intensity" id="perc-obstacle">0%</span>
                                <span class="distance" id="perc-obstacle-dist">-</span>
                            </div>
                        </div>
                        <details class="panel-help">
                            <summary>?</summary>
                            <dl>
                                <dt>Perception</dt>
                                <dd>All stimulus types are shown. Intensity and distance update when a stimulus is within the agent's sensory radius; otherwise they stay at 0% / -.</dd>
                                <dt>Intensity %</dt>
                                <dd>Highest perceived strength for that type. Decays linearly from 100% at the source to 0% at the radius edge.</dd>
                                <dt>Distance</dt>
                                <dd>Euclidean distance to the closest detected stimulus of that type, in grid cells.</dd>
                            </dl>
                        </details>
                    </div>
                    <div class="panel" id="memory">
                        <h2>Memory</h2>
                        <div id="memory-stats">
                            <p title="Cells in the cognitive map where a stimulus was recorded">Locations: <span id="mem-locations">0</span></p>
                            <p title="Directed traversals between adjacent cells">Edges: <span id="mem-edges">0</span></p>
                            <p title="Total cells the agent has stepped on">Visited: <span id="mem-visited">0</span></p>
                            <p title="Average edge strength (confidence in learned paths)">Avg strength: <span id="mem-strength">0.00</span></p>
                            <p title="Maximum value in the KDE density field">Density peak: <span id="mem-density-peak">-</span></p>
                        </div>
                        <details class="panel-help">
                            <summary>?</summary>
                            <dl>
                                <dt>Locations</dt>
                                <dd>Cells in the cognitive map where the agent recorded a stimulus encounter (type, intensity, reward).</dd>
                                <dt>Edges</dt>
                                <dd>Directed traversals between adjacent cells. Each step the agent takes adds or increments an edge.</dd>
                                <dt>Visited</dt>
                                <dd>Total cells the agent has stepped on. Familiarity decays over time; cells below 0.01 are forgotten.</dd>
                                <dt>Avg strength</dt>
                                <dd>Mean memory strength across all cognitive map entries. Strength rises when predictions match reality, decays each tick.</dd>
                                <dt>Density peak</dt>
                                <dd>Maximum value in the KDE density field — the hottest spot of reward-weighted experience.</dd>
                            </dl>
                        </details>
                    </div>
                    <div class="panel" id="vte-section">
                        <h2>Deliberation (VTE)</h2>
                        <div id="vte-status">
                            <p class="empty-state">No deliberation</p>
                        </div>
                        <details class="panel-help">
                            <summary>?</summary>
                            <dl>
                                <dt>VTE</dt>
                                <dd>Vicarious Trial and Error. The agent mentally simulates each direction using its cognitive map, accumulating discounted expected reward over a BFS horizon.</dd>
                                <dt>Deliberating</dt>
                                <dd>The top two directional values are within the VTE threshold — the agent is uncertain which way to go.</dd>
                                <dt>Hesitating</dt>
                                <dd>During deliberation, the agent sometimes pauses (Direction.STAY) instead of committing.</dd>
                                <dt>Decided</dt>
                                <dd>One direction clearly dominates; the agent commits without hesitation.</dd>
                                <dt>Candidates</dt>
                                <dd>The four cardinal directions with their simulated reward values. Bar length is relative to the best candidate.</dd>
                            </dl>
                        </details>
                    </div>
                    <div class="panel" id="info">
                        <h2>Agent</h2>
                        <p>Position: <span id="agent-pos">-</span></p>
                        <p>Orientation: <span id="agent-orient">-</span></p>
                        <details class="panel-help">
                            <summary>?</summary>
                            <dl>
                                <dt>Position</dt>
                                <dd>The agent's current (x, y) cell on the grid.</dd>
                                <dt>Orientation</dt>
                                <dd>The direction the agent last moved (N/S/E/W), shown as a heading line on the agent circle.</dd>
                            </dl>
                        </details>
                    </div>
                </div>
            </aside>
```

**Step 2: Add CSS for sidebar groups and perception header**

In `style.css`, after the `#sidebar::-webkit-scrollbar-thumb` rule (after line 154), add:

```css
.sidebar-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.sidebar-group-label {
    font-size: 0.6rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #78909C;
    padding: 0.2rem 0;
    border-bottom: 2px solid #78909C;
    margin-bottom: -0.25rem;
}

.perception-header {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.6rem;
    font-weight: 600;
    color: #aaa;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 0.15rem;
    border-bottom: 1px solid #eee;
    padding-bottom: 0.1rem;
}

.perception-header .dot-placeholder { width: 6px; flex-shrink: 0; }
.perception-header .type-label { flex: 1; }
.perception-header .intensity { font-family: monospace; width: 28px; text-align: right; }
.perception-header .distance { font-family: monospace; width: 32px; text-align: right; }
```

**Step 3: Verify**

Run the server. Confirm sidebar shows two labeled groups: "Controls" and "Status". Confirm perception panel has column headers. Confirm memory labels show full text and tooltips on hover.

**Step 4: Commit**

```bash
git add src/tolmans_sowbug_playground/web/static/index.html src/tolmans_sowbug_playground/web/static/style.css
git commit -m "feat(ui): add sidebar grouping, perception headers, and panel tooltips"
```

---

### Task 5: Toolbar Separation

**Files:**
- Modify: `src/tolmans_sowbug_playground/web/static/index.html:21-42`
- Modify: `src/tolmans_sowbug_playground/web/static/style.css:52-115`
- Modify: `src/tolmans_sowbug_playground/web/static/main.js` (add editing state tracking)

**Step 1: Restructure toolbar HTML**

In `index.html`, replace the toolbar div (lines 21-42):

```html
                <div id="env-toolbar">
                    <div class="toolbar-section">
                        <span class="toolbar-section-label">Map</span>
                        <select id="preset-select" aria-label="Map preset">
                            <option value="">Custom</option>
                            <option value="Empty">Empty</option>
                            <option value="Basic Foraging">Basic Foraging</option>
                            <option value="Choice Point">Choice Point</option>
                            <option value="Light + Drives">Light + Drives</option>
                        </select>
                        <label>W <input type="number" id="grid-width" value="20" min="5" max="100" aria-label="Grid width"></label>
                        <label>H <input type="number" id="grid-height" value="20" min="5" max="100" aria-label="Grid height"></label>
                        <button id="btn-regenerate">Regenerate</button>
                        <button id="btn-save-preset">Save</button>
                    </div>
                    <div class="toolbar-sep"></div>
                    <div class="toolbar-section" id="place-section">
                        <span class="toolbar-section-label">Place</span>
                        <select id="stim-type" aria-label="Stimulus type to place">
                            <option value="food">Food</option>
                            <option value="water">Water</option>
                            <option value="light">Light</option>
                            <option value="heat">Heat</option>
                            <option value="obstacle">Obstacle</option>
                        </select>
                        <span class="hint" id="edit-hint">L-click place / R-click remove</span>
                    </div>
                </div>
```

**Step 2: Update toolbar CSS**

In `style.css`, replace the toolbar styles (lines 52-115):

```css
/* Toolbar sits flush under canvas, same width */
#env-toolbar {
    background: white;
    border: 1px solid #ddd;
    border-top: none;
    border-radius: 0 0 4px 4px;
    padding: 0.3rem 0.6rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
    width: fit-content;
}

.toolbar-section {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.toolbar-section-label {
    font-size: 0.6rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #78909C;
}

#env-toolbar select {
    padding: 0.2rem 0.3rem;
    border: 1px solid #ccc;
    border-radius: 3px;
    font-size: 0.8rem;
}

#preset-select { min-width: 110px; }

#env-toolbar label {
    font-size: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.15rem;
    color: #666;
}

#env-toolbar input[type="number"] {
    width: 44px;
    padding: 0.15rem 0.25rem;
    border: 1px solid #ccc;
    border-radius: 3px;
    font-size: 0.8rem;
    font-family: monospace;
}

#btn-regenerate,
#btn-save-preset {
    padding: 0.2rem 0.5rem;
    border: 1px solid #ccc;
    border-radius: 3px;
    background: white;
    cursor: pointer;
    font-size: 0.75rem;
}
#btn-regenerate:hover,
#btn-save-preset:hover { background: #f0f0f0; }

.toolbar-sep {
    width: 1px;
    height: 18px;
    background: #ddd;
    flex-shrink: 0;
}

#env-toolbar .hint {
    font-size: 0.7rem;
    color: #aaa;
    font-style: italic;
}

#place-section.editing-disabled {
    opacity: 0.5;
    pointer-events: none;
}

#place-section.editing-disabled .hint {
    color: #E65100;
    font-style: normal;
}
```

**Step 3: Add editing state tracking to JS**

In `main.js`, in the play/pause button handlers, add code to toggle the editing-disabled class:

After the existing play/pause click handlers (around lines 733-734), modify them:

```javascript
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
```

**Step 4: Verify**

Run the server. Confirm toolbar shows "Map" and "Place" section labels. Click Play — Place section should dim with "Pause to edit" hint. Click Pause — Place section restores.

**Step 5: Commit**

```bash
git add src/tolmans_sowbug_playground/web/static/index.html src/tolmans_sowbug_playground/web/static/style.css src/tolmans_sowbug_playground/web/static/main.js
git commit -m "feat(ui): separate toolbar into Map and Place sections with edit mode"
```

---

### Task 6: Visual Polish Pass

**Files:**
- Modify: `src/tolmans_sowbug_playground/web/static/style.css` (typography, spacing, palette)
- Modify: `src/tolmans_sowbug_playground/web/static/main.js` (agent glow, chart line styles)

**Step 1: Update CSS typography and spacing**

In `style.css`:

1. Change body font-size from `13px` to `14px` (line 8)
2. Change `.panel` padding from `0.5rem 0.65rem` to `0.6rem 0.75rem` (line 161)
3. Change `.panel h2` font-size from `0.65rem` to `0.72rem` (line 165)
4. Change `#sidebar` gap from `0.5rem` to `0.65rem` (line 150)
5. Change `.panel-help dd` font-size from `0.65rem` to `0.68rem` (line 299)

**Step 2: Update chart rendering for better readability**

In `main.js`, in `renderDriveChart()`:

1. Change the series definitions to include dash patterns:

```javascript
    const series = [
        { key: "hunger",      color: "#4CAF50", label: "Hunger",      dash: [] },
        { key: "thirst",      color: "#2196F3", label: "Thirst",      dash: [6, 3] },
        { key: "temperature", color: "#F44336", label: "Temperature", dash: [2, 2] },
    ];
```

2. In the series drawing loop, add dash support and increase line width:

```javascript
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
```

3. Increase legend font from `9px` to `10px`:

```javascript
    cCtx.font = "10px sans-serif";
```

4. In the legend drawing, add dash indicator for each series:

```javascript
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
```

5. In `renderChart()`, increase accuracy line width from `1.5` to `2`.

**Step 3: Add agent glow effect**

In `main.js`, in the `render()` function, in the agents rendering block, add glow before the main circle:

Replace the agent rendering block with:

```javascript
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
```

**Step 4: Verify**

Run the server. Confirm: larger text, more padding in panels, agent has a subtle pulsing glow, drive chart uses dashed lines with thicker strokes, legend shows dash patterns.

**Step 5: Commit**

```bash
git add src/tolmans_sowbug_playground/web/static/style.css src/tolmans_sowbug_playground/web/static/main.js
git commit -m "feat(ui): visual polish — typography, spacing, agent glow, chart accessibility"
```

---

### Task 7: Responsiveness + Accessibility

**Files:**
- Modify: `src/tolmans_sowbug_playground/web/static/style.css` (responsive breakpoints)
- Modify: `src/tolmans_sowbug_playground/web/static/index.html` (ARIA attributes on canvases)
- Modify: `src/tolmans_sowbug_playground/web/static/main.js` (keyboard shortcuts, ARIA updates, live region)

**Step 1: Add responsive CSS breakpoints**

At the end of `style.css`, add:

```css
/* ---- Responsive ---- */
@media (max-width: 1200px) {
    main {
        grid-template-columns: 1fr;
    }
    #sidebar {
        max-height: none;
        flex-direction: row;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .sidebar-group {
        flex: 1;
        min-width: 220px;
    }
}

@media (max-width: 900px) {
    #sidebar {
        flex-direction: column;
    }
    .sidebar-group {
        min-width: 0;
    }
    .panel-help:not([open]) + .panel-help:not([open]) {
        /* Collapsed by default on small screens */
    }
    .panel {
        padding: 0.4rem 0.55rem;
    }
    #env-toolbar {
        flex-direction: column;
        align-items: flex-start;
    }
    .toolbar-sep {
        width: 100%;
        height: 1px;
    }
}

@media (max-width: 600px) {
    #app { padding: 0.5rem; }
    header h1 { font-size: 0.85rem; }
    .panel h2 { font-size: 0.6rem; }
}
```

**Step 2: Add ARIA attributes to canvases and a live region**

In `index.html`:

1. Update the grid canvas tag (line 19):
```html
                    <canvas id="grid-canvas" width="600" height="600" aria-label="Simulation grid showing the agent, resources, and cognitive map overlays" role="img"></canvas>
```

2. Update the chart canvases (lines 46-48):
```html
                    <canvas id="drive-chart-canvas" height="160" aria-label="Drive levels over time chart" role="img"></canvas>
                    <h3 class="chart-label">Prediction Accuracy</h3>
                    <canvas id="coverage-chart-canvas" height="120" aria-label="Prediction accuracy over time chart" role="img"></canvas>
```

3. Add a hidden live region just before `</main>`:
```html
                <div id="a11y-live" aria-live="polite" class="sr-only"></div>
```

**Step 3: Add screen-reader-only CSS class**

In `style.css`, add near the top (after the `*` reset):

```css
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}
```

**Step 4: Add keyboard shortcut and live region updates to JS**

At the bottom of `main.js`, before `connectWebSocket()`, add:

```javascript
// --- Keyboard shortcuts ---
document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT" || e.target.tagName === "TEXTAREA") return;
    if (e.code === "Space") {
        e.preventDefault();
        // Toggle play/pause
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
```

Then in `updateDashboard()`, at the end, add a call to `updateA11yLiveRegion(state)`.

Also update the ARIA progressbar values in the drive bar loop in `updateDashboard()`:

```javascript
        const barBg = bar ? bar.parentElement : null;
        if (barBg && barBg.hasAttribute("aria-valuenow")) {
            barBg.setAttribute("aria-valuenow", val.toFixed(2));
        }
```

**Step 5: Verify**

Run the server. Test:
1. Resize browser below 1200px — sidebar should stack below canvas
2. Resize below 900px — toolbar should stack vertically
3. Press Space — toggles play/pause
4. Tab through controls — all buttons/checkboxes focusable
5. Inspect ARIA attributes with browser dev tools

**Step 6: Commit**

```bash
git add src/tolmans_sowbug_playground/web/static/style.css src/tolmans_sowbug_playground/web/static/index.html src/tolmans_sowbug_playground/web/static/main.js
git commit -m "feat(ui): add responsive layout, ARIA accessibility, and keyboard shortcuts"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Drive bar urgency coloring + thresholds | CSS, HTML, JS |
| 2 | Chart hover tooltips + event annotations | JS |
| 3 | Canvas legend + resource icons | JS, HTML |
| 4 | Sidebar grouping + panel tooltips | HTML, CSS |
| 5 | Toolbar separation | HTML, CSS, JS |
| 6 | Visual polish (typography, spacing, glow, chart a11y) | CSS, JS |
| 7 | Responsiveness + accessibility | CSS, HTML, JS |
