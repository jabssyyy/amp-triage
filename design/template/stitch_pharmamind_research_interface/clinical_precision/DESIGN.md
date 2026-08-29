---
name: Clinical Precision
colors:
  surface: '#f4fafd'
  surface-dim: '#d4dbdd'
  surface-bright: '#f4fafd'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eef5f7'
  surface-container: '#e8eff1'
  surface-container-high: '#e2e9ec'
  surface-container-highest: '#dde4e6'
  on-surface: '#161d1f'
  on-surface-variant: '#404752'
  inverse-surface: '#2b3234'
  inverse-on-surface: '#ebf2f4'
  outline: '#707784'
  outline-variant: '#c0c7d4'
  surface-tint: '#0060a9'
  primary: '#005ea5'
  on-primary: '#ffffff'
  primary-container: '#0077ce'
  on-primary-container: '#fdfcff'
  inverse-primary: '#a2c9ff'
  secondary: '#006b55'
  on-secondary: '#ffffff'
  secondary-container: '#6dfad2'
  on-secondary-container: '#00725b'
  tertiary: '#006952'
  on-tertiary: '#ffffff'
  tertiary-container: '#008468'
  on-tertiary-container: '#f5fff9'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d3e4ff'
  primary-fixed-dim: '#a2c9ff'
  on-primary-fixed: '#001c38'
  on-primary-fixed-variant: '#004881'
  secondary-fixed: '#6dfad2'
  secondary-fixed-dim: '#4bddb7'
  on-secondary-fixed: '#002018'
  on-secondary-fixed-variant: '#005140'
  tertiary-fixed: '#63fbcf'
  tertiary-fixed-dim: '#3fdeb4'
  on-tertiary-fixed: '#002118'
  on-tertiary-fixed-variant: '#00513f'
  background: '#f4fafd'
  on-background: '#161d1f'
  surface-variant: '#dde4e6'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
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
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-bold:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  code-md:
    fontFamily: IBM Plex Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  edge-margin: 24px
  gutter: 16px
---

## Brand & Style

The design system is engineered for high-stakes antimicrobial research, where data integrity and clarity take precedence over decorative flair. The brand personality is clinical, analytical, and authoritative, reflecting the rigor of pharmaceutical drug discovery. 

The aesthetic is rooted in **Modern Corporate** principles with a focus on data density and utilitarian efficiency. It avoids the whimsical trends of consumer software, opting instead for a "Laboratory White" environment. The interface utilizes high-quality whitespace and structural alignment to reduce cognitive load during the analysis of complex peptide sequences and chemical properties. The emotional response is one of calm focus and professional reliability.

## Colors

The palette is anchored by a neutral foundation of off-white and charcoal to ensure maximum legibility for long-duration research sessions. 

- **Primary Blue (#0984E3):** Reserved for primary actions, active states, and navigational focus.
- **Teal & Green (#00B894, #55EFC4):** Used for functional signaling, such as "Success" states, compound stability, or validated results.
- **Neutral Charcoal (#2D3436):** Used for all body text and primary headers to maintain high contrast.
- **Surface Strategy:** The global background is a soft off-white (`#F8F9FA`), while active work surfaces, cards, and data tables are pure white (`#FFFFFF`) to create a clear "layering" of information without using shadows.

## Typography

This design system uses **Inter** for all UI elements to provide a systematic and neutral reading experience. For scientific data, specifically peptide sequences and chemical strings, **IBM Plex Mono** is employed to ensure character alignment and prevent misinterpretation of similar glyphs.

Typography is scaled for high information density. While headlines provide necessary hierarchy, the majority of the interface operates at the `body-md` (14px) and `body-sm` (12px) levels. The use of uppercase `label-bold` tokens is intended for table headers and metadata categories to differentiate them from dynamic research data.

## Layout & Spacing

The layout utilizes a **Fixed Grid** model for analytical dashboards to ensure consistent data visualization across desktop monitors (the primary target device). 

- **Grid:** A 12-column grid with 16px gutters.
- **Density:** Spacing is compact. A 4px base unit (0.25rem) allows for tight alignment in complex data tables and sidebars.
- **Responsive Behavior:** On tablet devices, the sidebars collapse into icons to preserve the central "Stage" where research data is visualized. This design system is not intended for mobile phone use due to the complexity of the data models.

## Elevation & Depth

This design system avoids shadows in favor of **Low-Contrast Outlines**. Depth is communicated through structural partitioning rather than simulated lighting.

1.  **Surfaces:** The primary background uses `#F8F9FA`. Secondary work containers (tables, inspector panels) use white `#FFFFFF`.
2.  **Borders:** All containers are defined by a `1px solid #E1E4E8` border.
3.  **Active State:** Interaction is indicated by changing the border color to the Primary Blue (`#0984E3`) rather than increasing elevation.
4.  **No Blurs:** Transparent effects and background blurs are strictly prohibited to maintain maximum contrast and readability for clinical data.

## Shapes

The shape language is conservative and geometric. A **Soft** roundedness (6px-8px) is applied to buttons and primary containers to modernise the tool without appearing "playful." 

- **Small Components (Checkboxes, Tags):** Use 4px radius.
- **Standard Containers (Cards, Inputs):** Use 6px radius.
- **Layout Shells:** Use 0px radius for screen-edge panels (e.g., sidebars) to maintain a professional, architectural feel.

## Components

- **Buttons:** Use flat fills for primary actions (`#0984E3` with white text). Secondary actions use a white background with a `#E1E4E8` border. No gradients or inner shadows.
- **Data Tables:** These are the core of the system. Use alternating row zebra-striping (Off-white/White) for high-density tables. Headers must use the `label-bold` typography token.
- **Input Fields:** Use 1px solid borders. On focus, the border shifts to Primary Blue with a subtle 2px outer glow in a highly transparent blue (non-blur).
- **Chips/Tags:** Used for compound attributes. Use a light grey background (`#F1F3F5`) with `body-sm` text. Functional tags (e.g., "Toxic", "Stable") use muted green or red backgrounds with high-contrast text.
- **Monospace Cells:** Any cell containing a peptide or DNA sequence must be wrapped in a `code-md` container with horizontal scroll enabled to prevent wrapping.
- **Status Indicators:** Use small 8px solid circles (pills) in Teal, Green, or Amber to denote experimental status.