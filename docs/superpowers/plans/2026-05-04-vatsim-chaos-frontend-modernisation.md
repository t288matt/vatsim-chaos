# VATSIM-Chaos Frontend Modernisation — Corrected Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernise the VATSIM-Chaos frontend from vanilla JS/CSS to TypeScript + Vite with professional UI/UX, WCAG 2.1 AA accessibility, and automated testing — while keeping the Flask backend and Docker setup unchanged.

**Architecture:** Concern-by-concern rollout — complete all accessibility work across the whole app, then all styling, then state management, then TypeScript migration. Each concern is fully applied before moving to the next. `src/` lives at the repo root; Vite outputs to `web/static/dist/`. Flask serves the built assets in prod, proxies to Vite dev server in dev.

**Tech Stack:** Vite 5.x, TypeScript 5.x (strict), Vitest + Playwright, ESLint + Prettier, CSS Variables, custom EventBus, Flask (unchanged), Docker multi-stage (Node build stage + existing Python stage)

---

## Decisions Confirmed (Gap Resolution)

| Gap | Decision |
|-----|----------|
| Phase structure | **Concern-by-concern** (accessibility → styling → state → TypeScript → testing → polish) |
| `src/` location | **Repo root** — `VATSIM-Chaos/src/`, `package.json` at root |
| Progress updates | **Keep polling** — no SSE migration, `/status` polling unchanged |
| Cesium scope | **Out of scope** — iframe stays as-is; Cesium modernisation is a future Phase 2 project |
| Visual regression | **Playwright** visual comparisons (automated, runs in CI) |
| Existing tests | **Delete them** — `test_green_logic.js` and `web/test_same_routes.py` don't work; start fresh |
| API contract | **Standardise Flask response format first** before writing `src/types/api.ts` |
| Flask template | Dev: proxy to Vite via `FLASK_ENV=development`; Prod: serve `web/static/dist/index.html` as static file |

---

## Known Backend Issues (Out of Scope — Track for Later)

- **`web/app.py:491`** — `os.chdir()` inside a daemon thread changes the process-level working directory for all threads. No concurrent processing is possible anyway (guarded by `is_processing`), but any route handler that resolves relative paths during processing could break. Fix: pass absolute paths to subprocess calls instead.
- **`web/app.py:130`** — `os.statvfs()` is POSIX-only; raises `AttributeError` on Windows. The `except` block silently returns `True`. Anyone developing on Windows (not in Docker) will get upload errors. Fix: use `shutil.disk_usage()` instead.

---

## File Structure

```
VATSIM-Chaos/
├── package.json              # NEW — root-level, Vite/Node deps
├── vite.config.ts            # NEW — outputs to web/static/dist/
├── tsconfig.json             # NEW — strict mode
├── .eslintrc.json            # NEW
├── .prettierrc               # NEW
├── playwright.config.ts      # NEW — visual regression
├── vitest.config.ts          # NEW
├── src/                      # NEW — all TypeScript source
│   ├── index.ts              # entry point
│   ├── types/
│   │   └── api.ts            # typed Flask API shapes (after standardisation)
│   ├── modules/
│   │   ├── eventBus.ts       # pub-sub
│   │   ├── fileManager.ts    # migrated from web/static/js/fileManager.js
│   │   ├── processor.ts      # migrated from web/static/js/processor.js
│   │   ├── mapViewer.ts      # migrated from web/static/js/mapViewer.js
│   │   ├── app.ts            # migrated from web/static/js/app.js
│   │   └── modal.ts          # NEW — accessible modal component
│   ├── utils/
│   │   ├── validation.ts     # extracted testable logic
│   │   └── errorHandler.ts   # centralised error handling
│   └── styles/
│       ├── _variables.css    # CSS custom properties
│       └── _components.css   # component library
├── src/__tests__/
│   ├── modules/
│   │   ├── fileManager.test.ts
│   │   └── processor.test.ts
│   └── integration/
│       └── workflow.test.ts
├── tests/visual/             # Playwright visual regression screenshots
├── web/
│   ├── app.py                # MODIFY — add Vite dev proxy + dist/ serving
│   ├── templates/
│   │   └── index.html        # MODIFY — ARIA labels, semantic HTML
│   └── static/
│       ├── js/               # OLD FILES — delete after Phase 5 cutover
│       │   ├── app.js        → replaced by src/modules/app.ts
│       │   ├── fileManager.js → replaced by src/modules/fileManager.ts
│       │   ├── processor.js  → replaced by src/modules/processor.ts
│       │   └── mapViewer.js  → replaced by src/modules/mapViewer.ts
│       ├── css/
│       │   └── main.css      # OLD — delete after Phase 3 cutover
│       └── dist/             # NEW — Vite build output (gitignored)
├── Dockerfile                # MODIFY — add Node.js build stage
└── .gitignore                # MODIFY — add dist/, node_modules/, coverage/
```

---

## Phase 1: Tooling & Project Setup

**Critical files:**
- Create: `package.json`, `vite.config.ts`, `tsconfig.json`, `.eslintrc.json`, `.prettierrc`, `vitest.config.ts`, `playwright.config.ts`, `src/index.ts`
- Modify: `Dockerfile`, `web/app.py`, `.gitignore`
- Delete: `test_green_logic.js`, `web/test_same_routes.py` (broken, replaced later)

### Task 1.1: Initialise Node.js project

- [ ] **Step 1: Create `package.json` at repo root**

```json
{
  "name": "vatsim-chaos",
  "private": true,
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "test:visual": "playwright test",
    "type-check": "tsc --noEmit",
    "lint": "eslint src --ext .ts,.tsx",
    "format": "prettier --write src/"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "typescript": "^5.0.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "eslint": "^8.0.0",
    "prettier": "^3.0.0",
    "vitest": "^1.0.0",
    "@vitest/coverage-v8": "^1.0.0",
    "@testing-library/dom": "^9.0.0",
    "@playwright/test": "^1.40.0"
  }
}
```

