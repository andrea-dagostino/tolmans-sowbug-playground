# Layout Restructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the web UI to a CSS Grid named-areas layout with ~70% canvas width, tiered sidebar, merged panels, and side-by-side charts.

**Architecture:** Replace the current 2-column `grid-template-columns: 4fr 1fr` with a CSS Grid using named areas (`canvas / toolbar / charts | sidebar`). The sidebar spans all rows and scrolls independently. Drives+Agent and Memory+VTE merge into combined panels.

**Tech Stack:** HTML, CSS (Grid + Flexbox), vanilla JS. No new dependencies.

**Design doc:** `docs/plans/2026-03-01-layout-restructure-design.md`

---

### Task 1: Restructure HTML into Grid Areas

**Files:**
- Modify: `src/tolmans_sowbug_playground/web/static/index.html`

This task restructures `<main>` from two children (`#env-column` + `#sidebar`) into four grid-area children (`#canvas-area` + `#toolbar-area` + `#charts-area` + `#sidebar`). The sidebar panel order changes to: Controls, Overlays, Drives+Agent (merged), Perceptions, Memory/Deliberation (merged). The monitoring div is removed; charts move to `#charts-area`.

**Step 1: Rewrite the HTML structure**

Replace the entire `<main>` block (lines 15–272) with:

```html
        <main>
            <!-- Grid area: canvas -->
            <div id="canvas-area">
                <div id="grid-container">
                    <canvas id="grid-canvas" width="600" height="600" aria-label="Simulation grid showing the agent, resources, and cognitive map overlays" role="img"></canvas>
                </div>
            </div>

            <!-- Grid area: toolbar -->
            <div id="toolbar-area">
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
            </div>

            <!-- Grid area: charts (side by side) -->
            <div id="charts-area">
                <div class="chart-container">
                    <h3 class="chart-label">Drives over time</h3>
                    <canvas id="drive-chart-canvas" height="160" aria-label="Drive levels over time chart" role="img"></canvas>
                </div>
                <div class="chart-container">
                    <h3 class="chart-label">Prediction Accuracy</h3>
                    <canvas id="coverage-chart-canvas" height="120" aria-label="Prediction accuracy over time chart" role="img"></canvas>
                </div>
                <details class="panel-help">
                    <summary>?</summary>
                    <dl>
                        <dt>Drive Chart</dt>
                        <dd>Plots the drive level for hunger, thirst and temperature over simulation ticks. Drives rise at a fixed rate and drop when the agent reaches the matching stimulus.</dd>
                        <dt>Prediction Accuracy</dt>
                        <dd>Cumulative accuracy of the agent's expectations vs. reality. Each time the agent updates a memory, the pre-update error is recorded. Accuracy = 1 - (cumulative error / prediction count). Trends upward as the agent learns.</dd>
                    </dl>
                </details>
            </div>

            <!-- Grid area: sidebar (scrolls independently) -->
            <aside id="sidebar">
                <!-- Tier 1: Interactive -->
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
                                <input type="range" id="speed-slider" min="1" max="30" value="5">
                            </label>
                        </div>
                    </div>
                    <div class="panel" id="overlays">
                        <h2>Overlays</h2>
                        <div class="overlay-toggles">
                            <label class="toggle-label">
                                <input type="checkbox" id="toggle-cogmap" checked>
                                Cog Map
                            </label>
                            <label class="toggle-label">
                                <input type="checkbox" id="toggle-perception" checked>
                                Perception
                            </label>
                            <label class="toggle-label">
                                <input type="checkbox" id="toggle-density" checked>
                                Density
                            </label>
                            <label class="toggle-label">
                                <input type="checkbox" id="toggle-vte" checked>
                                VTE
                            </label>
                            <label class="toggle-label">
                                <input type="checkbox" id="toggle-legend" checked>
                                Legend
                            </label>
                        </div>
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

                <!-- Tier 2: Live Status -->
                <div class="sidebar-group">
                    <div class="sidebar-group-label">Status</div>
                    <div class="panel" id="drives-agent">
                        <h2>Drives + Agent</h2>
                        <div class="drives-agent-row">
                            <div class="drives-col">
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
                            </div>
                            <div class="agent-col">
                                <p>Pos: <span id="agent-pos">-</span></p>
                                <p>Dir: <span id="agent-orient">-</span></p>
                            </div>
                        </div>
                        <details class="panel-help">
                            <summary>?</summary>
                            <dl>
                                <dt>Drives</dt>
                                <dd>Internal motivational states that rise each tick and bias the agent toward relevant stimuli.</dd>
                                <dt>Position</dt>
                                <dd>The agent's current (x, y) cell on the grid.</dd>
                                <dt>Direction</dt>
                                <dd>The direction the agent last moved (N/S/E/W).</dd>
                            </dl>
                        </details>
                    </div>
                </div>

                <!-- Tier 3: Reference -->
                <div class="sidebar-group">
                    <div class="sidebar-group-label">Reference</div>
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
                                <dd>Intensity and distance update when a stimulus is within the agent's sensory radius.</dd>
                                <dt>Intensity %</dt>
                                <dd>Highest perceived strength for that type. Decays linearly from 100% at the source to 0% at the radius edge.</dd>
                                <dt>Distance</dt>
                                <dd>Euclidean distance to the closest detected stimulus of that type, in grid cells.</dd>
                            </dl>
                        </details>
                    </div>
                    <div class="panel" id="memory-deliberation">
                        <h2>Memory / Deliberation</h2>
                        <div id="memory-stats">
                            <p title="Cells in the cognitive map where a stimulus was recorded">Locations: <span id="mem-locations">0</span></p>
                            <p title="Directed traversals between adjacent cells">Edges: <span id="mem-edges">0</span></p>
                            <p title="Total cells the agent has stepped on">Visited: <span id="mem-visited">0</span></p>
                            <p title="Average edge strength (confidence in learned paths)">Avg strength: <span id="mem-strength">0.00</span></p>
                            <p title="Maximum value in the KDE density field">Density peak: <span id="mem-density-peak">-</span></p>
                        </div>
                        <div class="panel-divider"></div>
                        <div id="vte-status">
                            <p class="empty-state">No deliberation</p>
                        </div>
                        <details class="panel-help">
                            <summary>?</summary>
                            <dl>
                                <dt>Locations</dt>
                                <dd>Cells in the cognitive map where the agent recorded a stimulus encounter.</dd>
                                <dt>Edges</dt>
                                <dd>Directed traversals between adjacent cells. Each step adds or increments an edge.</dd>
                                <dt>Visited</dt>
                                <dd>Total cells the agent has stepped on. Familiarity decays over time.</dd>
                                <dt>VTE</dt>
                                <dd>Vicarious Trial and Error. The agent mentally simulates each direction using its cognitive map.</dd>
                            </dl>
                        </details>
                    </div>
                </div>
            </aside>
            <div id="a11y-live" aria-live="polite" class="sr-only"></div>
        </main>
```

**Step 2: Verify the page loads**

Run: `uv run python -m tolmans_sowbug_playground serve --config configs/sowbug_basic.yaml`

Open browser to `http://localhost:8000`. The page will look broken (old CSS targeting old structure) but all elements should be present in DOM. Verify with browser DevTools that `#canvas-area`, `#toolbar-area`, `#charts-area`, and `#sidebar` are direct children of `<main>`.

**Step 3: Commit**

```bash
git add src/tolmans_sowbug_playground/web/static/index.html
git commit -m "refactor(ui): restructure HTML into grid areas with merged panels"
```

---

### Task 2: CSS Grid Layout and Merged Panel Styles

**Files:**
- Modify: `src/tolmans_sowbug_playground/web/static/style.css`

This task updates all CSS to match the new HTML structure: CSS Grid named areas on `<main>`, sidebar independent scroll, merged Drives+Agent layout, merged Memory/Deliberation panel, side-by-side charts, and compact inline overlays.

**Step 1: Rewrite the CSS**

Replace the full `style.css` with the updated version. Key changes from the original:

