# Design System: Everest Capital / BidDeed.AI + ZoneWise.AI

## 1. Visual Theme & Atmosphere

Everest Capital's dual-product ecosystem — BidDeed.AI (foreclosure auctions) and ZoneWise.AI (zoning intelligence) — presents as a dark-mode-native fintech platform where data density meets investor-grade confidence. The foundation is a deep navy canvas (`#1E3A5F`) paired with a warm amber accent (`#F59E0B`) that functions as the system's heartbeat — every interactive element, every call-to-action, every data highlight pulses in this orange-gold. The overall impression is of a Bloomberg terminal redesigned for real estate intelligence: serious, data-rich, and unmistakably premium.

The typography is built entirely on Inter Variable with OpenType features `"cv01"` and `"ss03"` enabled globally. Inter was chosen for its exceptional legibility at small sizes — critical for data-dense parcel tables, auction listings, and zoning overlays. At display sizes (48px-64px), Inter runs at weight 600 with aggressive negative letter-spacing (-1.2px at 64px), creating compressed, authoritative headlines that signal institutional confidence. At body sizes, weight 400 provides clean readability while weight 500 marks navigation and labels. JetBrains Mono serves as the monospace companion for parcel IDs, legal descriptions, and financial data, with tabular numerals (`"tnum"`) for all numerical displays.

What distinguishes Everest's visual system is the deliberate tension between the cold authority of navy and the warm urgency of amber. Navy dominates — backgrounds, headings, containers — establishing trust and permanence. Amber appears sparingly but decisively: primary CTAs, active states, data highlights, progress indicators. This restraint is intentional. In a domain where users are making six-figure auction decisions, the UI must feel stable (navy) while clearly signaling actionable elements (amber). The shadow system uses navy-tinted layers (`rgba(30,58,95,0.25)`) that extend the brand into depth, keeping elevation on-palette.

The two products share a unified design language but are distinguished by subtle theming: ZoneWise.AI leans into choropleth map interfaces with muted earth tones for zoning layers, while BidDeed.AI emphasizes tabular auction data with amber highlights on winning bids and deadline urgency. Both products always appear together — the PAIRING RULE is absolute.

**Key Characteristics:**
- Dark-mode-native: Navy `#1E3A5F` as primary background, `#0F2440` for deepest surfaces, `#2A4A6B` for elevated panels
- Inter Variable with `"cv01", "ss03"` globally — geometric alternates for maximum data legibility
- Weight 600 for display headlines, 500 for navigation/labels, 400 for body — no light weights
- Aggressive negative letter-spacing at display sizes (-1.2px at 64px, -0.8px at 48px)
- Amber `#F59E0B` as the ONLY chromatic accent — every interactive element, every CTA, every highlight
- Navy-tinted multi-layer shadows using `rgba(30,58,95,0.25)` — elevation that feels brand-colored
- JetBrains Mono for all monospace: parcel IDs, legal descriptions, financial data
- Tabular numerals (`"tnum"`) mandatory for all numerical displays
- Conservative border-radius (6px-8px) — professional, not playful
- Dual-product theming: ZoneWise = map/choropleth emphasis, BidDeed = table/auction emphasis

## 2. Color Palette & Roles

### Primary Brand
- **Everest Navy** (`#1E3A5F`): Primary brand color, page backgrounds, header backgrounds, card surfaces. The foundational color of the entire ecosystem.
- **Everest Amber** (`#F59E0B`): Primary accent, CTAs, links, active states, data highlights, progress bars. The ONLY warm color in the system.
- **Pure White** (`#FFFFFF`): Text on dark backgrounds, card surfaces in light contexts.

### Navy Scale (Dark Surfaces)
- **Navy Deepest** (`#0F2440`): Darkest background — sidebar, modal overlays, immersive sections.
- **Navy Primary** (`#1E3A5F`): Standard page background, primary canvas.
- **Navy Elevated** (`#2A4A6B`): Elevated surfaces — cards, dropdowns, tooltips on dark backgrounds.
- **Navy Light** (`#3B5E80`): Subtle borders on dark surfaces, divider lines.
- **Navy Muted** (`#4A7194`): Disabled states, placeholder text on dark backgrounds.