- [ ] **Step 2: Run `npm install` and verify lockfile created**

```bash
npm install
# Expected: node_modules/ created, package-lock.json created
```

- [ ] **Step 3: Create `vite.config.ts` at repo root**

```typescript
import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: resolve(__dirname, 'src'),
  build: {
    outDir: resolve(__dirname, 'web/static/dist'),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/upload': 'http://localhost:5000',
      '/files': 'http://localhost:5000',
      '/delete-file': 'http://localhost:5000',
      '/delete-all-files': 'http://localhost:5000',
      '/validate': 'http://localhost:5000',
      '/validate-same-routes': 'http://localhost:5000',
      '/process': 'http://localhost:5000',
      '/status': 'http://localhost:5000',
      '/briefing': 'http://localhost:5000',
      '/animation': 'http://localhost:5000',
    },
  },
});
```

- [ ] **Step 4: Create `tsconfig.json` at repo root**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "outDir": "./web/static/dist",
    "rootDir": "./src",
    "declaration": false,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "web/static/dist"]
}
```

- [ ] **Step 5: Create `src/index.ts` (stub entry point)**

```typescript
// Application entry point — modules wired up in Phase 5
console.log('VATSIM-Chaos initialising');
```

- [ ] **Step 6: Verify `npm run build` produces output**

```bash
npm run build
# Expected: web/static/dist/assets/*.js and *.css created
ls web/static/dist/
```

- [ ] **Step 7: Verify `npm run dev` starts Vite**

```bash
npm run dev
# Expected: Vite dev server on http://localhost:5173
```

- [ ] **Step 8: Delete broken test files**

```bash
rm test_green_logic.js
rm web/test_same_routes.py
```

- [ ] **Step 9: Commit**

```bash
git add package.json package-lock.json vite.config.ts tsconfig.json src/
git add .gitignore  # after adding dist/, node_modules/, coverage/
git commit -m "feat: add Vite + TypeScript tooling setup"
```

### Task 1.2: Flask integration for dev/prod asset serving

- [ ] **Step 1: Write failing test (verify Flask serves Vite output in prod)**

Create `web/test_asset_serving.py`:
```python
import os, pytest
os.environ['FLASK_ENV'] = 'production'
os.makedirs('web/static/dist', exist_ok=True)
with open('web/static/dist/index.html', 'w') as f:
    f.write('<html><body>test</body></html>')

from web.app import app

def test_prod_serves_dist_index():
    client = app.test_client()
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'test' in resp.data
```

Run: `pytest web/test_asset_serving.py -v`
Expected: **FAIL** — Flask still calls `render_template('index.html')`

- [ ] **Step 2: Update `web/app.py` route to serve from `dist/` in prod**

Replace the `index()` route at `web/app.py:52`:
```python
import os as _os

@app.route('/')
def index():
    if _os.environ.get('FLASK_ENV') == 'development':
        # In dev, Vite serves index.html at localhost:5173
        # Flask only handles API routes; this shouldn't be hit directly
        return 'Start Vite dev server and access http://localhost:5173', 200
    dist_index = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
        'web', 'static', 'dist', 'index.html'
    )
    if _os.path.exists(dist_index):
        return send_file(dist_index)
    return render_template('index.html')  # fallback during transition
```

- [ ] **Step 3: Run test — verify it passes**

```bash
pytest web/test_asset_serving.py -v
# Expected: PASS
```

- [ ] **Step 4: Update `.gitignore`**

Add to `.gitignore`:
```
node_modules/
web/static/dist/
coverage/
playwright-report/
test-results/
```

- [ ] **Step 5: Commit**

```bash
git add web/app.py .gitignore
git commit -m "feat: Flask serves Vite dist in production"
```

### Task 1.3: Docker multi-stage build with Node

- [ ] **Step 1: Update `Dockerfile` to add Node build stage**

Prepend to existing `Dockerfile`:
```dockerfile
# Stage 1: Build frontend assets
FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY vite.config.ts tsconfig.json ./
COPY src/ ./src/
RUN npm run build
# Output: /app/web/static/dist/

# Stage 2: Python application (existing)
FROM python:3.11-slim AS app
# ... existing Dockerfile content continues here ...
# Add this COPY before the CMD:
COPY --from=frontend-builder /app/web/static/dist/ /app/web/static/dist/
```

- [ ] **Step 2: Verify Docker build succeeds**

```bash
docker build -t vatsim-chaos-test .
# Expected: Build completes without errors
```

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "feat: Docker multi-stage build with Node frontend"
```

---

## Phase 2: Accessibility & Modern UX (Concern-by-concern across all components)

**Critical files:**
- Modify: `web/templates/index.html` — ARIA labels, semantic markup, focus trap
- Create: `src/styles/_variables.css`, `src/modules/modal.ts` (stub for future TS migration)

### Task 2.1: Replace emoji icons with ARIA-labelled SVG equivalents

- [ ] **Step 1: Run axe DevTools audit on current `index.html`**

Open http://localhost:5000, run axe browser extension. Note all violations.
Expected: Multiple violations (emoji as icons, missing labels, etc.)

- [ ] **Step 2: Replace emoji icons in `web/templates/index.html`**

For each emoji icon (🎯, 📂, etc.), replace with pattern:
```html
<!-- Before -->
🎯 Flight Conflict Generation

<!-- After -->
<svg aria-hidden="true" focusable="false" width="20" height="20">
  <use href="#icon-target"/>
</svg>
<span>Flight Conflict Generation</span>
```

