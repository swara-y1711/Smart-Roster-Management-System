---
name: RosterIQ System
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#464555'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#777587'
  outline-variant: '#c7c4d8'
  surface-tint: '#4d44e3'
  primary: '#3525cd'
  on-primary: '#ffffff'
  primary-container: '#4f46e5'
  on-primary-container: '#dad7ff'
  inverse-primary: '#c3c0ff'
  secondary: '#5b598c'
  on-secondary: '#ffffff'
  secondary-container: '#c7c3fe'
  on-secondary-container: '#514f81'
  tertiary: '#004f64'
  on-tertiary: '#ffffff'
  tertiary-container: '#006983'
  on-tertiary-container: '#a5e5ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e2dfff'
  primary-fixed-dim: '#c3c0ff'
  on-primary-fixed: '#0f0069'
  on-primary-fixed-variant: '#3323cc'
  secondary-fixed: '#e3dfff'
  secondary-fixed-dim: '#c4c1fb'
  on-secondary-fixed: '#181445'
  on-secondary-fixed-variant: '#444173'
  tertiary-fixed: '#b9eaff'
  tertiary-fixed-dim: '#81d1f0'
  on-tertiary-fixed: '#001f29'
  on-tertiary-fixed-variant: '#004d62'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  kpi-display:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
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
  nav-link:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '500'
    lineHeight: 22px
  table-body:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  table-header:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0.02em
  label-badge:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-dense: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system targets modern enterprise operations directors, resource managers, and departmental planners who oversee complex workforce schedules. The visual tone balances administrative authority with airy, cognitive ease: structured, disciplined, and frictionless under heavy data loads. 

The aesthetic adheres to **Corporate / Modern** principles elevated by crisp micro-geometry and refined informational density. Rather than overwhelming the user with utilitarian spreadsheets, the interface uses deliberate spatial breathing room, distinct status signifiers, and deep indigo anchor surfaces to establish visual calm and situational awareness across high-stakes planning sessions.

## Colors

The palette operates under a strict operational taxonomy to prevent cognitive overload across dense grids:

- **Canvas & Structural Surfaces**: Application backdrop `#F8FAFC`, elevated container cards `#FFFFFF`, and dividing borders `#E2E8F0`. Table row hover interactions trigger a subtle state change to `#F1F5F9`.
- **Text & Hierarchy**: Primary labels and values leverage high-contrast Slate `#0F172A`, secondary descriptive labels utilize `#475569`, and supplemental metadata settles back at `#64748B`.
- **Primary Brand Interactive**: `#4F46E5` drives primary CTAs, active focus indicators, and selections, shifting to `#4338CA` on hover, with `#EEF2FF` serving as the base soft tint.
- **Navigation Shell**: A commanding dark indigo `#1E1B4B` grounds the global left sidebar, populated by `#C7D2FE` default navigation items and crisp `#FFFFFF` labels on a `#312E81` active fill.
- **Roster Operational Status Codes**:
  - `W` (Working): Background `#DCFCE7`, text `#15803D`
  - `!` (Error / Under-allocated Gap): Background `#FEE2E2`, text `#B91C1C`
  - `?` (Warning / Pending Shift): Background `#FEF3C7`, text `#B45309`
  - `B` & `H` (Backup / Public Holiday): Background `#DBEAFE`, text `#1D4ED8`
  - `L` (Leave / Absence): Background `#EDE9FE`, text `#6D28D9`
  - `CO` (Compensatory Off): Background `#CFFAFE`, text `#0E7490`
  - `WO` (Weekly Off): Background `#F1F5F9`, text `#475569`

## Typography

The typography couples the structured geometry of **Plus Jakarta Sans** for headlines and metrics with the functional clarity of **Inter** for dense transactional tables and navigation.

- Heading tiers provide strong hierarchical anchors; metrics and operational KPI counters utilize the high-impact display weight (`32px` desktop, bold) to allow rapid scanning.
- Data tables maintain readability by locking body content to `14px` and upper column headers to uppercase `13px` with subtle tracking.
- Status badges use bold `12px` glyphs with uppercase tracking to ensure single and two-letter status indicators remain unambiguous at a glance.

## Layout & Spacing

The interface accommodates desktop operational environments optimized for viewport widths between `1440px` and `1600px`:

- **Layout Structure**: Employs a persistent navigation column (`260px` fixed width) alongside a fluid data canvas spanning the remainder of the viewport. Top-level workbench sections observe an outer content margin of `2rem` (32px).
- **Rhythm & Grid**: Layout elements align to a strict 8px base rhythm. Content blocks and roster matrices utilize a 12-column fluid grid connected by `1.5rem` (24px) gutters.
- **Roster & Data Grid Dimensions**: Data grid rows are strictly bounded to `44px` (dense) and `48px` (comfortable) heights to ensure vertical scanning stability. Table cells enforce horizontal padding of `1rem` (16px).
- **Surface Spacing**: Analytical cards and summary modules utilize an internal padding of `1.5rem` (24px), preserving visual separation between high-density metrics.

## Elevation & Depth

Visual hierarchy relies on crisp borders and low-contrast surface elevation to avoid visual noise across complex multi-column matrices:

- **Level 0 (Base Canvas)**: Background `#F8FAFC`, flat.
- **Level 1 (Card & Panel Surface)**: Surface `#FFFFFF` bordered with a 1px solid hairline divider of `#E2E8F0`. Accompanied by a subtle ambient shadow: `0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.02)`.
- **Level 2 (Dropdowns, Popovers, & Cell Overlays)**: Surface `#FFFFFF`, border `#CBD5E1`, with elevation shadow: `0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.04)`.
- **Level 3 (Modal Shift Drawers & Flyouts)**: Surface `#FFFFFF`, border-left `#E2E8F0`, with deep directional depth: `0 20px 25px -5px rgba(15, 23, 42, 0.12), 0 8px 10px -6px rgba(15, 23, 42, 0.04)`.

## Shapes

The design system incorporates a disciplined, low-radius shape profile (`roundedness: 1`) to preserve maximum data density and convey architectural reliability:

- Standard controls, text fields, badges, and calendar grid cells enforce a default radius of `0.25rem` (4px).
- Container cards, dashboards, and major panel segments apply a `rounded-lg` radius of `0.5rem` (8px).
- Operational status pills and user profile avatars remain the sole circular exceptions, utilizing full `9999px` radii to distinguish them immediately from rectilinear interactive inputs.

## Components

### Buttons
- **Primary**: Solid `#4F46E5` background, `#FFFFFF` text, 0.25rem corner radius, 8px 16px padding. Hover state deepens to `#4338CA`. Active state scales down to 98% with an indigo focus ring (`box-shadow: 0 0 0 3px #EEF2FF`).
- **Secondary**: `#FFFFFF` background, `#0F172A` text, 1px solid `#E2E8F0` border. Hover state switches to `#F8FAFC` and border `#CBD5E1`.
- **Tertiary / Ghost**: Transparent fill, `#475569` text. Hover state switches to `#F1F5F9`.

### Status Badges & Roster Cell Chips
- **Geometry**: Compact tags measuring 24px in height with an inset radius of 4px or pill format.
- **Variants**:
  - `W`: Background `#DCFCE7`, Text `#15803D`
  - `!`: Background `#FEE2E2`, Text `#B91C1C`, weight bold
  - `?`: Background `#FEF3C7`, Text `#B45309`, weight bold
  - `B` / `H`: Background `#DBEAFE`, Text `#1D4ED8`
  - `L`: Background `#EDE9FE`, Text `#6D28D9`
  - `CO`: Background `#CFFAFE`, Text `#0E7490`
  - `WO`: Background `#F1F5F9`, Text `#475569`

### Form Controls & Inputs
- **Text Fields**: Height 40px, background `#FFFFFF`, border 1px solid `#E2E8F0`, padding 8px 12px. Text color `#0F172A` (14px). Focus triggers border color `#4F46E5` with an indigo halo (`box-shadow: 0 0 0 3px #EEF2FF`).
- **Checkboxes & Radios**: 16px × 16px frame, border `#CBD5E1`. Selected state applies `#4F46E5` fill with crisp `#FFFFFF` check iconography.

### Cards & Analytical Panels
- White background (`#FFFFFF`), encased in a 1px border (`#E2E8F0`) with `0.5rem` (8px) radius and uniform `24px` padding. Headers contain a bold `18px` or `20px` title anchored against top-right secondary controls.

### Tables & Roster Matrix
- Headers maintain a `40px` vertical profile, filled with `#F8FAFC`, uppercase tracked `13px` `#475569` labels, and bottom border `#E2E8F0`.
- Data rows enforce strict `44px` to `48px` heights. Default background `#FFFFFF`, transitioning cleanly to `#F1F5F9` on cursor hover. Border dividers between rows sit at 1px `#E2E8F0`.