### Amber Scale (Accent)
- **Amber Primary** (`#F59E0B`): Primary CTA backgrounds, link text, active indicators.
- **Amber Hover** (`#D97706`): Hover state for primary CTAs — darker, more urgent.
- **Amber Light** (`#FCD34D`): Highlight backgrounds, selected row indicators, badge backgrounds.
- **Amber Pale** (`rgba(245,158,11,0.15)`): Subtle amber tint for hover states on dark surfaces.
- **Amber Deep** (`#B45309`): Pressed/active state for CTAs.

### Text Colors
- **Text Primary** (`#F8FAFC`): Near-white primary text on dark backgrounds.
- **Text Secondary** (`#CBD5E1`): Body text, descriptions on dark backgrounds.
- **Text Tertiary** (`#94A3B8`): Metadata, timestamps, de-emphasized content.
- **Text Disabled** (`#64748B`): Disabled labels, placeholder text.
- **Text Dark** (`#1E293B`): Primary text on light/white surfaces.
- **Text Dark Secondary** (`#475569`): Secondary text on light surfaces.

### Status Colors
- **Success** (`#10B981`): Successful bids, verified parcels, active status.
- **Success Background** (`rgba(16,185,129,0.15)`): Success badge/row backgrounds.
- **Warning** (`#F59E0B`): Deadline approaching, attention needed (shares amber accent).
- **Warning Background** (`rgba(245,158,11,0.15)`): Warning badge backgrounds.
- **Error** (`#EF4444`): Failed bids, validation errors, overdue items.
- **Error Background** (`rgba(239,68,68,0.15)`): Error badge/row backgrounds.
- **Info** (`#3B82F6`): Informational badges, neutral status indicators.

### Surface & Borders
- **Border Default** (`rgba(255,255,255,0.08)`): Standard border on dark surfaces.
- **Border Subtle** (`rgba(255,255,255,0.05)`): Ultra-subtle dividers.
- **Border Emphasis** (`rgba(255,255,255,0.12)`): Prominent borders, input focus (non-amber).
- **Border Amber** (`rgba(245,158,11,0.4)`): Active/selected state borders.
- **Surface Overlay** (`rgba(15,36,64,0.85)`): Modal/dialog backdrop.

### Shadow Colors
- **Shadow Navy** (`rgba(30,58,95,0.25)`): Primary shadow — navy-tinted for brand coherence.
- **Shadow Deep** (`rgba(15,36,64,0.35)`): Deep shadow for modals, elevated panels.
- **Shadow Black** (`rgba(0,0,0,0.15)`): Secondary shadow layer for depth reinforcement.
- **Shadow Amber Glow** (`rgba(245,158,11,0.15)`): Subtle amber glow on hover for CTAs.

### ZoneWise Choropleth Layers
- **Zone Residential** (`#4ADE80`): Residential zoning overlay.
- **Zone Commercial** (`#60A5FA`): Commercial zoning overlay.
- **Zone Industrial** (`#A78BFA`): Industrial zoning overlay.
- **Zone Agricultural** (`#FBBF24`): Agricultural zoning overlay.
- **Zone Mixed Use** (`#F472B6`): Mixed-use zoning overlay.
- **Zone PUD** (`#2DD4BF`): Planned Unit Development overlay.

## 3. Typography Rules

