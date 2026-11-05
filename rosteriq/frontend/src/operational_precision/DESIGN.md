---
name: Operational Precision
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
  tertiary: '#004d70'
  on-tertiary: '#ffffff'
  tertiary-container: '#006693'
  on-tertiary-container: '#b8e0ff'
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
  tertiary-fixed: '#c9e6ff'
  tertiary-fixed-dim: '#89ceff'
  on-tertiary-fixed: '#001e2f'
  on-tertiary-fixed-variant: '#004c6e'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
  data-tabular-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  data-tabular-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
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
  gutter-sm: 0.5rem
  gutter-lg: 1.5rem
  margin: 1.5rem
  margin-mobile: 0.75rem
  space-xs: 0.25rem
  space-sm: 0.375rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system embodies high-density, mission-critical operational planning for complex enterprise teams. Drawing heavily from contemporary utilitarian B2B paradigms (shadcn/ui precision, Linear-like clarity, and dense spreadsheet ergonomics), the interface prioritizes immediate legibility, zero-latency feedback, and uncompromising structure. 

The emotional tone is calm, authoritative, and frictionless. Users manage round-the-clock schedules, complex compliance rules, and workforce allocation under dynamic constraints; the interface eliminates visual noise in favor of hairline structural separators, precise status micro-tokens, and scannable tabular typography. High data density is balanced by a deep slate canvas and an assertive, deep-indigo control rail that anchors the workspace.

## Colors

The color system delivers high contrast across complex grids while preserving strict semantic categorization for workforce allocations.

### Foundations & Surfaces
- **Canvas Base**: `#F8FAFC` (Slate 50) provides a soft, low-glare backdrop that frames white data tables.
- **Card & Grid Surface**: `#FFFFFF` for primary interaction panels, cells, and modals.
- **Grid Dividers & Hairlines**: `#E2E8F0` (Slate 200) strictly applied at 1px thickness for cell and structural borders.
- **Row Hover & Selection**: `#F1F5F9` (Slate 100) for ephemeral grid states.
- **Sidebar Rail**: `#1E1B4B` (Indigo 950) establishing structural hierarchy, paired with `#C7D2FE` (Indigo 200) for navigation labels and icons.

### Text Levels
- **Text Primary**: `#0F172A` (Slate 900) for critical labels, table headers, and employee identifiers.
- **Text Secondary**: `#475569` (Slate 600) for sub-metrics, role badges, and secondary attributes.
- **Text Muted**: `#64748B` (Slate 500) for timestamps, keyboard shortcuts, and empty states.

### Primary Action Tints
- **Primary Action**: `#4F46E5` (Indigo 600) for primary command triggers and focus rings.
- **Primary Hover**: `#4338CA` (Indigo 700).
- **Primary Soft Tint**: `#EEF2FF` (Indigo 50) for selected row highlights and primary chips.

### Roster Status System (Fixed Semantics)
Status tokens use paired foreground and background coordinates with minimum 4.5:1 contrast compliance:
- **Working / Covered (`W`)**: Background `#DCFCE7`, Text `#15803D`
- **Coverage Gap / Critical (`!`)**: Background `#FEE2E2`, Text `#B91C1C`
- **Warning / Pending Review (`?`)**: Background `#FEF3C7`, Text `#B45309`
- **Backup Support (`B`)**: Background `#DBEAFE`, Text `#1D4ED8`
- **Holiday Duty (`H`)**: Background `#DBEAFE`, Text `#1D4ED8`
- **Approved Leave (`L`)**: Background `#EDE9FE`, Text `#6D28D9`
- **Compensatory Off (`CO`)**: Background `#CFFAFE`, Text `#0E7490`
- **Weekly Off / Closed (`WO`)**: Background `#F1F5F9`, Text `#475569`

## Typography

The typography structure leverages **Inter** for all UI body copy, forms, and grid contents, combined with **Plus Jakarta Sans** for dashboard section titles and high-level headers.

All grid cells, timestamps, metrics, and workforce calculations MUST use OpenType feature settings: `font-feature-settings: "tnum" on, "cv02" on, "cv03" on, "cv04" on`. This guarantees tabular digit alignment across dense shift columns, preventing layout drift when numbers update dynamically.

## Layout & Spacing

The application utilizes an edge-to-edge application frame consisting of a fixed, collapsible utility rail on the left (64px collapsed, 240px expanded) and a fluid viewport container for the roster canvas.