Add SVG sprite sheet at bottom of `<body>`:
```html
<svg xmlns="http://www.w3.org/2000/svg" style="display:none">
  <symbol id="icon-target" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
  </symbol>
  <!-- Add remaining icons: upload, file, check, x, alert, play, etc. -->
</svg>
```

- [ ] **Step 3: Add ARIA labels to all form inputs**

```html
<!-- Before -->
<input type="time" id="startTime">

<!-- After -->
<label for="startTime">Event Start Time</label>
<input type="time" id="startTime" aria-describedby="startTime-hint">
<span id="startTime-hint" class="sr-only">Format: HH:MM in 24-hour time</span>
```

- [ ] **Step 4: Add `aria-live` regions for dynamic content**

```html
<!-- Status messages area -->
<div id="uploadStatus" aria-live="polite" aria-atomic="true"></div>
<div id="processingStatus" aria-live="assertive" aria-atomic="false"></div>
```

- [ ] **Step 5: Add focus trap to pilot briefing modal**

In `web/static/js/app.js`, find `showBriefing()` and add:
```javascript
// After modal opens, trap focus
const focusableSelectors = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
const modal = document.getElementById('briefingModal');
const focusable = modal.querySelectorAll(focusableSelectors);
const firstFocusable = focusable[0];
const lastFocusable = focusable[focusable.length - 1];
firstFocusable.focus();

modal.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return;
    if (e.shiftKey) {
        if (document.activeElement === firstFocusable) { e.preventDefault(); lastFocusable.focus(); }
    } else {
        if (document.activeElement === lastFocusable) { e.preventDefault(); firstFocusable.focus(); }
    }
});
```

- [ ] **Step 6: Add keyboard navigation for Escape key on modal**

Already in `app.js` — verify `keydown` listener for `Escape` closes modal and restores focus to trigger element.

- [ ] **Step 7: Re-run axe audit — verify 0 violations**

```bash
# Install axe-playwright for automated check
npm install --save-dev axe-playwright @playwright/test
```

Create `tests/visual/accessibility.spec.ts`:
```typescript
import { test, expect } from '@playwright/test';
import { injectAxe, checkA11y } from 'axe-playwright';

test('WCAG 2.1 AA — 0 violations on main page', async ({ page }) => {
    await page.goto('http://localhost:5000');
    await injectAxe(page);
    await checkA11y(page, null, { runOnly: ['wcag2a', 'wcag2aa'] });
});
```

Run: `npx playwright test tests/visual/accessibility.spec.ts`
Expected: **PASS** with 0 violations.

- [ ] **Step 8: Commit**

```bash
git add web/templates/index.html web/static/js/app.js tests/
git commit -m "feat: WCAG 2.1 AA accessibility — SVG icons, ARIA labels, focus management"
```

### Task 2.2: Toast notifications and visual feedback

- [ ] **Step 1: Add toast notification CSS to `web/static/css/main.css`**

```css
.toast-container {
    position: fixed;
    top: 1rem;
    right: 1rem;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.toast {
    padding: 0.75rem 1rem;
    border-radius: 4px;
    color: #fff;
    font-size: 0.875rem;
    max-width: 320px;
    animation: slideIn 250ms ease;
}
.toast--success { background: #10b981; }
.toast--error   { background: #ef4444; }
.toast--warning { background: #f59e0b; }
@keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to   { transform: translateX(0);   opacity: 1; }
}
```

- [ ] **Step 2: Add `showToast()` utility to `web/static/js/app.js`**

```javascript
function showToast(message, type = 'success', duration = 4000) {
    const container = document.getElementById('toastContainer') 
        ?? Object.assign(document.createElement('div'), { 
            id: 'toastContainer', 
            className: 'toast-container',
            role: 'status',
            'aria-live': 'polite'
        });
    if (!container.parentNode) document.body.appendChild(container);
    
    const toast = Object.assign(document.createElement('div'), {
        className: `toast toast--${type}`,
        textContent: message
    });
    container.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
}
window.showToast = showToast;
```

- [ ] **Step 3: Replace `showMessage()` calls in `fileManager.js` with `showToast()`**

Search for `this.showMessage(` in `web/static/js/fileManager.js` and replace each with `showToast(`.

- [ ] **Step 4: Add step-progress indicator to processing section in `index.html`**

```html
<div id="progressSteps" aria-label="Processing progress" class="progress-steps" hidden>
    <div class="progress-step" data-step="0">Extract flight plans</div>
    <div class="progress-step" data-step="1">Analyse conflicts</div>
    <div class="progress-step" data-step="2">Merge KML files</div>
    <div class="progress-step" data-step="3">Schedule conflicts</div>
    <div class="progress-step" data-step="4">Generate animation</div>
    <div class="progress-step" data-step="5">Audit data</div>
</div>
```

- [ ] **Step 5: Update `processor.js` to drive the step indicator**

In `monitorProgress()`, after receiving status response, add:
```javascript
const steps = document.querySelectorAll('.progress-step');
steps.forEach((el, i) => {
    el.classList.toggle('progress-step--done', i < status.current_step);
    el.classList.toggle('progress-step--active', i === status.current_step);
});
```

- [ ] **Step 6: Commit**

```bash
git add web/static/css/main.css web/static/js/app.js web/static/js/fileManager.js web/static/js/processor.js web/templates/index.html
git commit -m "feat: toast notifications and step progress indicator"
```

### Task 2.3: UI component redesign — file upload area

The current upload area is a plain box with minimal feedback. Target state:

- [ ] **Step 1: Redesign upload zone in `index.html`**