### Font Family
- **Primary**: `Inter Variable`, with fallbacks: `SF Pro Display, -apple-system, system-ui, Segoe UI, Roboto, Helvetica Neue, sans-serif`
- **Monospace**: `JetBrains Mono`, with fallbacks: `SF Mono, Menlo, Consolas, monospace`
- **OpenType Features**: `"cv01", "ss03"` enabled globally on Inter. `"tnum"` for all numerical data.

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Features | Notes |
|------|------|------|--------|-------------|----------------|----------|-------|
| Display XL | Inter Variable | 64px (4.00rem) | 600 | 1.00 (tight) | -1.2px | cv01, ss03 | Hero headlines, landing page |
| Display Large | Inter Variable | 48px (3.00rem) | 600 | 1.05 (tight) | -0.8px | cv01, ss03 | Section headlines |
| Display | Inter Variable | 36px (2.25rem) | 600 | 1.10 (tight) | -0.6px | cv01, ss03 | Feature section titles |
| Heading 1 | Inter Variable | 28px (1.75rem) | 600 | 1.15 | -0.4px | cv01, ss03 | Card headers, panel titles |
| Heading 2 | Inter Variable | 22px (1.38rem) | 600 | 1.20 | -0.2px | cv01, ss03 | Sub-sections, table headers |
| Heading 3 | Inter Variable | 18px (1.13rem) | 600 | 1.25 | -0.1px | cv01, ss03 | Compact headings, sidebar titles |
| Body Large | Inter Variable | 16px (1.00rem) | 400 | 1.60 | normal | cv01, ss03 | Descriptions, feature text |
| Body | Inter Variable | 14px (0.88rem) | 400 | 1.55 | normal | cv01, ss03 | Standard reading text |
| Body Medium | Inter Variable | 14px (0.88rem) | 500 | 1.55 | normal | cv01, ss03 | Navigation, labels, emphasis |
| Small | Inter Variable | 13px (0.81rem) | 400 | 1.50 | normal | cv01, ss03 | Metadata, timestamps |
| Caption | Inter Variable | 12px (0.75rem) | 500 | 1.40 | 0.2px | cv01, ss03 | All-caps labels, overlines |
| Micro | Inter Variable | 11px (0.69rem) | 500 | 1.35 | 0.3px | cv01, ss03 | Tiny labels, badge text |
| Data Large | JetBrains Mono | 20px (1.25rem) | 500 | 1.20 | normal | tnum | Large financial figures, bid amounts |
| Data Body | JetBrains Mono | 14px (0.88rem) | 400 | 1.50 | normal | tnum | Parcel IDs, table data, prices |
| Data Small | JetBrains Mono | 12px (0.75rem) | 400 | 1.40 | normal | tnum | Compact data, timestamps |
| Code | JetBrains Mono | 13px (0.81rem) | 400 | 1.60 | normal | -- | Code blocks, API responses |

### Principles
- **Weight 600 for all headings** — Everest headlines are bold and commanding, the opposite of light-weight trends. In a domain of financial decisions, authority comes from weight.
- **cv01 + ss03 everywhere** — The alternate lowercase 'a' (single-story) and adjusted letterforms give Inter a cleaner, more geometric feel that matches the data-density of the product.
- **tnum for all numbers** — Every price, every parcel ID, every bid amount uses tabular numerals for perfect column alignment. Non-negotiable.
- **JetBrains Mono for financial data** — Not just code blocks but any structured data: parcel numbers, legal descriptions, bid amounts, coordinates. This signals "this is precise, machine-verified data."
- **Negative letter-spacing at display only** — Body text breathes normally. Only display sizes (36px+) use compressed tracking.

## 4. Component Stylings

### Buttons

**Primary (Amber)**
- Background: `#F59E0B`
- Text: `#1E293B` (dark text on amber for contrast)
- Padding: `10px 20px`
- Border-radius: `6px`
- Font: Inter Variable, 14px, weight 500
- Hover: `#D97706` background, `box-shadow: 0 0 0 3px rgba(245,158,11,0.3)`
- Active: `#B45309` background
- Disabled: `#F59E0B` at 40% opacity, no pointer events
- Transition: `background 0.15s, box-shadow 0.15s`

**Secondary (Ghost/Outline)**
- Background: `transparent`
- Text: `#F8FAFC`
- Border: `1px solid rgba(255,255,255,0.12)`
- Padding: `10px 20px`
- Border-radius: `6px`
- Hover: `rgba(255,255,255,0.05)` background
- Active: `rgba(255,255,255,0.08)` background

**Danger**
- Background: `#EF4444`
- Text: `#FFFFFF`
- Hover: `#DC2626`
- Same sizing as primary

### Cards & Containers

**Standard Card (Dark)**
- Background: `#2A4A6B`
- Border: `1px solid rgba(255,255,255,0.08)`
- Border-radius: `8px`
- Padding: `24px`
- Shadow: `rgba(30,58,95,0.25) 0px 20px 40px -20px, rgba(0,0,0,0.15) 0px 10px 20px -10px`

**Elevated Card**
- Same as standard but shadow at Level 3
- Border: `1px solid rgba(255,255,255,0.12)`

