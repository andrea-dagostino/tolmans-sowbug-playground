# UI Improvements Design

**Date:** 2026-03-01
**Approach:** In-place edits to existing HTML/CSS/JS. No new dependencies.

---

## 1. Drive Bar Urgency Coloring + Thresholds

- Bars transition color based on value: green (0-0.3), yellow (0.3-0.6), orange (0.6-0.8), red (0.8-1.0)
- Threshold tick mark at 0.8 on each bar (danger zone indicator)
- Numeric value text color matches urgency
- Replaces static `.hunger`/`.thirst`/`.temperature` CSS classes with dynamic inline background
- CSS transition on background-color added

## 2. Chart Hover Tooltips + Event Annotations

- Both charts: vertical crosshair line follows mouse cursor
- Floating tooltip (rendered on canvas) shows exact tick and values at cursor position
- `mousemove`/`mouseleave` event listeners on chart canvases
- Event annotations: `eventLog` array tracks key moments client-side:
  - Drive drops sharply = resource found
  - VTE state changes (first deliberation)
- Events rendered as thin vertical dashed lines with rotated text labels
- Pure canvas implementation, no HTML overlay

## 3. Canvas Legend + Resource Icons

- Unicode icons on resource tiles: food=leaf, water=droplet, light=sun, heat=flame, obstacle=square
- Drawn via `ctx.fillText()` centered in each cell after the colored square fill
- Floating legend in top-right corner of canvas (semi-transparent white box with colored swatches + labels)
- `renderLegend()` function called at end of `render()`
- Toggleable via checkbox in Overlays panel

## 4. Sidebar Grouping + Panel Tooltips

- Two visual groups with dividers:
  - **Controls group:** Controls, Overlays
  - **Status group:** Drives, Perceptions, Memory, Deliberation, Agent
- Wrapped in `<div class="sidebar-group">` with label and CSS accent
- Perception panel: column header row "Type | Intensity | Distance"
- Memory labels expanded: "Avg str" -> "Avg strength", "Density pk" -> "Density peak"
- `title` attributes on abbreviated/technical labels

## 5. Toolbar Separation

- Two `<div class="toolbar-section">` groups within the toolbar:
  - **Left: Map Settings** -- Preset, W/H, Regenerate, Save
  - **Right: Place Objects** -- Stimulus type dropdown, mode indicator
- Status badge: "Pause to edit" hint when simulation is running
- `.editing-disabled` class toggled based on running state

## 6. Visual Polish Pass

- **Typography:** 14px body, 12px labels, 16px panel headers, 11px help text
- **Spacing:** Panel padding 0.6rem 0.75rem, 0.15rem more gap between sidebar panels
- **Unified color palette:**
  - Food green: #4CAF50
  - Water blue: #2196F3
  - Heat red: #F44336
  - Agent orange: #FF9800
  - Cognitive purple: #7C4DFF
  - Neutral gray: #78909C
- **Agent glow:** Pulsing outer ring at 1.5x radius, 15% opacity, breathing animation
- **Charts:** Line width 2px, dashed temperature line (colorblind), legend text 10px

## 7. Responsiveness + Accessibility

- **Responsive:** Below 1200px sidebar stacks below canvas. Below 900px panels become accordion. Min width 600px
- **ARIA:** `role`/`aria-label` on all interactive elements. Drive bars get `role="progressbar"` with value attributes
- **Color a11y:** Dash patterns on chart lines (solid hunger, dashed thirst, dotted temperature). Legend includes shape indicators
- **Keyboard:** Space for play/pause (when canvas not focused)
- **Screen reader:** Chart canvases get `aria-label`. Hidden live region updated every ~5 ticks with summary

---

## Files Modified

- `src/tolmans_sowbug_playground/web/static/index.html` -- HTML structure changes (sidebar groups, toolbar sections, ARIA, perception headers)
- `src/tolmans_sowbug_playground/web/static/style.css` -- Typography, spacing, urgency colors, responsive breakpoints, group styles
- `src/tolmans_sowbug_playground/web/static/main.js` -- Chart interactivity, legend rendering, urgency coloring logic, event tracking, agent glow, a11y updates