1. `main` uses `grid-template-areas` with `7fr 3fr` columns
2. `#canvas-area`, `#toolbar-area`, `#charts-area` get their grid-area assignments
3. `#sidebar` gets `grid-area: sidebar` and spans all rows with independent scroll
4. Remove `#env-column` and `#monitoring` styles (those elements no longer exist)
5. Add `.drives-agent-row` flex layout for the merged Drives+Agent panel
6. Add `.agent-col` compact styles
7. Add `.panel-divider` for Memory/Deliberation separator
8. Add `#charts-area` flex layout for side-by-side charts
9. Add `.overlay-toggles` flex-wrap for inline overlay checkboxes
10. Update responsive breakpoints

Complete replacement CSS:

```css
/* style.css — Schematic Sowbug */
* { margin: 0; padding: 0; box-sizing: border-box; }

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

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5;
    color: #333;
    font-size: 14px;
}

#app { max-width: 1600px; margin: 0 auto; padding: 0.75rem 1rem; }

header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #ddd;
}

header h1 { font-size: 1rem; font-weight: 600; }
#tick-counter { font-family: monospace; font-size: 0.85rem; color: #666; }

/* ---- CSS Grid: canvas / toolbar / charts | sidebar ---- */
main {
    display: grid;
    grid-template-columns: 7fr 3fr;
    grid-template-rows: 1fr auto auto;
    grid-template-areas:
        "canvas  sidebar"
        "toolbar sidebar"
        "charts  sidebar";
    gap: 0;
    align-items: start;
}

#canvas-area  { grid-area: canvas; }
#toolbar-area { grid-area: toolbar; }
#charts-area  { grid-area: charts; }
#sidebar      { grid-area: sidebar; }

/* ---- Canvas ---- */
#canvas-area {
    min-width: 0;
}

#grid-container {
    background: white;
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 3px;
    line-height: 0;
    width: fit-content;
}

#grid-canvas { display: block; cursor: crosshair; }

/* ---- Toolbar ---- */
#toolbar-area {
    min-width: 0;
}

#env-toolbar {
    background: white;
    border: 1px solid #ddd;
    border-top: none;
    border-radius: 0 0 4px 4px;
    padding: 0.4rem 0.6rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
    width: fit-content;
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

#place-section.editing-disabled {
    opacity: 0.5;
    pointer-events: none;
}

#place-section.editing-disabled .hint {
    color: #E65100;
    font-style: normal;
}

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
    margin-left: auto;
}

/* ---- Charts area (side by side) ---- */
#charts-area {
    display: flex;
    gap: 0.75rem;
    padding-top: 0.75rem;
    min-width: 0;
}

.chart-container {
    flex: 1;
    min-width: 0;
}

.chart-label {
    font-size: 0.6rem;
    font-weight: 600;
    color: #bbb;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 0.2rem;
}

#drive-chart-canvas,
#coverage-chart-canvas {
    width: 100%;
    background: #fff;
    border: 1px solid #eee;
    border-radius: 3px;
    display: block;
}
#drive-chart-canvas { height: 160px; }
#coverage-chart-canvas { height: 160px; }

#charts-area .panel-help {
    flex-basis: 100%;
    margin-top: 0.25rem;
    background: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 0.4rem 0.6rem;
}

/* ---- Sidebar (independent scroll, spans all rows) ---- */
#sidebar {
    min-width: 0;
    max-height: calc(100vh - 60px);
    overflow-y: auto;
    scrollbar-width: thin;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
    padding-left: 0.75rem;
}

#sidebar::-webkit-scrollbar { width: 4px; }
#sidebar::-webkit-scrollbar-thumb { background: #ccc; border-radius: 2px; }

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

/* Shared section card style */
.panel {
    background: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 0.6rem 0.75rem;
}

.panel h2 {
    font-size: 0.72rem;
    margin-bottom: 0.35rem;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

/* ---- Controls ---- */
#btn-group { display: flex; gap: 0.25rem; margin-bottom: 0.35rem; }
#btn-group button {
    flex: 1;
    padding: 0.25rem 0;
    border: 1px solid #ccc;
    border-radius: 3px;
    background: white;
    cursor: pointer;
    font-size: 0.75rem;
}
#btn-group button:hover { background: #f0f0f0; }

#speed-control { font-size: 0.8rem; color: #555; }
#speed-control label { display: flex; align-items: center; gap: 0.3rem; }
#speed-slider { flex: 1; margin: 0; }

/* ---- Overlay toggles (inline) ---- */
.overlay-toggles {
    display: flex;
    flex-wrap: wrap;
    gap: 0.15rem 0.6rem;
}

.toggle-label {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.75rem;
    cursor: pointer;
    color: #555;
}
.toggle-label input { cursor: pointer; }

/* ---- Drives + Agent merged panel ---- */
.drives-agent-row {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
}

.drives-col {
    flex: 1;
    min-width: 0;
}

.agent-col {
    flex-shrink: 0;
    border-left: 1px solid #eee;
    padding-left: 0.6rem;
}

.agent-col p {
    font-size: 0.75rem;
    color: #555;
    margin-bottom: 0.15rem;
    white-space: nowrap;
}
.agent-col span {
    font-family: monospace;
    color: #333;
}

.drive-bar { display: flex; align-items: center; gap: 0.3rem; margin-bottom: 0.25rem; }
.drive-bar label { width: 58px; font-size: 0.7rem; color: #555; flex-shrink: 0; }
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

/* ---- Perceptions ---- */
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

#perception-list {}

.perception-item {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    margin-bottom: 0.1rem;
    line-height: 1.3;
}
.perception-item .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
}
.perception-item .type-label { flex: 1; color: #555; }
.perception-item .intensity { font-family: monospace; width: 28px; text-align: right; color: #333; }
.perception-item .distance { font-family: monospace; width: 32px; text-align: right; color: #aaa; }

.empty-state { font-style: italic; color: #bbb; font-size: 0.75rem; }

/* ---- Memory / Deliberation merged panel ---- */
#memory-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 0.1rem 0.5rem; }
#memory-stats p { font-size: 0.75rem; color: #555; }
#memory-stats span { font-family: monospace; color: #333; }

.panel-divider {
    height: 1px;
    background: #eee;
    margin: 0.4rem 0;
}

/* ---- VTE deliberation ---- */
.vte-header {
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    margin-bottom: 0.2rem;
    text-align: center;
}
.vte-decided { background: #E8F5E9; color: #2E7D32; }
.vte-deliberating { background: #F3E5F5; color: #7B1FA2; }
.vte-hesitating { background: #FFF3E0; color: #E65100; }

.vte-candidate {
    display: flex;
    align-items: center;
    gap: 0.2rem;
    font-size: 0.7rem;
    margin-bottom: 0.1rem;
}
.vte-candidate.chosen { font-weight: 600; }
.vte-candidate .dir-label { width: 32px; font-family: monospace; font-size: 0.65rem; }
.vte-candidate .bar-bg { flex: 1; height: 6px; }
.vte-candidate .vte-bar { background: #7C4DFF; }
.vte-candidate.chosen .vte-bar { background: #E040FB; }
.vte-candidate .vte-val { width: 36px; font-family: monospace; font-size: 0.65rem; text-align: right; color: #888; }

/* ---- Inline help (details/summary) ---- */
.panel-help {
    margin-top: 0.35rem;
    border-top: 1px solid #eee;
    padding-top: 0.25rem;
}

.panel-help summary {
    font-size: 0.65rem;
    color: #bbb;
    cursor: pointer;
    user-select: none;
    list-style: none;
    text-align: right;
}
.panel-help summary::-webkit-details-marker { display: none; }
.panel-help summary::before { content: ""; }
.panel-help[open] summary { color: #999; margin-bottom: 0.25rem; }

.panel-help dl { margin: 0; }
.panel-help dt {
    font-size: 0.68rem;
    font-weight: 600;
    color: #555;
    margin-top: 0.2rem;
}
.panel-help dt:first-child { margin-top: 0; }
.panel-help dd {
    font-size: 0.68rem;
    color: #999;
    line-height: 1.3;
    margin-left: 0;
}

/* ---- Responsive ---- */
@media (max-width: 1200px) {
    main {
        grid-template-columns: 1fr;
        grid-template-areas:
            "canvas"
            "toolbar"
            "sidebar"
            "charts";
    }
    #sidebar {
        max-height: none;
        padding-left: 0;
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
    #charts-area {
        flex-direction: column;
    }
}

@media (max-width: 600px) {
    #app { padding: 0.5rem; }
    header h1 { font-size: 0.85rem; }
    .panel h2 { font-size: 0.6rem; }
}
```