**Auction Card (BidDeed-specific)**
- Standard card base
- Left border accent: `3px solid #F59E0B` for active auctions
- Left border accent: `3px solid #EF4444` for deadline < 24h
- Left border accent: `3px solid #10B981` for won auctions
- Timer badge: amber background, dark text, JetBrains Mono

**Parcel Card (ZoneWise-specific)**
- Standard card base
- Zoning badge in top-right with zone-specific color
- Map thumbnail with `border-radius: 6px` clip

### Badges / Tags / Pills

**Status Badge**
- Padding: `2px 8px`
- Border-radius: `4px`
- Font: Inter Variable, 11px, weight 500
- Variants use status color at 15% opacity for background, full color for text, 40% for border

**Zoning Badge**
- Same sizing as status badge
- Uses ZoneWise choropleth colors
- Background at 20% opacity, text at full color

### Inputs & Forms

**Text Input (Dark)**
- Background: `rgba(255,255,255,0.05)`
- Border: `1px solid rgba(255,255,255,0.08)`
- Border-radius: `6px`
- Padding: `10px 14px`
- Text: `#F8FAFC`
- Placeholder: `#64748B`
- Focus: `border-color: #F59E0B; box-shadow: 0 0 0 3px rgba(245,158,11,0.15)`
- Font: Inter Variable, 14px, weight 400

**Search Input**
- Same as text input
- Left icon (magnifying glass) at `#94A3B8`
- Keyboard shortcut badge (⌘K) in right side

### Navigation

**Top Navigation**
- Background: `#0F2440` with `backdrop-filter: blur(12px)`
- Height: `64px`
- Logo: Left-aligned, Inter Variable, 18px, weight 600, `#F8FAFC`
- Nav links: Inter Variable, 14px, weight 500, `#CBD5E1`
- Active link: `#F59E0B` text with `rgba(245,158,11,0.1)` background pill
- CTA button: Amber primary, right-aligned

**Sidebar**
- Background: `#0F2440`
- Width: `260px`
- Active item: `rgba(245,158,11,0.1)` background, `#F59E0B` left border (3px)
- Inactive item: `#CBD5E1` text, no background
- Section headers: Inter Variable, 11px, weight 500, `#64748B`, uppercase, 0.5px tracking

### Data Tables

- Header: `#0F2440` background, Inter Variable 12px weight 500, `#94A3B8`, uppercase, 0.3px tracking
- Row: `#1E3A5F` background, alternating with `rgba(255,255,255,0.02)`
- Row hover: `rgba(245,158,11,0.05)` background
- Selected row: `rgba(245,158,11,0.1)` background, left border `3px solid #F59E0B`
- Cell text: Inter Variable 14px weight 400, `#F8FAFC`
- Numeric cells: JetBrains Mono 14px, `"tnum"`, right-aligned
- Border between rows: `1px solid rgba(255,255,255,0.05)`

## 5. Layout Principles

### Spacing System
| Token | Value | Use |
|-------|-------|-----|
| xs | 4px | Icon padding, tight gaps |
| sm | 8px | Compact element spacing |
| md | 12px | Standard gap, form spacing |
| lg | 16px | Card padding, section gaps |
| xl | 24px | Section padding, card internal |
| 2xl | 32px | Major section spacing |
| 3xl | 48px | Page-level section breaks |
| 4xl | 64px | Hero sections, major breaks |

### Grid & Container
- **Max content width**: `1280px`
- **Dashboard grid**: 12-column, `16px` gap
- **Sidebar + content**: `260px fixed` + `1fr fluid`
- **Card grid**: `repeat(auto-fill, minmax(320px, 1fr))` with `16px` gap
- **Auction listing**: Single column, full width rows
- **Map + panel split**: `60% map` + `40% panel` (ZoneWise split-screen)

### Whitespace Philosophy
Data-dense but never cluttered. The navy background provides natural breathing room through color rather than empty space. Tables and lists can be tight (8px row padding) because the dark surface creates implicit separation. Hero sections use generous vertical spacing (64px+) to create contrast with the data-heavy product sections.

