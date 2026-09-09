---
name: ui-ux-craft
description: Audit HTML, CSS, component libraries, and frontend interfaces for semantic HTML, accessibility (a11y/WCAG), the 4 essential UI states, responsive layout safety, and time-tested professional UI conventions. Use when building or modifying web, mobile, or desktop user interfaces.
---

# UI/UX Craft & Frontend Engineering Guard

> **Telemetry (dogfood):** on each invocation record it with `ck skill --called ui-ux-craft --stage <stage>` so usage is measurable (see ADR-0007).

Bridge the gap between naive "vibe-coding" and production-grade frontend engineering. Guarantee that user interfaces are accessible, resilient to network and data edge cases, responsive across all viewports, and maintainable.

---

## ⚡ The 4 Mandatory UI States (The "Never Skip" Law)

Every component or view that displays dynamic, remote, or asynchronous data **MUST** explicitly handle all four states:

1. **Loading State**:
   - Display skeleton loaders or accessible spinners while awaiting data.
   - Skeletons must match the dimension of loaded content to eliminate Cumulative Layout Shift (CLS).
2. **Empty State**:
   - Never leave an empty blank card, table, or screen when data is `[]` or `null`.
   - Provide a helpful illustration/icon, a human-readable explanation, and a clear call-to-action (e.g., *"No projects found. Click 'New Project' to get started."*).
3. **Error State**:
   - Catch network and runtime rendering failures gracefully.
   - Display a non-technical error message explaining what happened.
   - Always include an actionable **"Retry"** button to re-trigger the failed query.
4. **Success State**:
   - Render the complete, structured data cleanly with appropriate pagination or virtualization if unbounded.

---

## ♿ Semantic HTML & Accessibility (A11y / WCAG 2.1 AA)

1. **Interactive Elements**:
   - **Never** use `<div onClick>` or `<span onClick>` for buttons or links.
   - Use `<button type="button">` for actions. Use `<a href="...">` for navigation.
   - Keyboard navigation must work out-of-the-box (`Tab` order, `Enter`, and `Space` activation).
2. **Form Accessibility**:
   - Every input field must have an explicit `<label htmlFor="id">` or wrap inside a `<label>`.
   - Use `aria-describedby` to link input fields to their inline error messages or help text.
   - Mark invalid fields with `aria-invalid="true"`.
3. **Icons and Images**:
   - Informative images **MUST** have descriptive `alt` text.
   - Decorative icons/graphics **MUST** have `aria-hidden="true"` or empty `alt=""`.
   - Icon-only buttons **MUST** have an `aria-label="Action Description"` (e.g. `aria-label="Close dialog"`).
4. **Focus & Contrast**:
   - Never remove focus outlines with `outline: none` without providing an explicit, high-contrast `:focus-visible` ring.
   - Text color contrast must achieve at least 4.5:1 against the background for normal text (3:1 for large text).
5. **Touch Targets**:
   - On mobile/touch interfaces, all tap targets must be at least **44 × 44 CSS pixels** (`min-h-[44px] min-w-[44px]`).

---

## 📱 Responsive & Defensive CSS

1. **Mobile-First Layout**:
   - Design for small screens first, then progressively expand with media queries / responsive utility classes (`sm:`, `md:`, `lg:`).
2. **Fluid Containers**:
   - **Never** use fixed container widths like `width: 800px` that cause horizontal scrollbars on mobile.
   - Use fluid constraints: `w-full max-w-4xl mx-auto`.
3. **Text Overflow Containment**:
   - User-generated text (names, titles, emails, URLs) can be arbitrarily long.
   - Always apply overflow protection: `truncate`, `break-words`, or `line-clamp-2` to prevent layout breaking.
4. **Agent Creative Autonomy & Token Cohesion**:
   - **Agent Design Freedom**: The agent has full creative autonomy to design aesthetic layouts, propose palettes, and decide brand/theme colors.
   - **Token Cohesion**: When choosing or introducing colors, define them cleanly as reusable design tokens or CSS custom properties (e.g. `:root { --accent: #6366f1; }`) or utility classes rather than scattering arbitrary one-off magic hex values across individual component styles. This preserves maintainability while empowering the agent to craft beautiful, intentional designs.

---

## 🔒 Defensive Interaction & Idempotency

1. **Double-Submit Prevention**:
   - Submission buttons must be disabled and show loading indicators while a form or action is in flight (`disabled={isSubmitting}`).
2. **Optimistic Updates**:
   - If mutating UI optimistically before server response, always provide an instant rollback mechanism if the server returns an error.
3. **Feedback Timing**:
   - Provide immediate visual acknowledgment upon user interaction (button active state, toast notification, or progress indicator).

