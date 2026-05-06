# VATSIM-Chaos: Frontend Modernisation Plan (UI/UX + TypeScript)

## Context

VATSIM-Chaos has excellent backend infrastructure (Python, Flask, conflict detection) and a comprehensive Docker plan (`DOCKER_PLAN.md`). The frontend needs modernisation for contemporary UI/UX and code quality.

**Current Frontend State:**
- Vanilla JavaScript (2,447 lines) + vanilla CSS (1,049 lines)
- Dark VATSIM theme with glassmorphism effects
- No framework (React/Vue), no TypeScript, no tests
- Functional but lacks: modern interactions, accessibility, visual polish
- Served by Flask from `web/static/` and `web/templates/`

**Your Requirements:**
1. **Modern UI/UX** — Professional appearance, smooth interactions, visual feedback
2. **Docker-ready** — Works with existing Docker setup from `DOCKER_PLAN.md`

**Timeline:** 13 weeks, 7 phases with incremental rollout

---

## Critique of Existing Frontend Plan

**The previous plan was solid for modernisation approach**, but missed:

- **Didn't account for existing Docker infrastructure** — Your DOCKER_PLAN.md already handles containerisation beautifully
- **Assumed Vite integration issues** — With proper build output directory, Vite integrates cleanly with Flask
- **Over-complicated Phase 1** — Shouldn't create multiple Dockerfiles; should use multi-stage in existing Dockerfile

**What This Plan Adds:**
1. **Specific Flask integration** — Vite builds to `web/static/dist/`, Flask serves it
2. **Respects existing Docker work** — References DOCKER_PLAN.md, doesn't reinvent
3. **Clear rollout strategy** — Old JS/CSS → new TypeScript/CSS in parallel, switchover in Phase 5
4. **Verification for each phase** — How to test that modernisation works

---

## Implementation Plan

### Phase 1: Tooling & Project Setup (Weeks 1-2)

**Frontend Build Setup:**
- Install Vite 5.x, TypeScript 5.x, ESLint, Prettier
- Create `package.json` with build scripts
- Create `src/` directory for TypeScript source
- Configure `vite.config.ts` to output to `web/static/dist/`
- TypeScript strict mode in `tsconfig.json`
- ESLint + Prettier configuration for code quality

**Flask Integration:**
- Update `web/app.py` to serve assets:
  - In dev: proxy requests to `http://localhost:5173` (Vite dev server)
  - In prod: serve pre-built files from `web/static/dist/`
- Create simple routing to distinguish asset requests from API calls

**Docker Integration (Minimal):**
- Update `Dockerfile`: add Node.js build stage before Python stage
  - Stage 1: `node:18-alpine` → `npm install`, `npm run build` → outputs `web/static/dist/`
  - Stage 2: existing Python stage (inherits built assets)
- Keep `docker-compose.yml` and `docker.env` unchanged

**Deliverable:**
- ✅ `npm run dev` starts Vite on localhost:5173
- ✅ `npm run build` creates optimised bundle in `web/static/dist/`
- ✅ Flask development server proxies to Vite for HMR
- ✅ Docker builds with both Node and Python stages
- ✅ Old JS/CSS still works (coexist during transition)

---

### Phase 2: Accessibility & Modern UX (Weeks 3-4)

**Accessibility (WCAG 2.1 AA):**
- Replace 30+ emoji icons with semantic approach (ARIA labels or SVG icons)
- Implement modal with focus trap + restoration
- Fix form semantics: associated labels, `aria-live` regions
- Add keyboard navigation: proper Tab/Shift+Tab, Escape, Enter handling
- Test with axe DevTools (target: 0 violations)

**Visual Feedback & Interactions:**
- File upload: drag-and-drop highlight (cyan border), file previews, upload progress bars
- File library: metadata display (date, size), sorting/filtering, status badges
- Toast notifications: success (green), error (red), warning (orange), auto-dismiss
- Loading states: spinners, skeleton loaders during operations
- Error messages: styled cards with icon, message, recovery steps
- Real-time progress: step indicators (1/6 → 2/6) with elapsed/remaining time
- Input validation: live feedback ("Start time must be before end time")
- Smooth transitions: fade-ins, slide-ins on modals (250-400ms)
- Hover/focus states: clear visual indicators on buttons, links

