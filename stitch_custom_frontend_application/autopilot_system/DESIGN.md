---
name: Autopilot System
colors:
  surface: '#f8f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f8f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#45464d'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#006a61'
  on-secondary: '#ffffff'
  secondary-container: '#86f2e4'
  on-secondary-container: '#006f66'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#0d1c2e'
  on-tertiary-container: '#77859a'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#89f5e7'
  secondary-fixed-dim: '#6bd8cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#005049'
  tertiary-fixed: '#d5e3fc'
  tertiary-fixed-dim: '#b9c7df'
  on-tertiary-fixed: '#0d1c2e'
  on-tertiary-fixed-variant: '#3a485b'
  background: '#f8f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
  headline-sm:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 22px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-desktop: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

The design system establishes an operational, mission-critical utility environment for autonomous web journey orchestration. The target audience includes operations leads, QA engineers, workflow automation managers, and enterprise operators who require absolute clarity, high legibility, and deterministic feedback. 

The aesthetic is functional minimalism anchored in institutional discipline:
- Visual posture: Utilitarian, predictable, and calm. Eliminates cognitive friction through disciplined linear hierarchy.
- Tone: Explicit, objective, and plain-spoken. Translates technical telemetry (DOM state changes, selector timeouts, execution loops) into direct human operations without conversational jargon or emojis.
- Physicality: Completely flat structure. No drop shadows, no glassmorphism, no gradient fills, and no decorative elevation. Separation relies strictly on solid boundary borders, calibrated neutral surface contrast, and systematic spacing.

## Colors

The palette is composed entirely of solid, matte tones engineered to prevent screen fatigue and ensure strict WCAG AAA readability across dense data surfaces.

### Surface and Canvas Architecture
- Root Application Canvas: `#F8F9FA` (Soft off-white to eliminate glare).
- Primary Containers & Panels: `#FFFFFF` (Solid, completely opaque surface for cards, sheets, and tables).
- Secondary Recessed Surfaces: `#F1F3F5` (Subtle container wells, inactive tracks, and table headers).
- Border Hierarchy: `#E2E8F0` for interior dividers; `#CBD5E1` for structural component perimeters and interactive boundaries.

### Core Chromatics
- Primary Brand / Ink High: `#0F172A` (Deep slate navy for primary actions, critical headers, and high-emphasis text).
- Interactive Secondary: `#0D9488` (Deep teal for primary affordances, active navigation indicators, and verified execution anchors).
- Neutral / Inactive Slate: `#475569` (Medium slate for secondary labels, metadata, and structural outlines).

### Operational State Tokens
All state indicators are single-weight solids without ambient halos or gradient fills:
- Success / Verified: `#15803D` (Subdued forest green for successful transitions and resolved runs). Surface tint: `#DCFCE7`.
- Alert / Paused: `#B45309` (Amber ochre for interventions required, rate warnings, or retries). Surface tint: `#FEF3C7`.
- Danger / Failed: `#B91C1C` (Deep crimson for terminated runs, broken selectors, and fatal blocks). Surface tint: `#FEE2E2`.
- Informational / Active: `#0369A1` (Direct slate azure for current step focus). Surface tint: `#E0F2FE`.

## Typography

Typography relies on neutral, highly legible sans-serif metrics designed for technical dashboards. In code and production implementations, the stack falls back to the native OS font family (`system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif`). For raw values, steps, and selectors, an unadorned monospace typeface (`JetBrains Mono` or `ui-monospace`) is specified.

### Rules of Typesetting
- Punctuation & Copy: Avoid decorative typography, stylistic em dashes, and non-standard symbols. Use standard periods, hyphens, and colons.
- Voice & Tone: Clear, active verbs. Avoid abstract terms like "Resolving DOM node hierarchy"; use "Finding submit button on checkout page". Replace "Thread cycle timeout" with "Agent stopped: Page took too long to respond".
- Numeric Hierarchy: Data figures and run totals must use tabular numerals (`font-variant-numeric: tabular-nums`) to ensure vertical column alignment across runtime logs.

## Layout & Spacing

The layout model is strictly structural, modular, and linear. It accommodates dense informational layouts such as continuous journey run steps, live agent viewports, and assertion trees without spatial ambiguity.

### Grid Architecture
- Root Layout: Two-pane fixed/fluid architecture. A fixed 260px vertical utility sidebar combined with an unconstrained fluid content canvas.
- Desktop Multi-Column: Standard 12-column layout for dashboard overview screens with a fixed `1.5rem` (`24px`) gutter and `2rem` (`32px`) canvas margin.
- Content Density: Agent logs, journey step chains, and telemetry inspectors follow a single-axis vertical orientation to prevent horizontal tracking fatigue.

### Breakpoints and Adaptations
- Mobile (`< 768px`): The 260px sidebar collapses into a flat top bar. All two-pane splits (such as Agent Viewport vs Step Logs) stack vertically into full-width views. Canvas margins reduce to `1rem` (`16px`).
- Tablet (`768px - 1024px`): Sidebar collapses to an icon-and-label rail (64px width). Content matrices shift from 3 or 4 columns down to 2 columns.
- Desktop (`> 1024px`): Full two-column and three-column side-by-side inspection layouts enabled.