```html
<div id="uploadArea" class="upload-zone" role="button" tabindex="0"
     aria-label="Upload XML flight plan files — click or drag and drop">
    <svg class="upload-zone__icon" aria-hidden="true">...</svg>
    <p class="upload-zone__title">Drop XML files here</p>
    <p class="upload-zone__subtitle">or <span class="upload-zone__link">browse</span></p>
    <p class="upload-zone__hint">SimBrief XML · max 16 MB · up to 50 files</p>
</div>
```

- [ ] **Step 2: Add upload zone CSS to `main.css`**

```css
.upload-zone {
    border: 2px dashed var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-6);
    text-align: center;
    cursor: pointer;
    transition: border-color var(--duration-normal) var(--ease-out),
                background var(--duration-normal) var(--ease-out);
}
.upload-zone:hover,
.upload-zone.dragover {
    border-color: var(--color-primary);
    background: rgba(0, 212, 255, 0.05);
}
.upload-zone__icon { color: var(--color-primary); width: 40px; height: 40px; margin-bottom: var(--space-3); }
.upload-zone__title { font-size: var(--font-size-lg); font-weight: var(--font-weight-medium); }
.upload-zone__subtitle { color: var(--color-text-muted); font-size: var(--font-size-sm); }
.upload-zone__link { color: var(--color-primary); text-decoration: underline; }
.upload-zone__hint { color: var(--color-text-muted); font-size: var(--font-size-sm); margin-top: var(--space-2); }
```

- [ ] **Step 3: Redesign file list items with metadata and status badges**

Each file in the library should show: filename, route (origin → destination), file size, upload date, and validation status badge.

Update `fileManager.js` `renderFileList()` method to produce:
```html
<div class="file-item file-item--valid" data-filename="plan.xml">
    <input type="checkbox" id="file-plan.xml" class="file-item__checkbox">
    <label class="file-item__label" for="file-plan.xml">
        <span class="file-item__name">plan.xml</span>
        <span class="file-item__route">YSSY → YMML</span>
        <span class="file-item__meta">2.4 KB · 04-05-2026</span>
    </label>
    <span class="file-item__badge file-item__badge--valid" aria-label="Valid">
        <svg aria-hidden="true"><!-- check icon --></svg>
    </span>
</div>
```

CSS:
```css
.file-item {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    margin-bottom: var(--space-2);
    transition: background var(--duration-fast);
}
.file-item:hover { background: var(--color-surface-2); }
.file-item--selected { border-color: var(--color-primary); background: rgba(0, 212, 255, 0.06); }
.file-item__name { font-weight: var(--font-weight-medium); }
.file-item__route { color: var(--color-primary); font-size: var(--font-size-sm); }
.file-item__meta { color: var(--color-text-muted); font-size: var(--font-size-sm); }
.file-item__badge--valid   { color: var(--color-success); }
.file-item__badge--invalid { color: var(--color-error); }
.file-item__badge--pending { color: var(--color-text-muted); animation: spin 1s linear infinite; }
```

- [ ] **Step 4: Add per-file upload progress bar**

In `fileManager.js`, during `uploadFiles()`, for each file being uploaded show:
```javascript
const progressEl = fileItemEl.querySelector('.file-item__progress');
progressEl.style.width = `${Math.round(progress)}%`;
progressEl.setAttribute('aria-valuenow', Math.round(progress));
```

HTML structure: `<div class="file-item__progress-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"></div>`

- [ ] **Step 5: Commit**

```bash
git add web/templates/index.html web/static/css/main.css web/static/js/fileManager.js
git commit -m "feat: redesigned file upload zone and file library with metadata badges"
```

### Task 2.4: UI component redesign — buttons and controls

- [ ] **Step 1: Define button component variants in `main.css`**

```css
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    min-height: var(--touch-target);
    padding: var(--space-2) var(--space-5);
    border-radius: var(--radius-md);
    font-family: var(--font-family);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    border: none;
    cursor: pointer;
    transition: opacity var(--duration-fast), transform var(--duration-fast);
}
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn:not(:disabled):hover { opacity: 0.88; transform: translateY(-1px); }
.btn:not(:disabled):active { transform: translateY(0); }

.btn--primary  { background: var(--color-primary); color: var(--color-bg); }
.btn--secondary { background: var(--color-surface-2); color: var(--color-text); border: 1px solid var(--color-border); }
.btn--danger   { background: var(--color-error); color: #fff; }
.btn--loading  { position: relative; pointer-events: none; }
.btn--loading::after {
    content: '';
    position: absolute;
    width: 16px; height: 16px;
    border: 2px solid currentColor;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
```

- [ ] **Step 2: Apply `.btn` classes to all buttons in `index.html`**

- Generate Schedule button → `class="btn btn--primary"`
- Pilot Briefing button → `class="btn btn--secondary"`
- Delete All button → `class="btn btn--danger"`
- Select All / Select None → `class="btn btn--secondary btn--sm"`

- [ ] **Step 3: Add loading state to Generate Schedule button**

In `processor.js`, when processing starts:
```javascript
const generateBtn = document.getElementById('generateBtn');
generateBtn.classList.add('btn--loading');
generateBtn.disabled = true;
generateBtn.dataset.originalText = generateBtn.textContent;
generateBtn.textContent = 'Generating…';
// On complete/fail:
generateBtn.classList.remove('btn--loading');
generateBtn.disabled = false;
generateBtn.textContent = generateBtn.dataset.originalText;
```

- [ ] **Step 4: Commit**

```bash
git add web/templates/index.html web/static/css/main.css web/static/js/processor.js
git commit -m "feat: button component system with loading state and hover effects"
```

### Task 2.5: UI component redesign — layout and panels

- [ ] **Step 1: Add consistent spacing and panel hierarchy to `main.css`**