**Step 2: Verify the layout**

Run: `uv run python -m tolmans_sowbug_playground serve --config configs/sowbug_basic.yaml`

Open browser to `http://localhost:8000`. Verify:
- Canvas takes ~70% width, sidebar ~30%
- Sidebar has three tier groups (Controls, Status, Reference)
- Charts are side by side below the toolbar
- Overlays are inline/wrapped
- Drives and Agent info share one panel with bars left, pos/dir right
- Memory and VTE share one panel with divider between them
- Sidebar scrolls independently when content overflows

**Step 3: Commit**

```bash
git add src/tolmans_sowbug_playground/web/static/style.css
git commit -m "feat(ui): CSS grid layout with merged panels and side-by-side charts"
```

---

### Task 3: Update JavaScript DOM References

**Files:**
- Modify: `src/tolmans_sowbug_playground/web/static/main.js`

The HTML restructure removed some wrapper elements (`#env-column`, `#monitoring`, `#info`, separate `#drives`, `#memory`, `#vte-section` panels). The JS references to elements by ID are mostly unchanged (bars, spans, etc. kept their IDs), but we need to verify no broken references exist.

**Step 1: Audit and fix JS references**

The following DOM IDs remain unchanged and need no JS updates:
- `grid-canvas`, `grid-container`
- `btn-play`, `btn-pause`, `btn-step`, `btn-reset`, `speed-slider`, `speed-val`
- `preset-select`, `grid-width`, `grid-height`, `btn-regenerate`, `btn-save-preset`
- `stim-type`, `place-section`, `edit-hint`
- `toggle-cogmap`, `toggle-perception`, `toggle-density`, `toggle-vte`, `toggle-legend`
- `bar-hunger`, `bar-thirst`, `bar-temperature`, `val-hunger`, `val-thirst`, `val-temperature`
- `agent-pos`, `agent-orient`
- `perc-food`, `perc-water`, `perc-light`, `perc-heat`, `perc-obstacle` (and `-dist` variants)
- `mem-locations`, `mem-edges`, `mem-visited`, `mem-strength`, `mem-density-peak`
- `vte-status`
- `drive-chart-canvas`, `coverage-chart-canvas`
- `a11y-live`

