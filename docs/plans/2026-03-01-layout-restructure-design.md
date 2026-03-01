# Layout Restructure Design

## Goal

Restructure the web UI layout to give the canvas ~70% width, organize sidebar panels into tiered groups, merge Drives+Agent and Memory+Deliberation panels, and place charts side by side.

## Proposed Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Sowbug Simulation                              Tick: 106  [⚙] │
├─────────────────────────────────┬───────────────────────────────┤
│                                 │ CONTROLS                      │
│                                 │ [▶] [⏸] [⏭] [⟲]   ⏩ 5 tps  │
│                                 ├───────────────────────────────┤
│                                 │ DRIVES + AGENT                │
│      CANVAS (~70% width)        │ Hunger ██████░ .76  Pos:10,10│
│                                 │ Thirst █████░░ .65  Dir: N   │
│      [floating legend]          │ Temp   █████░░ .53           │
│                                 ├───────────────────────────────┤
│                                 │ OVERLAYS  ☑☑☑☑              │
├─────────────────────────────────┼───────────────────────────────┤
│  TOOLBAR                        │ PERCEPTIONS                   │
│ Map: [W][H][Regen][Save]        │  Type | Intensity | Dist      │
│ Place: [Food ▾] L/R-click hint  │  light   88%        1.0      │
├─────────────────────────────────┼───────────────────────────────┤
│                                 │ MEMORY / DELIBERATION         │
│  CHARTS (side by side)          │  Locations: 2  Edges: 81     │
│  ┌──────────┬──────────┐       │  Visited: 55                  │
│  │ Drives   │ Predict. │       │  VTE: Idle                    │
│  │ over Time│ Accuracy │       │                               │
│  └──────────┴──────────┘       │                               │
└─────────────────────────────────┴───────────────────────────────┘
```

## Architecture: CSS Grid with Named Areas

### HTML Structure

`<main>` gets four direct children:

```html
<main>
  <div id="canvas-area">    <!-- canvas + grid-container -->
  <div id="toolbar-area">   <!-- env-toolbar (Map + Place) -->
  <div id="charts-area">    <!-- side-by-side charts -->
  <aside id="sidebar">      <!-- all sidebar panels -->
</main>
```

### CSS Grid Template

```css
main {
  grid-template-columns: 7fr 3fr;
  grid-template-rows: 1fr auto auto;
  grid-template-areas:
    "canvas  sidebar"
    "toolbar sidebar"
    "charts  sidebar";
}
```

## Sidebar Organization (3 Tiers)

### Tier 1 — Interactive
- **Controls:** Play/Pause/Step/Reset buttons + speed slider
- **Overlays:** Checkboxes rendered inline with `flex-wrap: wrap`

### Tier 2 — Live Status
- **Drives + Agent (merged):** Drive bars on left (~65%), agent position/direction on right (~35%) using flex row

### Tier 3 — Reference
- **Perceptions:** Table with Type/Intensity/Distance columns
- **Memory / Deliberation (merged):** Memory stats grid on top, thin divider, VTE status below

## Scroll Behavior

Sidebar scrolls independently with `overflow-y: auto` and `max-height: calc(100vh - header height)`. Canvas/toolbar/charts scroll with the main page.

## Panel Merges

### Drives + Agent
Flex row layout:
- Left: Three drive bars (Hunger/Thirst/Temperature) with bar-fill + threshold marker
- Right: Compact monospace display of Position and Direction

### Memory + Deliberation
Single panel titled "Memory / Deliberation":
- Top section: Memory stats grid (Locations, Edges, Visited, Avg strength, Density peak)
- Thin divider
- Bottom section: VTE status (decided/deliberating/hesitating + candidate bars)

## Charts Side by Side

Charts container uses `display: flex; gap: 0.75rem` with each chart at `flex: 1`. Both Drives-over-Time and Prediction Accuracy are visible simultaneously. Existing hover tooltip logic preserved.

## Responsive Breakpoints

- `> 1200px`: Full proposed layout (grid areas)
- `900–1200px`: Sidebar collapses below canvas/toolbar/charts (single column)
- `< 900px`: Everything stacks vertically, charts stack vertically

## Files Changed

1. `web/static/index.html` — restructure into new grid areas, merge panels
2. `web/static/style.css` — grid layout, merged panel styles, side-by-side charts, responsive
3. `web/static/main.js` — update DOM references for merged panels