```css
/* Panel sections */
.panel-section {
    padding: var(--space-4) var(--space-5);
    border-bottom: 1px solid var(--color-border);
}
.panel-section:last-child { border-bottom: none; }

.panel-section__title {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-bold);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: var(--space-3);
}

/* Left panel header */
.left-panel__header {
    padding: var(--space-4) var(--space-5);
    background: linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-2) 100%);
    border-bottom: 1px solid var(--color-border);
}

/* File count badge */
.file-count-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    padding: 0 var(--space-1);
    background: var(--color-primary);
    color: var(--color-bg);
    border-radius: 10px;
    font-size: 11px;
    font-weight: var(--font-weight-bold);
}

/* Selection summary bar */
.selection-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-2) var(--space-4);
    background: var(--color-surface-2);
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
}
```

- [ ] **Step 2: Update `index.html` to use panel sections**

Wrap each logical section (Upload, Time Controls, File Library, Actions) in `<div class="panel-section">` with a `<h2 class="panel-section__title">` heading.

- [ ] **Step 3: Add a selection count badge to the "Selected" area**

Show "3 of 12 selected" as a formatted summary in the selection bar, updated dynamically by `fileManager.js`.

- [ ] **Step 4: Add empty state for file library**

When no files are uploaded, show:
```html
<div class="empty-state" id="emptyState">
    <svg aria-hidden="true" class="empty-state__icon"><!-- upload icon --></svg>
    <p class="empty-state__title">No flight plans yet</p>
    <p class="empty-state__body">Upload SimBrief XML files to get started</p>
</div>
```

Toggle `hidden` on this when files exist.

- [ ] **Step 5: Commit**

```bash
git add web/templates/index.html web/static/css/main.css web/static/js/fileManager.js
git commit -m "feat: improved layout hierarchy, empty state, selection summary"
```

### Task 2.6: UI component redesign — processing feedback

- [ ] **Step 1: Replace the vague progress area with a proper step timeline**

Update `index.html` processing section:
```html
<div id="processPanel" class="panel-section" hidden>
    <h2 class="panel-section__title">Processing</h2>
    <div class="step-timeline" aria-label="Processing steps">
        <div class="step-timeline__item" data-step="0">
            <div class="step-timeline__indicator"></div>
            <div class="step-timeline__content">
                <span class="step-timeline__label">Extract flight plans</span>
                <span class="step-timeline__status"></span>
            </div>
        </div>
        <!-- Repeat for steps 1-5: Analyse conflicts, Merge KML, Schedule, Animation, Audit -->
    </div>
    <div class="process-meta">
        <span id="elapsedTime">0s elapsed</span>
    </div>
</div>
```

- [ ] **Step 2: Add step timeline CSS**

```css
.step-timeline { display: flex; flex-direction: column; gap: var(--space-2); }
.step-timeline__item {
    display: flex;
    align-items: flex-start;
    gap: var(--space-3);
    padding: var(--space-2) 0;
    opacity: 0.4;
    transition: opacity var(--duration-normal);
}
.step-timeline__item--done,
.step-timeline__item--active { opacity: 1; }

.step-timeline__indicator {
    width: 20px; height: 20px;
    border-radius: 50%;
    border: 2px solid var(--color-border);
    flex-shrink: 0;
    transition: background var(--duration-normal), border-color var(--duration-normal);
}
.step-timeline__item--done .step-timeline__indicator {
    background: var(--color-success);
    border-color: var(--color-success);
}
.step-timeline__item--active .step-timeline__indicator {
    border-color: var(--color-primary);
    animation: pulse 1s ease infinite;
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(0,212,255,0.4); }
    50% { box-shadow: 0 0 0 6px rgba(0,212,255,0); }
}

.step-timeline__label { font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); }
.step-timeline__status { font-size: var(--font-size-sm); color: var(--color-text-muted); }
.process-meta { margin-top: var(--space-4); color: var(--color-text-muted); font-size: var(--font-size-sm); }
```

- [ ] **Step 3: Update `processor.js` to drive the timeline**

In `monitorProgress()`, update each step item's classes and the elapsed time counter:
```javascript
const elapsed = Math.round((Date.now() - this.processingStartTime) / 1000);
document.getElementById('elapsedTime').textContent = `${elapsed}s elapsed`;

document.querySelectorAll('.step-timeline__item').forEach((el, i) => {
    el.classList.toggle('step-timeline__item--done', i < status.current_step);
    el.classList.toggle('step-timeline__item--active', i === status.current_step);
    const statusEl = el.querySelector('.step-timeline__status');
    if (i < status.current_step) statusEl.textContent = 'Done';
    else if (i === status.current_step) statusEl.textContent = 'Running…';
    else statusEl.textContent = '';
});
```

- [ ] **Step 4: Show process panel when processing starts, hide when done**

```javascript
// On start
document.getElementById('processPanel').hidden = false;
// On complete — show success state, hide panel after 3s delay
setTimeout(() => { document.getElementById('processPanel').hidden = true; }, 3000);
```

- [ ] **Step 5: Commit**

```bash
git add web/templates/index.html web/static/css/main.css web/static/js/processor.js
git commit -m "feat: step timeline for processing feedback with elapsed time"
```

---

## Phase 3: Modern Styling Architecture

**Critical files:**
- Create: `src/styles/_variables.css`, `src/styles/_components.css`
- Modify: `web/static/css/main.css` (refactor to use CSS variables)

### Task 3.1: CSS variables and component system

- [ ] **Step 1: Take baseline Playwright screenshots of current UI**

Create `tests/visual/baseline.spec.ts`:
```typescript
import { test } from '@playwright/test';

test('capture baseline screenshots', async ({ page }) => {
    await page.goto('http://localhost:5000');
    await page.screenshot({ path: 'tests/visual/snapshots/baseline-main.png', fullPage: true });
});
```