All IDs are preserved in the new HTML. No JS changes are needed for DOM references.

**Step 2: Verify full functionality**

Run: `uv run python -m tolmans_sowbug_playground serve --config configs/sowbug_basic.yaml`

Open browser and test:
1. Click Play — simulation runs, drive bars update, charts draw, perceptions update
2. Click Pause — simulation stops, canvas is editable
3. Left-click canvas — places stimulus
4. Right-click canvas — removes stimulus
5. Hover over charts — tooltips appear
6. Toggle overlay checkboxes — canvas overlays toggle
7. Speed slider works
8. Step button advances one tick
9. Reset button resets simulation
10. VTE section updates when agent deliberates
11. Memory stats update as agent explores
12. Resize browser window — responsive breakpoints work

**Step 3: Commit (only if JS changes were needed)**

If any JS fixes were required:
```bash
git add src/tolmans_sowbug_playground/web/static/main.js
git commit -m "fix(ui): update JS DOM references for new layout structure"
```

---

### Task 4: Run Existing Tests

**Files:** None (verification only)

**Step 1: Run the full test suite**

Run: `uv run python -m pytest -v`

Expected: All 91 tests pass. The layout changes are purely frontend (HTML/CSS/JS) and should not affect any Python backend tests.

**Step 2: Commit all changes together if not yet committed**

If any files have uncommitted changes:
```bash
git add -A
git commit -m "feat(ui): complete layout restructure with grid areas and merged panels"
```