**Deliverable:**
- ✅ WCAG 2.1 AA compliant (axe: 0 violations)
- ✅ Professional visual feedback on every interaction
- ✅ Old JavaScript still works (HTML layer modernised)

---

### Phase 3: Modern Styling Architecture (Weeks 5-6)

**CSS Variables & Components:**
- Create `src/styles/_variables.css` with CSS custom properties:
  - Colors: primary (#00d4ff), success (#10b981), error (#ef4444), warning (#f59e0b)
  - Spacing: 4px, 8px, 12px, 16px, 20px, 24px scale
  - Typography: font sizes, weights, line heights
  - Animations: easing functions, duration presets (250ms, 400ms)
- Extract reusable component styles: buttons, forms, panels, badges, cards
- Create `src/styles/_components.css` for component library

**Enhanced Styling:**
- SVG icon integration (Feather Icons or similar)
- Smooth animations: button lift on hover, progress animations
- Responsive design: breakpoints for mobile (375px), tablet (768px), desktop (1024px)
- Touch-friendly: 44px+ touch targets
- Dark mode CSS variables (ready for `prefers-color-scheme` in future)
- Component variants: button sizes (sm/md/lg), button types (primary/secondary/danger)
- Professional gradients and shadows for depth

**Deliverable:**
- ✅ Maintainable, themeable CSS architecture
- ✅ Professional component design system
- ✅ Visual parity with existing design (no breaking changes)
- ✅ CSS minification in production build

---

### Phase 4: State Management & Events (Weeks 7-8)

**Event-Driven Architecture:**
- Build `EventBus` utility (simple pub-sub, zero dependencies)
- Define event types in `src/modules/types.ts`:
  - `FileUploadedEvent`, `ProcessingStartedEvent`, `ProgressUpdateEvent`, `BriefingReadyEvent`, etc.
- Refactor modules to emit events instead of direct DOM manipulation
- Remove global `window.app` variable; coordinate via EventBus listeners

**Testability & Decoupling:**
- Modules become independent and testable in isolation
- Event flow becomes traceable (easier debugging)
- No tight coupling between FileManager, Processor, MapViewer

**Deliverable:**
- ✅ Event-driven architecture with clean separation
- ✅ Decoupled, independently testable modules
- ✅ Feature parity maintained with old code

---

### Phase 5: TypeScript Migration (Weeks 9-10)

**Strict Type Safety:**
- Migrate each module: `fileManager.js` → `fileManager.ts`, etc.
- Enable strict mode (`strict: true`)
- Define types for:
  - `FlightPlan`, `Conflict`, `ProcessingStatus`
  - File upload data, API responses
  - Event payloads
- Create `src/types/api.ts` for backend response shapes
- Create `src/utils/validation.ts` for testable validation functions

**IDE Support & Compile-Time Safety:**
- Full autocomplete in development
- Compile-time error catching
- Refactoring confidence with type checking

**Deliverable:**
- ✅ Full TypeScript compilation (0 errors)
- ✅ Type safety throughout codebase
- ✅ IDE autocomplete working
- ✅ Can now safely delete old `.js` files

---

### Phase 6: Testing & Error Handling (Weeks 11-12)

**Unit Tests (Vitest):**
- Test critical modules: FileManager, Processor, Utilities
- Target 80%+ coverage on business logic
- Testing Library for DOM interaction tests

**Integration Tests:**
- Full workflow: upload → validation → processing → briefing
- Error scenarios: invalid files, network failures, edge cases
- UI interaction tests: drag-drop, modal focus, keyboard navigation

**Error Handling:**
- Centralised error handler in `src/utils/errorHandler.ts`
- User-friendly error messages (no stack traces)
- Retry logic for transient failures
- Graceful degradation

**Deliverable:**
- ✅ 80%+ test coverage on business logic
- ✅ Production-ready error handling
- ✅ Automated test execution

---

### Phase 7: Polish, Performance & Optimization (Weeks 13+)

**Visual Polish:**
- Professional SVG iconography (replace remaining emoji)
- Refined colour palette (WCAG AAA contrast audit)
- Subtle gradients and depth effects
- Improved typography refinement
- Micro-interactions: ripple on click, subtle fade-ins, loading spinners
- Empty states with helpful illustrations and guidance

**Performance Optimization:**
- Bundle analysis: target < 50KB gzip for JS + CSS
- Code splitting: lazy-load modal components
- Tree-shaking: remove unused CSS
- Font optimization: system font stack (no external fonts)
- Image optimization: SVG only, no PNG

**Documentation:**
- `README.md`: updated with `npm run dev`, `npm run build`, `npm run test`
- Architecture guide: module responsibilities, event flow diagram
- TypeScript patterns document
- Testing guide: how to write new tests
- Deployment checklist: Docker build, environment variables, verification steps

**Deliverable:**
- ✅ Polished, professional interface
- ✅ Optimised bundle (< 50KB gzip)
- ✅ Complete documentation
- ✅ Ready for production deployment

---

## Design Direction

**Visual Style:** Modern ATC aesthetic, professional and responsive

- **Dark theme base:** Keep VATSIM community's preferred dark theme
- **Refined palette:**
  - Primary: #00d4ff (cyan, kept from original)
  - Success: #10b981 (professional green)
  - Error: #ef4444 (clear red)
  - Warning: #f59e0b (professional orange)
  - Neutrals: #0f172a background, refined grays
- **Typography:** System fonts (Inter fallback → -apple-system, Segoe UI, sans-serif)
- **Icons:** Professional SVG (Feather Icons or custom VATSIM-themed)
- **Spacing:** Consistent scale, breathing room between sections
- **Animations:** Smooth, purposeful (250-400ms), never gratuitous
- **Accessibility:** WCAG 2.1 AA minimum throughout

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Bundler** | Vite 5.x | Fast dev server, optimised builds, zero-config |
| **Language** | TypeScript 5.x | Type safety, IDE support, industry standard |
| **Testing** | Vitest + Testing Library | Vite-native, Jest-compatible, fast |
| **Linting** | ESLint + @typescript-eslint | Catches bugs, enforces standards |
| **Formatting** | Prettier | Opinionated consistency, zero-config |
| **Icons** | Feather Icons (SVG) | Professional, lightweight, 24x24px |
| **CSS** | CSS + CSS Variables | Native, no build overhead, themeable |
| **State** | EventBus (custom) | Simple, testable, zero dependencies |
| **Backend** | Flask (unchanged) | Existing, proven, works great |
| **Docker** | Multi-stage (existing plan) | See DOCKER_PLAN.md for strategy |

---

## Critical Files

### Phase 1: Tooling
- ✨ `package.json` — Scripts, dependencies
- ✨ `vite.config.ts` — Bundler configuration
- ✨ `tsconfig.json` — TypeScript strict settings
- ✨ `.eslintrc.json`, `.prettierrc` — Code quality
- ✨ `src/index.ts` — Application entry point
- 📝 `Dockerfile` — Add Node.js build stage
- 📝 `web/app.py` — Serve dist/, dev proxy

### Phase 2-3: HTML/CSS
- 📝 `web/templates/index.html` — ARIA labels, semantic markup
- ✨ `src/styles/_variables.css` — CSS variables
- ✨ `src/styles/_components.css` — Component styles
- ✨ `src/modules/modal.ts` — Accessible modal component

### Phase 4-5: TypeScript
- ✨ `src/modules/types.ts` — Event & data types
- ✨ `src/modules/eventBus.ts` — Pub-sub system
- 🔄 `src/modules/fileManager.ts` — Migrated from JS
- 🔄 `src/modules/processor.ts` — Migrated from JS
- 🔄 `src/modules/mapViewer.ts` — Migrated from JS
- ✨ `src/modules/app.ts` — New orchestrator
- ✨ `src/utils/validation.ts` — Testable utilities
- ✨ `src/utils/errorHandler.ts` — Centralised error handling

### Phase 6+: Testing
- ✨ `vitest.config.ts` — Test runner config
- ✨ `src/__tests__/modules/fileManager.test.ts` — Unit tests
- ✨ `src/__tests__/integration/workflow.test.ts` — Integration tests

### Always Update
- 📝 `.gitignore` — Add dist/, coverage/, node_modules/
- 📝 `README.md` — Dev/build/test instructions

Legend: ✨ = new file, 📝 = modify existing, 🔄 = migrate with refactor

---

## Implementation Sequence

**Feature-by-Feature Switchover** (Zero-regression approach):

### Phase 1: Tooling Setup (Weeks 1-2)
- `npm run dev` works, Docker multi-stage builds
- Both old and new code ready to coexist

### Phase 2: Module 1 - FileManager (Weeks 3-5)
- Modernise FileManager completely (HTML + CSS + TypeScript + tests)
- Keep old `fileManager.js` running alongside
- Route file upload/management to new TypeScript module
- **Validation:** Test thoroughly, full coverage, compare against old behavior
- **Rollback:** If issues, revert to old `fileManager.js` immediately
- **Cutover:** Switch production to new FileManager once validated (1-2 days of testing)

### Phase 3: Module 2 - Processor (Weeks 6-8)
- Modernise Processor (orchestration, progress tracking)
- Keep old `processor.js` running
- Switch to new TypeScript Processor
- Same validation/rollback/cutover process

### Phase 4: Module 3 - MapViewer (Weeks 9-11)
- Modernise MapViewer (Cesium integration)
- Switch to new TypeScript MapViewer
- Validate, test, cutover

### Phase 5: Global UX & Accessibility (Weeks 12-14)
- HTML semantic updates (ARIA labels, accessibility)
- CSS variables and component system
- Toast notifications, visual feedback, animations
- Test across all modules together

### Phase 6: Testing & Documentation (Weeks 15-16)
- Full integration tests across all modules
- 80%+ coverage target
- Documentation, deployment guide

### Phase 7: Polish & Performance (Weeks 17+)
- Visual refinement, SVG icons, animations
- Bundle optimization
- Production hardening

**Switchover Strategy (Zero Downtime):**
- Each module independently tested and validated before switchover
- Old code kept as fallback during each transition
- If new module breaks, immediate rollback to old version (seconds)
- Only delete old code AFTER all modules successfully running in production (week 16+)
- Docker handles both scenarios seamlessly

---

## Success Criteria

### Code Quality ✓
- TypeScript compiles with zero errors (strict mode)
- ESLint: zero warnings in new code
- Test coverage: 80%+ on business logic
- Bundle size: < 50KB gzip (JS + CSS)

### UI/UX ✓
- WCAG 2.1 AA compliant (axe: 0 violations)
- All interactions have visual feedback (loading, success, error)
- Smooth animations (250-400ms)
- Professional appearance throughout
- Mobile-responsive (touch targets ≥ 44px)

### Docker ✓
- Multi-stage build works (Node stage + Python stage)
- `docker-compose up` still works with existing config
- Production image < 400MB total
- Frontend bundle included and served by Flask

### Functionality ✓
- Zero regressions in file upload/processing workflow
- Briefing modal displays correctly
- Performance ≥ baseline (no slowdowns)
- All original features work perfectly

### Documentation ✓
- `README.md`: dev/build/test/deploy instructions
- Architecture: module responsibilities, event flow
- TypeScript patterns documented
- Testing guide: how to write new tests
- Deployment: Docker build + verification steps

---

## Verification Checklist

### Phase 1
- [ ] `npm install` successful
- [ ] `npm run dev` starts Vite on localhost:5173
- [ ] `npm run build` creates `web/static/dist/`
- [ ] Flask dev server proxies to Vite correctly
- [ ] Docker multi-stage build succeeds
- [ ] Flask serves assets from built files

### Phase 2
- [ ] `npm run lint` passes (0 warnings)
- [ ] axe audit: 0 violations
- [ ] Keyboard navigation: Tab, Shift+Tab, Escape work
- [ ] Screen reader: can identify all form inputs and buttons

### Phase 3
- [ ] Visual regression: pixel-perfect match with original
- [ ] CSS variables: all colors load from variables
- [ ] Responsive: tested at 375px, 768px, 1024px widths
- [ ] Bundle CSS minified in production build

### Phase 4
- [ ] All events emitted to EventBus, logged in console
- [ ] Modules work standalone (can test independently)
- [ ] No console errors about undefined globals

### Phase 5
- [ ] `npm run type-check` (tsc): 0 errors
- [ ] `npm run lint`: 0 warnings
- [ ] IDE autocomplete: working in all files
- [ ] Old JS files can be safely deleted

### Phase 6
- [ ] `npm run test` passes: all tests green
- [ ] `npm run test:coverage`: ≥ 80% coverage
- [ ] No console errors or warnings during test run

### Phase 7
- [ ] `npm run build` output: < 50KB gzip
- [ ] Docker image size: < 400MB
- [ ] All original workflows work end-to-end
- [ ] Lighthouse: performance ≥ 85
- [ ] README updated with all instructions

---

## Integration with Existing Infrastructure

### Docker
- ✅ Multi-stage `Dockerfile`: Node stage builds frontend, Python stage runs Flask
- ✅ Existing `docker-compose.yml` unchanged (no new services needed)
- ✅ Existing `docker.env` unchanged (no new environment variables)
- ✅ Reference `DOCKER_PLAN.md` for container strategy

### Flask
- ✅ Existing Flask app (`web/app.py`) serves Vite output
- ✅ Dev mode: proxy to Vite dev server (hot-reload)
- ✅ Prod mode: serve static files from `web/static/dist/`
- ✅ All existing endpoints (`/upload`, `/process`, `/status`) unchanged

### Existing Code
- ✅ Old JS/CSS remain until Phase 5 (safe parallel transition)
- ✅ New TypeScript alongside old JS (both work simultaneously)
- ✅ After Phase 5: delete old files, zero downtime

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Vite → Flask integration delays | MEDIUM | Test Phase 1 thoroughly, keep fallback to direct file serving |
| CSS visual regression | MEDIUM | Screenshot tests before/after Phase 3, keep old CSS as reference |
| State management complexity | LOW | EventBus is simple, don't over-engineer, expand only if needed |
| TypeScript learning curve | LOW | Use `any` temporarily, tighten gradually as team learns |
| Bundle size bloat | MEDIUM | Regular bundle analysis, tree-shake CSS, lazy-load components |
| Docker image too large | LOW | Multi-stage build, exclude node_modules, test image size regularly |
| Test maintenance burden | MEDIUM | Start with critical paths only, expand incrementally |

---

## Next Steps

1. ✅ **Review this plan** — Critique and approve approach
2. **Phase 1 Setup** — Install Vite, TypeScript, update Docker
3. **Phase 1 Verification** — Confirm dev server and Docker work
4. **Continue sequentially** — Complete each phase before next

---

## Notes

- **Docker Strategy:** Your existing `DOCKER_PLAN.md` is comprehensive. This plan integrates with it, not replacing it.
- **Frontend Focus:** This plan addresses modern UI/UX and code quality. Backend architecture is solid and unchanged.
- **Incremental:** Old and new code coexist until Phase 5, allowing safe rollback.
- **Production-Ready:** By Phase 7, system is optimised, tested, and documented for production.
- **British English:** All documentation uses British spelling (colour, favour, organisation, etc.) per your CLAUDE.md preferences.