Run: `npx playwright test tests/visual/baseline.spec.ts`

- [ ] **Step 2: Create `src/styles/_variables.css`**

```css
:root {
    /* Colours */
    --color-primary:    #00d4ff;
    --color-success:    #10b981;
    --color-error:      #ef4444;
    --color-warning:    #f59e0b;
    --color-bg:         #0f172a;
    --color-surface:    #1e293b;
    --color-surface-2:  #334155;
    --color-text:       #f1f5f9;
    --color-text-muted: #94a3b8;
    --color-border:     #475569;

    /* Spacing */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 20px;
    --space-6: 24px;

    /* Typography */
    --font-family: -apple-system, 'Segoe UI', system-ui, sans-serif;
    --font-size-sm:   0.875rem;
    --font-size-base: 1rem;
    --font-size-lg:   1.125rem;
    --font-size-xl:   1.25rem;
    --font-weight-normal: 400;
    --font-weight-medium: 500;
    --font-weight-bold:   700;

    /* Animations */
    --duration-fast:   150ms;
    --duration-normal: 250ms;
    --duration-slow:   400ms;
    --ease-out: cubic-bezier(0.0, 0.0, 0.2, 1);

    /* Radii */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;

    /* Touch targets */
    --touch-target: 44px;
}
```

- [ ] **Step 3: Refactor `web/static/css/main.css` to use CSS variables**

For every hardcoded colour (e.g., `#00d4ff`, `#1a1a2e`, `rgba(...)`) replace with the corresponding variable. Example:
```css
/* Before */
.btn-primary { background: #00d4ff; color: #0f172a; }

/* After */
.btn-primary { background: var(--color-primary); color: var(--color-bg); }
```

- [ ] **Step 4: Add responsive breakpoints**

At bottom of `main.css`:
```css
/* Mobile: 375px */
@media (max-width: 375px) {
    .main-layout { flex-direction: column; }
    .left-panel, .right-panel { width: 100%; }
}

/* Tablet: 768px */
@media (max-width: 768px) {
    .left-panel { width: 100%; max-width: none; }
    .right-panel { display: none; } /* Map hidden on mobile */
}

/* Touch targets */
button, .clickable { min-height: var(--touch-target); }
```

- [ ] **Step 5: Run visual regression — compare against baseline**

Create `tests/visual/regression.spec.ts`:
```typescript
import { test, expect } from '@playwright/test';

test('no visual regression after CSS variables', async ({ page }) => {
    await page.goto('http://localhost:5000');
    await expect(page).toHaveScreenshot('main-after-variables.png', {
        maxDiffPixelRatio: 0.02  // 2% difference tolerance
    });
});
```

Run: `npx playwright test tests/visual/regression.spec.ts`
Expected: Visual diff within tolerance.

- [ ] **Step 6: Commit**

```bash
git add src/styles/ web/static/css/main.css tests/visual/
git commit -m "feat: CSS variables, responsive breakpoints, visual regression baseline"
```

---

## Phase 4: State Management & Events (EventBus in vanilla JS)

**Critical files:**
- Create: `src/modules/eventBus.ts` (TypeScript stub — compiled to JS via Vite, or written as plain JS initially)
- Modify: `web/static/js/app.js`, `fileManager.js`, `processor.js`, `mapViewer.js`

> Note: EventBus is written in TypeScript in `src/` but since Phase 5 handles full migration, this phase can write it as plain JS in `web/static/js/eventBus.js` as a stepping stone. Decide before starting.

### Task 4.1: Build EventBus utility

- [ ] **Step 1: Write Vitest test for EventBus**

Create `src/__tests__/modules/eventBus.test.ts`:
```typescript
import { describe, it, expect, vi } from 'vitest';
import { EventBus } from '../../modules/eventBus';

describe('EventBus', () => {
    it('calls listener on emit', () => {
        const bus = new EventBus();
        const fn = vi.fn();
        bus.on('test', fn);
        bus.emit('test', { value: 42 });
        expect(fn).toHaveBeenCalledWith({ value: 42 });
    });

    it('does not call unsubscribed listener', () => {
        const bus = new EventBus();
        const fn = vi.fn();
        const off = bus.on('test', fn);
        off();
        bus.emit('test', {});
        expect(fn).not.toHaveBeenCalled();
    });

    it('handles multiple listeners for same event', () => {
        const bus = new EventBus();
        const fn1 = vi.fn(), fn2 = vi.fn();
        bus.on('test', fn1);
        bus.on('test', fn2);
        bus.emit('test', {});
        expect(fn1).toHaveBeenCalledOnce();
        expect(fn2).toHaveBeenCalledOnce();
    });
});
```

Run: `npm run test`
Expected: **FAIL** — EventBus not yet implemented.

- [ ] **Step 2: Implement `src/modules/eventBus.ts`**

```typescript
type Listener<T = unknown> = (payload: T) => void;

export class EventBus {
    private listeners = new Map<string, Set<Listener>>();

    on<T>(event: string, listener: Listener<T>): () => void {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event)!.add(listener as Listener);
        return () => this.listeners.get(event)?.delete(listener as Listener);
    }

    emit<T>(event: string, payload: T): void {
        this.listeners.get(event)?.forEach(fn => fn(payload));
    }
}

export const bus = new EventBus();
```

- [ ] **Step 3: Run tests — verify EventBus tests pass**

```bash
npm run test
# Expected: All 3 EventBus tests pass
```

- [ ] **Step 4: Commit**

```bash
git add src/modules/eventBus.ts src/__tests__/
git commit -m "feat: EventBus pub-sub with full test coverage"
```

---

## Phase 5: API Standardisation + TypeScript Migration

### Task 5.1: Standardise Flask API response format (prerequisite for TypeScript types)