### Border Radius Scale
| Token | Value | Use |
|-------|-------|-----|
| none | 0px | Table cells, inline elements |
| sm | 4px | Badges, tags, small pills |
| md | 6px | Buttons, inputs, small cards |
| lg | 8px | Cards, panels, modals |
| xl | 12px | Hero cards, featured sections |
| full | 9999px | Avatar circles, pill buttons (rare) |

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat (Level 0) | No shadow | Inline elements, table cells |
| Subtle (Level 1) | `rgba(30,58,95,0.15) 0px 4px 8px` | Subtle card lift, hover |
| Standard (Level 2) | `rgba(30,58,95,0.25) 0px 12px 24px -8px, rgba(0,0,0,0.15) 0px 6px 12px -4px` | Standard cards, panels |
| Elevated (Level 3) | `rgba(30,58,95,0.25) 0px 20px 40px -20px, rgba(0,0,0,0.15) 0px 10px 20px -10px` | Featured cards, dropdowns |
| Deep (Level 4) | `rgba(15,36,64,0.35) 0px 30px 50px -20px, rgba(0,0,0,0.2) 0px 15px 30px -10px` | Modals, floating panels |
| Amber Glow | Standard + `0 0 20px rgba(245,158,11,0.15)` | CTA hover, highlighted cards |
| Ring (Focus) | `0 0 0 3px rgba(245,158,11,0.3)` | Keyboard focus ring |

**Shadow Philosophy**: All shadows use navy-tinted base colors (`rgba(30,58,95,...)`) rather than neutral gray, ensuring elevation reinforces the brand palette. The amber glow is reserved exclusively for interactive hover states on primary CTAs, creating a warm "beacon" effect that draws the eye to actionable elements against the cool navy field. Negative spread values keep shadows tight and controlled — no diffuse, blurry halos.

## 7. Do's and Don'ts

### Do
- Use Inter Variable with `"cv01", "ss03"` on every text element
- Use weight 600 for all headings — bold authority is the brand voice
- Apply navy-tinted shadows (`rgba(30,58,95,0.25)`) for all elevated elements
- Use `#1E3A5F` (Everest Navy) as the primary background — not black, not gray
- Use `#F59E0B` (amber) as the ONLY chromatic accent
- Keep border-radius between 4px-8px for most elements
- Use `"tnum"` and JetBrains Mono for ANY numerical display
- Always pair BidDeed.AI with ZoneWise.AI — never show one without the other
- Use left-border accents (3px solid) for active/selected states
- Use status colors at 15% opacity for backgrounds, full color for text

### Don't
- Don't use any chromatic color besides amber for interactive elements — no blue links, no green buttons
- Don't use light font weights (300) for headings — Everest is bold, not whisper-light
- Don't use neutral gray shadows — always tint with navy
- Don't use pill-shaped buttons (9999px radius) for standard CTAs — they're too casual
- Don't use pure black (`#000000`) for backgrounds — always use the navy scale
- Don't skip `"tnum"` on numerical data — misaligned numbers look amateur
- Don't show BidDeed without ZoneWise or vice versa — the PAIRING RULE is absolute
- Don't use warm background colors (cream, beige) — the system is dark-mode-native
- Don't use more than one accent color — amber is the single source of energy
- Don't use decorative gradients — the system is flat + shadow, not gradient-based

## 8. Responsive Behavior

### Breakpoints
| Name | Width | Key Changes |
|------|-------|-------------|
| Mobile | <640px | Single column, sidebar collapses to bottom nav, map goes full-width above panel |
| Tablet | 640-1024px | 2-column grids, sidebar overlay, split-screen becomes tabbed |
| Desktop | 1024-1400px | Full layout, sidebar visible, split-screen active |
| Large Desktop | >1400px | Centered content with generous margins, wider data tables |

### Touch Targets
- Minimum button size: `44px` height on mobile
- Table row minimum height: `48px` for tap targets
- Navigation items: `44px` minimum height with `12px` horizontal padding
- Map controls: `44px × 44px` minimum

### Collapsing Strategy
- Hero: 64px display → 36px on mobile, weight 600 maintained
- Navigation: horizontal → hamburger with slide-out drawer
- Split-screen (ZoneWise): side-by-side → stacked (map top, panel bottom)
- Data tables: horizontal scroll with sticky first column on mobile
- Card grids: 3-column → 2-column → single column
- Sidebar: persistent → overlay → bottom tab bar on mobile
- Section spacing: 64px → 32px on mobile