### Grid & Density Hierarchy
- **Canvas Layout**: Fluid horizontal allocation with strict minimum width boundaries per shift cell (minimum `88px` desktop, `64px` compact view).
- **Roster Table System**: Sticky dual-axes (pinned left 2 columns for employee name/metadata, pinned top row for date/shift timeline headers).
- **Vertical Rhythm**: Base row height fixed at `40px` (Dense Mode) or `48px` (Standard Mode). Gaps inside cells are fixed to `space-xs` (4px) to retain maximum content density without clipping.
- **Adaptive Breakpoints**:
  - `Desktop (>1280px)`: Full multi-week matrix view with persistent metadata drawer.
  - `Tablet (768px - 1279px)`: 7-day rolling window view; drawer transforms to slide-over panel.
  - `Mobile (<767px)`: Day-by-day swipe timeline; column matrix collapses into vertical list cards with horizontal shift indicators.

## Elevation & Depth

Visual hierarchy uses **low-contrast hairlines** and **subtle ambient shadows**, avoiding heavy elevations that disrupt dense data reading.

- **Level 0 (Base Canvas)**: No shadow. Pure `#F8FAFC` background.
- **Level 1 (Cards, Cell Matrix, Toolbars)**: 1px continuous border in `#E2E8F0` with zero shadow.
- **Level 2 (Dropdowns, Shift Pickers, Popovers)**: 1px border `#E2E8F0`, shadow `0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.05)`.
- **Level 3 (Command Palette, Modals, Slide-overs)**: 1px border `#E2E8F0`, shadow `0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.05)`.
- **Pinned Column & Row Separators**: 1px vertical/horizontal divider accented with a subtle right/bottom drop: `inset -1px 0 0 #E2E8F0` to distinguish scrollable boundaries.

## Shapes

The interface adopts a controlled, modern micro-radius profile (`roundedness: 1`). 

- **Containers & Cards**: `rounded-md` (6px) or `rounded-lg` (8px).
- **Data Cells**: `0px` radius along cell perimeters to maintain uninterrupted grid line continuums.
- **Status Badges & Shift Pills**: `rounded` (4px) to balance readable text containment with compact cell padding.
- **Inputs & Buttons**: `rounded-md` (6px) aligned with the shadcn/ui aesthetic.

## Components

### Buttons
- **Primary**: Background `#4F46E5`, hover `#4338CA`, text `#FFFFFF`, height `32px` (compact) or `36px` (regular), font weight `500`. Shadow: `0 1px 2px 0 rgba(0, 0, 0, 0.05)`.
- **Secondary / Outline**: Background `#FFFFFF`, border `1px solid #E2E8F0`, text `#0F172A`, hover background `#F8FAFC`.
- **Ghost**: Background transparent, hover background `#F1F5F9`, text `#475569`.
- **Focus Rings**: `box-shadow: 0 0 0 2px #FFFFFF, 0 0 0 4px #4F46E5`.

### Status Pills & Shift Tags
- High-contrast badges displaying code + optional title (e.g., `W • 09:00 - 17:00`).
- Padding: `2px 6px` inside cells. Height: `22px`.
- Typography: `data-tabular-sm` (11px or 12px, weight 600).
- Borders: `1px solid` matching 20% opacity of token text color for contrast refinement against white cells.

### Grid Matrix Cells
- Dimensions: Height `40px` (dense) or `48px` (default); minimum width `88px`.
- Border: `1px solid #E2E8F0` on bottom and right edges.
- States:
  - Default: `#FFFFFF`.
  - Hover: `#F1F5F9`.
  - Multi-select drag: `#EEF2FF` with `1px dashed #4F46E5` outline.
  - Conflict overlay: Soft diagonal hatching overlay using `#FEE2E2` and `#B91C1C`.

### Form Controls & Inputs
- **Text Inputs**: Height `32px`, border `1px solid #E2E8F0`, radius `6px`, font size `13px`. Placeholder `#64748B`.
- **Checkboxes & Radios**: 16x16px, border `#CBD5E1`, checked background `#4F46E5` with crisp white checkmark.

### Cards & Summary KPI Blocks
- Background `#FFFFFF`, border `1px solid #E2E8F0`, padding `12px 16px`.
- Metric numbers rendered in `Plus Jakarta Sans` 20px, label in `Inter` 12px muted text (`#64748B`).