**Standard envelope:**
```json
{ "ok": true, "data": {...} }
{ "ok": false, "error": "Human-readable message" }
```

- [ ] **Step 1: Write tests for each endpoint's new response shape**

Create `web/test_api_responses.py`:
```python
import pytest, json
from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    return flask_app.test_client()

def test_upload_success_envelope(client):
    # POST /upload with no files → ok: false
    resp = client.post('/upload')
    data = json.loads(resp.data)
    assert 'ok' in data
    assert data['ok'] == False
    assert 'error' in data

def test_validate_success_envelope(client):
    # GET /validate/nonexistent → ok: false
    resp = client.get('/validate/nonexistent.xml')
    data = json.loads(resp.data)
    assert 'ok' in data
    assert data['ok'] == False
```

Run: `pytest web/test_api_responses.py -v`
Expected: **FAIL**

- [ ] **Step 2: Add response helper to `web/app.py`**

```python
def api_ok(data):
    return jsonify({'ok': True, 'data': data})

def api_error(message, status=400):
    return jsonify({'ok': False, 'error': message}), status
```

- [ ] **Step 3: Update all Flask endpoints to use the envelope**

Replace all `jsonify({'error': ...})` → `api_error(...)` and `jsonify({...data...})` → `api_ok({...data...})` across `web/app.py`.

- [ ] **Step 4: Run API tests — verify they pass**

```bash
pytest web/test_api_responses.py -v
# Expected: All pass
```

- [ ] **Step 5: Update JavaScript callers to handle `data.ok` / `data.data`**

In `fileManager.js`, `processor.js`, and `app.js`, find all `fetch()` call response handlers and update:
```javascript
// Before
const data = await resp.json();
if (data.error) { ... }

// After
const body = await resp.json();
if (!body.ok) { showToast(body.error, 'error'); return; }
const data = body.data;
```

- [ ] **Step 6: Commit**

```bash
git add web/app.py web/test_api_responses.py web/static/js/
git commit -m "feat: standardise Flask API response envelope {ok, data/error}"
```

### Task 5.2: TypeScript migration — FileManager

- [ ] **Step 1: Write Vitest tests for FileManager business logic**

Create `src/__tests__/modules/fileManager.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';
import { formatFileSize, isValidXmlFilename } from '../../modules/fileManager';

describe('FileManager utilities', () => {
    it('formats bytes correctly', () => {
        expect(formatFileSize(1024)).toBe('1.0 KB');
        expect(formatFileSize(1048576)).toBe('1.0 MB');
        expect(formatFileSize(512)).toBe('512 B');
    });

    it('validates XML filenames', () => {
        expect(isValidXmlFilename('plan.xml')).toBe(true);
        expect(isValidXmlFilename('plan.txt')).toBe(false);
        expect(isValidXmlFilename('')).toBe(false);
    });
});
```

Run: `npm run test`
Expected: **FAIL** — functions not yet in TypeScript.

- [ ] **Step 2: Create `src/types/api.ts` with standardised shapes**

```typescript
export interface ApiOk<T> { ok: true; data: T }
export interface ApiError { ok: false; error: string }
export type ApiResponse<T> = ApiOk<T> | ApiError;

export interface FileInfo {
    id: string;
    name: string;
    size: number;
    upload_date: number;
}

export interface ValidationResult {
    valid: boolean;
    flight_count: number;
    flights: Array<{
        origin: string;
        destination: string;
        aircraft_type: string;
        waypoint_count: number;
    }>;
}

export interface ProcessingStatus {
    is_processing: boolean;
    current_step: number;
    total_steps: number;
    completed: boolean;
    failed: boolean;
    error: string | null;
    start_time: string | null;
    end_time: string | null;
}
```

- [ ] **Step 3: Create `src/modules/fileManager.ts`**

Migrate `web/static/js/fileManager.js` to TypeScript. Export utility functions used in tests. Keep full feature parity. Key changes:
- Replace `this.showMessage(...)` → `showToast(...)` (imported from app module)
- Use `ApiResponse<FileInfo[]>` for `/files` response typing
- Replace `window.app` references with EventBus events

- [ ] **Step 4: Run tests — verify they pass**

```bash
npm run test
npm run type-check
# Expected: All tests pass, 0 TypeScript errors
```

- [ ] **Step 5: Wire TypeScript FileManager into `src/index.ts`**

```typescript
import { FileManager } from './modules/fileManager';
const fileManager = new FileManager();
```

- [ ] **Step 6: Build and verify in browser**

```bash
npm run build
# Start Flask: cd web && FLASK_ENV=production python app.py
# Open http://localhost:5000 — verify file upload/management works
```

- [ ] **Step 7: Delete old `web/static/js/fileManager.js`**

```bash
rm web/static/js/fileManager.js
```

- [ ] **Step 8: Commit**

```bash
git add src/ web/static/js/
git commit -m "feat: FileManager migrated to TypeScript with Vitest coverage"
```

### Task 5.3: TypeScript migration — Processor, MapViewer, App

Repeat the same pattern as Task 5.2 for each remaining module:

- [ ] Migrate `processor.js` → `src/modules/processor.ts`
  - Type: `ProcessingStatus`, polling logic, EventBus events
  - Test: progress step calculation, error state handling
  - Verify: full workflow runs end-to-end
  - Delete: `web/static/js/processor.js`

- [ ] Migrate `mapViewer.js` → `src/modules/mapViewer.ts`
  - Type: iframe reference, `refreshMap()` return type
  - Note: Cesium iframe stays as-is; MapViewer just wraps it
  - Verify: map loads in browser, animation plays
  - Delete: `web/static/js/mapViewer.js`

