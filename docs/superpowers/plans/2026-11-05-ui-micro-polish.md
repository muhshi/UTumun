# UI Micro-Polish (Make Interfaces Feel Better) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement design-engineering micro-polish based on the `make-interfaces-feel-better` principles across the Tuton UT dashboard (tabular numbers, text balance, scoped transitions, tactile button states, and comfortable hit areas) and deploy to the production VPS.

**Architecture:** Refine styling rules in `app/static/css/style.css` and template markup in `app/templates/index.html` to eliminate layout jitter from dynamic numbers, avoid awkward text line wrapping, replace heavy `transition: all` rules with GPU-accelerated explicit transitions, expand small button hit areas to >=40px, and push updates to the live Docker environment.

**Tech Stack:** HTML5, CSS3, Tailwind CSS, Alpine.js, FastAPI / Jinja2, Docker, Git.

---

### Task 1: Refactor CSS Polish in `app/static/css/style.css`

**Files:**
- Modify: `app/static/css/style.css:30-80`

- [x] **Step 1: Check existing style.css rules**

Verify root font-smoothing, transition definitions, and missing utilities in `app/static/css/style.css`.

- [x] **Step 2: Apply micro-polish CSS rules in `app/static/css/style.css`**

Add root `html` font-smoothing, replace `transition: all` in `.card-hover-effect` with explicit properties (`transform, box-shadow, border-color`), declare `text-wrap: balance` for headings, declare `font-variant-numeric: tabular-nums` for counters and numbers, and add tactile press & hit area classes:

```css
html {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

h1, h2, h3, h4 {
  text-wrap: balance;
}

.tabular-nums {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
}

.card-hover-effect {
  transition-property: transform, box-shadow, border-color;
  transition-duration: 200ms;
  transition-timing-function: cubic-bezier(0.16, 1, 0.3, 1);
}

.btn-tactile {
  transition-property: transform, background-color, border-color, box-shadow, color;
  transition-duration: 150ms;
  transition-timing-function: ease-out;
}

.btn-tactile:active {
  transform: scale(0.97);
}

.hit-target-40 {
  min-width: 40px;
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
```

- [x] **Step 3: Verify CSS syntax and formatting**

Check that `style.css` contains valid CSS and does not break existing color variables or animations.

- [x] **Step 4: Commit Task 1 changes**

```bash
git add app/static/css/style.css
git commit -m "style: apply optical polish rules, tabular nums, and scoped transitions"
```

---

### Task 2: Polish Dashboard Template in `app/templates/index.html`

**Files:**
- Modify: `app/templates/index.html`

- [ ] **Step 1: Audit `transition-all` occurrences in `app/templates/index.html`**

Find all 28 instances of `transition-all` and replace them with scoped transitions like `transition-colors`, `transition-transform`, or `.btn-tactile`.

- [ ] **Step 2: Add `tabular-nums` to dynamic numbers and counters**

Add `tabular-nums` to:
- Header stats / recap counters (`total_students`, `completed`, `pending`, `completion_rate`)
- Progress percentage labels and progress bars
- Matrix cells (completed/total counters per session)
- Student card score displays and trajectory score badges

- [ ] **Step 3: Expand hit areas of small action buttons to >=40px**

Update small icon buttons (quick copy feedback, quick copy grade, modal close, session selector items) to have `min-h-[40px] min-w-[40px]` or comfortable padding with tactile press states.

- [ ] **Step 4: Update CSS & JS cache buster versions in `index.html`**

Update `style.css?v=2.5` and `app.js?v=2.5` in `app/templates/index.html`.

- [ ] **Step 5: Commit Task 2 changes**

```bash
git add app/templates/index.html
git commit -m "feat(ui): apply tabular numbers, scoped transitions, and tactile hit targets"
```

---

### Task 3: Local Testing & Verification

**Files:**
- Test: `tests/`

- [ ] **Step 1: Run complete test suite**

Run: `.venv/bin/pytest tests/ -q`
Expected: 76 passed.

- [ ] **Step 2: Verify HTML page rendering via test client**

Ensure `/` route returns status 200 and loads polished stylesheet tags.

---

### Task 4: Server Deployment & Container Synchronization

**Files:**
- Server: `bpsdemak@10.133.21.24` -> `apps/muhshi/UTumun`
- Container: `tuton_dashboard`

- [ ] **Step 1: Push changes to GitHub repository**

```bash
git push origin main
```

- [ ] **Step 2: Pull repository on remote server**

```bash
ssh bpsdemak@10.133.21.24 "cd apps/muhshi/UTumun && git pull"
```

- [ ] **Step 3: Synchronize updated templates & static files into docker container**

```bash
ssh bpsdemak@10.133.21.24 "cd apps/muhshi/UTumun && docker cp app tuton_dashboard:/app/"
```

- [ ] **Step 4: Restart container and test live dashboard response**

```bash
ssh bpsdemak@10.133.21.24 "docker restart tuton_dashboard && curl -s -f http://localhost:8020/api/recap | grep total_students"
```

- [ ] **Step 5: Verify live UI in browser**

Confirm port `8020` is serving the updated UI with no console errors and smooth micro-interactions.