### Map Behavior (ZoneWise-specific)
- Map maintains minimum 300px height on mobile
- Choropleth overlays use higher opacity on mobile for legibility
- Controls reposition to bottom-left on mobile
- Parcel selection opens bottom sheet instead of side panel

## 9. Agent Prompt Guide

### Quick Color Reference
- Primary CTA: Amber (`#F59E0B`)
- CTA Hover: Amber Dark (`#D97706`)
- Background: Everest Navy (`#1E3A5F`)
- Deep Background: Navy Deep (`#0F2440`)
- Elevated Surface: Navy Elevated (`#2A4A6B`)
- Heading text: White (`#F8FAFC`)
- Body text: Silver (`#CBD5E1`)
- Muted text: Slate (`#94A3B8`)
- Border: `rgba(255,255,255,0.08)`
- Link: Amber (`#F59E0B`)
- Success: Green (`#10B981`)
- Error: Red (`#EF4444`)
- Focus ring: `rgba(245,158,11,0.3)`

### Example Component Prompts
- "Create a hero section on navy background (#1E3A5F). Headline at 64px Inter Variable weight 600, line-height 1.00, letter-spacing -1.2px, color #F8FAFC, font-feature-settings 'cv01' 1, 'ss03' 1. Subtitle at 16px weight 400, line-height 1.60, color #CBD5E1. Amber CTA button (#F59E0B, 6px radius, 10px 20px padding, #1E293B text) and ghost button (transparent, 1px solid rgba(255,255,255,0.12), #F8FAFC text, 6px radius)."
- "Design an auction card: #2A4A6B background, 1px solid rgba(255,255,255,0.08) border, 8px radius, 3px solid #F59E0B left border. Shadow: rgba(30,58,95,0.25) 0px 20px 40px -20px, rgba(0,0,0,0.15) 0px 10px 20px -10px. Title at 18px Inter weight 600, color #F8FAFC, 'cv01' 'ss03'. Bid amount at 20px JetBrains Mono weight 500, color #F59E0B, 'tnum'. Body at 14px weight 400, #CBD5E1."
- "Build a status badge: rgba(16,185,129,0.15) background, #10B981 text, 4px radius, 2px 8px padding, 11px Inter weight 500, border 1px solid rgba(16,185,129,0.4)."
- "Create navigation: #0F2440 sticky header with backdrop-filter blur(12px). Inter 14px weight 500 for links, #CBD5E1 text, 'cv01' 'ss03'. Active link: #F59E0B text with rgba(245,158,11,0.1) background pill. Amber CTA right-aligned (#F59E0B bg, #1E293B text, 6px radius)."
- "Design a data table: header row #0F2440 with Inter 12px weight 500 uppercase #94A3B8 0.3px tracking. Data rows alternate #1E3A5F and rgba(255,255,255,0.02). Hover: rgba(245,158,11,0.05). Numerical columns: JetBrains Mono 14px 'tnum' right-aligned. Row borders: 1px solid rgba(255,255,255,0.05)."
- "Build ZoneWise split-screen: left panel 60% width with Mapbox container (dark style), right panel 40% #0F2440 background. Panel has scrollable parcel list with cards: #2A4A6B bg, 8px radius, zoning badge top-right using zone color at 20% opacity."

### Iteration Guide
1. Always enable `font-feature-settings: "cv01" 1, "ss03" 1` on all Inter text
2. Weight 600 for headings, 500 for nav/labels, 400 for body — no exceptions
3. Shadow formula: `rgba(30,58,95,0.25) 0px Y1 B1 -S1, rgba(0,0,0,0.15) 0px Y2 B2 -S2`
4. Heading color is `#F8FAFC`, body is `#CBD5E1`, muted is `#94A3B8`
5. Border-radius stays 4px-8px — never pill-shaped on standard elements
6. Use `"tnum"` + JetBrains Mono for ANY number in tables, prices, IDs
7. Amber (`#F59E0B`) is the single interactive color — if it's clickable, it's amber
8. Dark backgrounds use the navy scale: `#0F2440` → `#1E3A5F` → `#2A4A6B`
9. Focus rings always use `0 0 0 3px rgba(245,158,11,0.3)`
10. BidDeed + ZoneWise always together — the pairing rule is design-system-level