- [ ] Migrate `app.js` → `src/modules/app.ts`
  - Type: `BriefingManager`, keyboard handlers, component orchestration
  - Remove `window.app` global — coordinate via EventBus
  - Verify: briefing modal opens, print/download work
  - Delete: `web/static/js/app.js`

- [ ] **Final commit after all modules migrated**

```bash
git commit -m "feat: complete TypeScript migration — all modules converted"
```

---

## Phase 6: Testing & Error Handling

**Critical files:**
- Create: `src/__tests__/integration/workflow.test.ts`, `src/utils/errorHandler.ts`
- Expand: existing unit tests to 80%+ coverage

### Task 6.1: Integration tests

- [ ] **Step 1: Write integration test for upload → validate → process flow**

Create `src/__tests__/integration/workflow.test.ts`:
```typescript
import { describe, it, expect, vi } from 'vitest';

// Mock fetch for the full upload → validate → process workflow
describe('Upload → Process workflow', () => {
    it('validates file before processing', async () => {
        // Mock /validate/<filename> returning valid response
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ ok: true, data: { valid: true, flight_count: 1, flights: [] } })
        });
        // Test that FileManager marks file as valid after validation
        // ... test body
    });
});
```

- [ ] **Step 2: Write integration test for error path (network failure)**

```typescript
it('shows toast on network failure', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));
    // Test that showToast('error') is called
});
```

- [ ] **Step 3: Implement `src/utils/errorHandler.ts`**

```typescript
import { bus } from '../modules/eventBus';

export function handleError(context: string, error: unknown): void {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`[${context}]`, error);
    bus.emit('error', { context, message });
}
```

- [ ] **Step 4: Run coverage report**

```bash
npm run test:coverage
# Expected: ≥ 80% coverage on business logic in src/modules/ and src/utils/
```

- [ ] **Step 5: Commit**

```bash
git add src/__tests__/ src/utils/
git commit -m "feat: integration tests and centralised error handling"
```

---

## Phase 7: Polish, Performance & CI

**Critical files:**
- Update: `.github/workflows/docker.yml` — add Node.js lint/test/build steps
- Verify: bundle < 50KB gzip, Lighthouse ≥ 85

### Task 7.1: CI/CD pipeline — add Node.js steps

- [ ] **Step 1: Update `.github/workflows/docker.yml`**

Before the Docker build step, add:
```yaml
- name: Set up Node.js
  uses: actions/setup-node@v4
  with:
    node-version: '18'
    cache: 'npm'

- name: Install frontend dependencies
  run: npm ci

- name: Type-check
  run: npm run type-check

- name: Lint
  run: npm run lint

- name: Run frontend tests
  run: npm run test

- name: Build frontend
  run: npm run build
```

- [ ] **Step 2: Verify CI passes on a test push**

```bash
git add .github/workflows/docker.yml
git commit -m "ci: add Node.js lint, type-check, test, and build steps"
git push
# Check GitHub Actions run succeeds
```

### Task 7.2: Bundle size and performance

- [ ] **Step 1: Analyse bundle size**

```bash
npm run build
# Check web/static/dist/assets/*.js sizes
# Target: < 50KB gzip total
gzip -c web/static/dist/assets/*.js | wc -c
```

- [ ] **Step 2: Add code splitting for modal (lazy load)**

In `src/index.ts`:
```typescript
// Lazy load modal on first use
async function openBriefing() {
    const { BriefingModal } = await import('./modules/modal');
    new BriefingModal().show();
}
```

- [ ] **Step 3: Run Lighthouse audit**

```bash
npx lighthouse http://localhost:5000 --output json --quiet | jq '.categories.performance.score'
# Expected: ≥ 0.85
```

- [ ] **Step 4: Update `README.md` with new dev/build/test commands**

Add section:
```markdown
## Frontend Development

```bash
npm install          # install dependencies
npm run dev          # Vite dev server on :5173 (proxies API to Flask :5000)
npm run build        # production build → web/static/dist/
npm run test         # Vitest unit tests
npm run test:visual  # Playwright visual regression
npm run type-check   # TypeScript without emitting
npm run lint         # ESLint
```
```

- [ ] **Step 5: Final commit**

```bash
git add README.md
git commit -m "docs: update README with frontend dev workflow"
```

---

## Verification Checklist (End-to-End)

- [ ] `npm install` — no errors
- [ ] `npm run build` — `web/static/dist/` contains JS + CSS
- [ ] `npm run dev` — Vite starts on :5173, proxies API to Flask on :5000
- [ ] `npm run test` — all Vitest tests green
- [ ] `npm run test:coverage` — ≥ 80% coverage on `src/modules/` and `src/utils/`
- [ ] `npm run test:visual` — Playwright axe audit 0 violations, visual regression within 2%
- [ ] `npm run type-check` — 0 TypeScript errors
- [ ] `npm run lint` — 0 ESLint warnings
- [ ] Docker: `docker build .` succeeds with multi-stage Node + Python
- [ ] `docker-compose up` — app accessible on :5000, serves Vite-built assets
- [ ] Bundle size: JS + CSS gzipped < 50KB
- [ ] Lighthouse performance score ≥ 85
- [ ] Full workflow test: upload XML → validate → select → generate → view animation → open briefing
- [ ] Modal: Escape closes, focus returns to trigger, screen reader can read content
- [ ] Responsive: layout correct at 375px, 768px, 1024px

---

## Cesium Phase 2 (Future — Out of Scope for This Plan)

The Cesium animation (`animation/status_bar_development.html`) stays as-is. When Phase 2 begins:
- Extract Cesium logic into a proper ES module
- Enable typed `postMessage` communication between the parent frame and Cesium
- Consider replacing iframe with direct Cesium SDK integration in the main bundle
- This is a separate project — do not begin until Phase 1 (this plan) is complete and stable in production