## Elevation & Depth

This system enforces a **strict zero-shadow policy**. Depth is created entirely through contrasting surface tones and crisp border perimeters.

### Flat Hierarchy Rules
- Base Layer: `#F8F9FA` serves as the canvas substrate.
- Panel Layer: Components, cards, tables, and inspection panes are solid `#FFFFFF` bounded by a 1px border of `#CBD5E1`.
- Recessed Elements: Input fields, log viewports, code displays, and table headers use `#F1F3F5` with a 1px `#E2E8F0` internal border.
- Overlays & Modals: Floating dialogs and popovers use `#FFFFFF` with an emphasized 2px solid boundary of `#0F172A`. No ambient blur, no backdrop blur filters, and no drop shadows. Scrims are solid `#0F172A` with a fixed opacity of 40%.
- Interactive States: Hover and focus depths are conveyed by border color shifts (e.g., changing from `#CBD5E1` to `#0F172A`) or background tone shifts to `#F1F3F5`, never by physical elevation or translation on the Z-axis.

## Shapes

The shape system utilizes restrained, compact corner radii (`4px` to `6px`) to reinforce an engineered, high-density look. Rounding is never purely decorative; it distinguishes discrete interactive boundaries from global container frameworks.

- Small Components (Buttons, Inputs, Badges, Tabs): `4px` (`0.25rem`).
- Containers & Cards (Panels, Step Containers, Viewport Frames): `6px` (`0.375rem`).
- Zero Radius: Code log terminal blocks, execution progress track bars, and status indicator strips maintain square `0px` edges for clean horizontal and vertical alignment.
- Pill Shapes: Prohibited. Status chips and badges must be rectangular with `4px` corners.

## Components

### Buttons
- Primary Button: Solid `#0F172A` background, white label, `4px` radius, 1px solid `#0F172A` border. Hover: `#1E293B`. Active: `#334155`.
- Secondary Button: Solid `#FFFFFF` background, `#0F172A` label, 1px solid `#CBD5E1` border. Hover: `#F1F3F5` background, `#0F172A` border.
- Accent Action (Run/Deploy): Solid `#0D9488` background, white label, 1px solid `#0F172A`. Hover: `#0F766E`.
- Destructive Button: Solid `#FFFFFF` background, `#B91C1C` label, 1px solid `#B91C1C` border. Hover: `#FEE2E2` background.
- Focus State: Visible 2px solid `#0F172A` outline offset by 2px. No glowing rings.

### Form Inputs & Selectors
- Standard Input: 36px height, solid `#FFFFFF` background, 1px solid `#CBD5E1` border, `4px` radius, text in `#0F172A`.
- Active/Focused Input: 1px solid `#0F172A` with a crisp 1px `#0F172A` inset boundary. No fuzzy halo.
- Disabled Input: Solid `#F1F3F5` background, `#94A3B8` border, `#64748B` text.

### Badges & Status Chips
- Height: 20px, uppercase `label-sm` typography, `4px` radius, 1px solid perimeter border.
- Success: `#DCFCE7` background, `#15803D` text, 1px solid `#86EFAC` border.
- Alert: `#FEF3C7` background, `#B45309` text, 1px solid `#FDE68A` border.
- Danger: `#FEE2E2` background, `#B91C1C` text, 1px solid `#FCA5A5` border.
- Neutral/Queued: `#F1F3F5` background, `#475569` text, 1px solid `#CBD5E1` border.

### Cards & Container Panels
- Structure: Background `#FFFFFF`, 1px solid `#CBD5E1` border, `6px` radius.
- Header: 48px fixed height, 1px solid `#E2E8F0` bottom border, padded `0.75rem` `1rem`.
- Padding: Internal container padding set to `1rem` or `1.5rem` without inset bevels.

### Lists & Data Tables
- Table Container: Completely flat with 1px external border `#CBD5E1`.
- Table Header: Solid `#F1F3F5` background, 1px solid `#CBD5E1` bottom border, `12px` medium bold text in `#475569`.
- Table Row: Alternating rows prohibited. All rows `#FFFFFF`. 1px solid `#E2E8F0` row divider. Row hover: `#F8F9FA`.

### Checkboxes & Radios
- Checkbox: 16x16px square, `2px` corner radius, 1px solid `#475569`. Checked: Solid `#0F172A` fill with a sharp white check glyph.
- Radio: 16x16px circle, 1px solid `#475569`. Checked: Solid `#FFFFFF` fill with an internal centered 8px solid `#0F172A` circle.

### Journey Execution Step List (Domain Specific)
- Vertical Linear Chain: Steps connect via a solid 2px vertical guide rule (`#CBD5E1`).
- Step Node Item: Left-hand 24px square sequence indicator (Number or solid monochrome icon). Right-hand content panel with `#FFFFFF` background, 1px solid `#CBD5E1` border, containing:
  - Header: Direct human action (e.g., "Click: Sign in button", "Wait for navigation to complete").
  - Target URL or Identifier: Highlighted in a compact monospace strip with `#F1F3F5` background and 1px `#E2E8F0` border.
- Live Running Step: Active step is marked by a solid 3px left border of `#0D9488` with `#F8FAFC` background.