---

## 🎬 Motion Physics & Micro-Interaction Craft (Emil Kowalski Laws)

Bridge the gap between generic transitions and world-class design engineering. Eliminate "AI motion slop":

1. **The Law of Scale (The `scale(0)` Ban)**:
   - **Never** animate modals, tooltips, popovers, or cards starting from `scale(0)`.
   - Scale entrances **MUST** start between **`0.92` and `0.97`** paired with an opacity fade (`opacity: 0 -> 1`). Elements should feel like they are stepping forward into focus, not bursting from an infinitely small singularity.
2. **The Law of Easing & Latency**:
   - **Never** use `ease-in` on UI entrance animations. `ease-in` begins sluggishly, making clicks feel delayed and unresponsive.
   - **Entrances** must use **`ease-out`** (or a crisp spring with fast initial velocity) so the UI reacts instantly to user action.
   - **Exits** must be **30–40% faster** than entrances. When dismissing content, users perceive lingering animations as lag.
3. **The Timing Hierarchy**:
   - **Micro-feedback** (buttons, toggles, checkboxes): **100ms – 160ms**.
   - **Overlays & Popovers** (tooltips, dropdowns, menus): **150ms – 220ms**.
   - **Surfaces & Modals** (dialogs, side-drawers, sheets): **200ms – 350ms**.
   - **Hard Ceiling**: No interactive UI animation should exceed **400ms**.
   - **Stagger Delays**: List/grid item staggers must be between **30ms – 60ms** (staggers >80ms make lists feel broken).
4. **Gesture Physics vs Discrete Curves**:
   - For user-driven gestures (swiping, dragging, sheets): **Always use springs** (`bounce: 0.1–0.25`). Fixed bezier curves discard touch velocity upon release and feel robotic.
   - For discrete clicks: use damped transitions without oscillating bounce.
5. **Spatial Transform Continuity (`transform-origin`)**:
   - Popovers, context menus, and tooltips must animate from their **trigger anchor** (e.g. `transform-origin: top right`), never from their arbitrary center.
6. **Zero Animation on High-Frequency Actions**:
   - If an action occurs 100+ times/day (command palettes, keyboard shortcuts, switching tab rows), **do not animate it**, or keep it under 100ms. Motion fatigue destroys productivity.
7. **Composite-Only Properties & A11y**:
   - Animate **only composite properties**: `transform` and `opacity`. Never animate layout-triggering properties (`width`, `height`, `top`, `left`, `margin`).
   - Always honor `@media (prefers-reduced-motion: reduce)` by disabling transforms/motion and using simple opacity fades or instant cuts.

---

## 🔍 UI/UX Craft Audit Checklist

- [ ] **4-State Completeness:** Are Loading, Empty, Error (with retry), and Success states implemented?
- [ ] **Semantic Elements:** Are `<button>`, `<nav>`, `<main>`, `<header>`, `<footer>`, and `<label>` used properly?
- [ ] **Keyboard & Focus:** Can the entire interaction flow be operated via keyboard alone with visible focus rings?
- [ ] **Icon / Image A11y:** Do icon-only buttons have `aria-label`? Do images have appropriate `alt` tags?
- [ ] **Viewport Responsiveness:** Does the UI display without horizontal scrolling at 375px (mobile) and 1440px (desktop)?
- [ ] **Touch Target Size:** Are all mobile buttons and links at least 44×44px in clickable area?
- [ ] **Text Overflow:** Are long strings protected with `truncate` or `break-words`?
- [ ] **Submission Protection:** Are submit buttons disabled during active mutations?
- [ ] **Scale & Motion Feel:** Do entrances scale from 0.92–0.97 (never scale(0))? Are durations ≤ 350ms with ease-out?
- [ ] **Reduced Motion Support:** Does the CSS/component respect `prefers-reduced-motion`?

---

## 📋 Required Audit Output

```markdown
### 🎨 UI/UX Craft & Frontend Stability Report

- **Component / View:** `src/components/UserProfile.tsx`
- **4-State Completeness:** [PASS (all 4 handled) | MISSING: Empty / Error retry]
- **A11y & Semantic HTML:** [PASS | VIOLATIONS DETECTED (e.g. div onClick without role/tabindex)]
- **Responsive Layout:** [PASS | OVERFLOW RISKS DETECTED]
- **Interaction Hygiene:** [PASS | MISSING: Double-submit prevention on form]
- **Motion & Micro-Interactions:** [PASS | MOTION SLOP DETECTED (e.g. scale(0), ease-in entrance, duration > 400ms)]
- **Remediation Plan:** [Concrete fixes to elevate component to production standards]
```
