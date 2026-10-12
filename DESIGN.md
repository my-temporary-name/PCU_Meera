---
name: Doctor's view
description: A quiet, berry-accented clinical workspace where colour appears only for status or attention, and glass is reserved for the floating controls.
colors:
  berry: "#A2305F"
  berry-soft: "#F6DCE5"
  blush-header: "#F8E4E6"
  ink: "#261A22"
  ink-secondary: "#4D3A46"
  ink-muted: "#7B6571"
  hairline: "#EEDADD"
  hairline-strong: "#E2C6CC"
  page: "#FFFFFF"
  surface: "#FFFFFF"
  surface-tint: "#FBF4F3"
  status-green: "#38A06C"
  status-amber: "#E0A02A"
  status-red: "#D93B2B"
  status-grey: "#A89AA2"
  quiet-ink: "#1F1F1F"
  quiet-ink-secondary: "#4A4A4A"
  quiet-muted: "#666666"
  quiet-line: "#E6E6E6"
  quiet-tint: "#F1F1F1"
  dark-page: "#140F13"
  dark-surface: "#1E161C"
  dark-ink: "#F6EEF1"
  dark-ink-muted: "#B3A0AA"
  dark-hairline: "#34262E"
  dark-berry: "#E0709F"
  dark-berry-soft: "#3A2030"
  dark-status-green: "#56C492"
  dark-status-amber: "#EDB655"
  dark-status-red: "#F0604C"
typography:
  display:
    fontFamily: "Newsreader, 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif"
    fontSize: "30px"
    fontWeight: 560
    lineHeight: 1.1
    letterSpacing: "-0.018em"
  headline:
    fontFamily: "Newsreader, 'Iowan Old Style', Palatino, Georgia, serif"
    fontSize: "25px"
    fontWeight: 560
    lineHeight: 1.2
    letterSpacing: "-0.016em"
  title:
    fontFamily: "Newsreader, 'Iowan Old Style', Palatino, Georgia, serif"
    fontSize: "17px"
    fontWeight: 520
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  body:
    fontFamily: "'DM Sans', ui-sans-serif, -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "'tnum' 1"
  value:
    fontFamily: "'DM Sans', ui-sans-serif, sans-serif"
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.022em"
    fontFeature: "'tnum' 1"
  label:
    fontFamily: "'DM Sans', ui-sans-serif, sans-serif"
    fontSize: "11px"
    fontWeight: 650
    letterSpacing: "0.09em"
rounded:
  chip: "8px"
  inner: "12px"
  card: "20px"
  panel: "16px"
  bar: "24px"
  popup: "28px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "18px"
  lg: "26px"
  xl: "40px"
components:
  domain-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "26px 28px"
  tab-active:
    backgroundColor: "{colors.berry}"
    textColor: "{colors.surface}"
    rounded: "999px"
  chip-condition:
    backgroundColor: "{colors.berry-soft}"
    textColor: "{colors.berry}"
    rounded: "{rounded.chip}"
    padding: "3px 10px"
  status-pill-red:
    backgroundColor: "{colors.status-red}"
    textColor: "{colors.surface}"
    rounded: "{rounded.chip}"
---

# Design System: Doctor's view

## Overview

**Creative North Star: "The Quiet Consulting Room"**

A doctor glances at this between patients. The room is calm: white surfaces, ink text, one berry accent, and almost everything grey until you point at it. Colour is rationed. It appears for clinical status (green, amber, red, grey), for the one thing you have chosen, and for the live conversation. Everything else waits.

The surface is split in two layers. Content (cards, panels, charts) is solid and legible. Glass is the material of the floating control layer only: the top bar and the popups, over a scrim, so the page visibly sits underneath them. Type pairs a refined serif for names and titles with a clean sans for every number and label, so a figure always reads as a figure.

Motion is deliberate and rare: cards lift and tilt a few degrees toward the pointer, details open as a slow amoeba-like split, popups settle from the card that opened them. Nothing loops except the notes orb, which is the one living thing on the page.

**Key Characteristics:**
- Quiet by default: neutral greys at rest, the real palette on hover, focus or selection.
- Status colours are always on and mean only status.
- One berry accent, used for interaction, never for decoration or status.
- Content solid, controls glass. No glass on content cards.
- Serif for names and titles, sans with tabular numerals for all clinical values.
- Every animation has a reduced-motion alternative; print is solid white.

## Colors

A white page, tinted neutrals toward berry, and a single accent.

### Primary
- **Berry** (#A2305F): the active tab pill, "Open" links and chevrons, focus rings, selected value tiles, the main chart series, condition chips (text) and medicine bars. In dark mode, **Rose Berry** (#E0709F).
- **Soft Berry Tint** (#F6DCE5 / dark #3A2030): chip and selected-tile backgrounds, avatar plate.

### Secondary (status, always colour)
- **Green** (#38A06C / dark #56C492): lower concern, in range.
- **Amber** (#E0A02A / dark #EDB655): increased attention.
- **Red** (#D93B2B / dark #F0604C): high attention. Pushed toward orange-red so it never reads as berry.
- **Grey** (#A89AA2): no priority defined.

### Neutral
- **Ink** (#261A22 / dark #F6EEF1): primary text and clinical values.
- **Ink Secondary** (#4D3A46) and **Ink Muted** (#7B6571 / dark #B3A0AA): supporting text, labels. Muted text on glass uses a deeper value (#624D5A) to keep 4.5:1.
- **Hairline** (#EEDADD / dark #34262E): every border, 1 px.
- **Quiet greys** (#1F1F1F, #4A4A4A, #666666, #E6E6E6, #F1F1F1; dark #EDEDED, #2A2A2A): the resting state of quiet components.
- **Blush Header** (#F8E4E6): episode and patient header tints only.

### Named Rules
**The Colour-Is-Earned Rule.** A surface is grey until it is hovered, focused or selected. Status dots and pills are the only things that stay coloured at rest.

**The Berry Is Not A Status Rule.** Berry never marks green, amber, red or grey, and status colours never decorate. If red and berry look alike side by side, red moves toward orange.

## Typography

**Display and title font:** Newsreader (variable, bundled locally, SIL OFL), falling back to Iowan Old Style, Palatino, Georgia.
**Body and numbers font:** DM Sans (variable, bundled locally, SIL OFL), falling back to the system sans.

**Character:** a quiet editorial serif for who and what, a precise sans for how much. Numerals are tabular everywhere.

### Hierarchy
- **Display** (560, 30px, 1.1, -0.018em): the patient name, the doctor's name.
- **Headline** (560, 25px, 1.2): "Domains", "Predictions", popup titles (26px).
- **Title** (520, 17px): the four visit-brief boxes, episode headings.
- **Body** (400, 14px, 1.5): reading text; keep lines near 65 to 75 characters.
- **Value** (700, 24px, -0.022em, tabular): clinical figures on tiles and cards.
- **Label** (650, 11px, +0.09em, uppercase): CONDITIONS, MEDICINES, VISIT BRIEF.

### Named Rules
**The Figure Stays Sans Rule.** Numbers are never set in the serif, and always use tabular numerals, right-aligned in value rows.

## Layout

A two-column workspace: a pinned 220 px left rail (page tabs and the four visit-brief boxes) and a content column up to 1280 px, inside a 1560 px centred shell. The floating top bar spans the same left and right edges. A 76 px gutter on the right holds the notes orb, so nothing overlaps.

The overview reads top to bottom: patient panels, then Domains (four across, then two, then one), Predictions, and Interventions and recommendations as the same card grid. Detail is on demand: popups and the amoeba details, not long pages. Spacing runs on a multiple-of-four rhythm with generous card padding (about 26 px). Below 900 px the rail becomes a row, the boxes a two-column grid, and the orb moves to the bottom right.

The schedule screen before it is a single column: hospital bar, doctor banner, then a 20-minute timeline that scrolls inside its own frame with faded top and bottom edges.

## Elevation & Depth

A hybrid. Content depth is tonal and shadow-light: hairline borders plus one soft, berry-tinted shadow. Glass appears only on the floating layer.

### Shadow Vocabulary
- **Rest** (`0 1px 2px rgba(38,26,34,.05), 0 6px 20px rgba(162,48,95,.07)`): cards at rest.
- **Lift** (`0 2px 6px rgba(38,26,34,.07), 0 12px 32px rgba(162,48,95,.12)`): hover.
- **Raised** (`0 4px 10px rgba(38,26,34,.08), 0 22px 48px rgba(162,48,95,.16)`): a domain card under the pointer.
- **Popup** (`0 12px 40px rgba(162,48,95,.14), 0 36px 90px rgba(38,26,34,.22)`): the dialog.

### Glass tiers
- **Regular** (bar, tab switchers): 56 % fill of the brand surface, blur 24 px, saturate 140 %.
- **Thick** (popups): 78 % fill, blur 28 px, over a 30 % scrim blurred 6 px.
- **Static** (patient card, inner blocks): 80 % and 66 % fill with a lit rim and no blur.

### Named Rules
**The Glass Is For Controls Rule.** Backdrop blur is allowed on the bar and the popups, and nowhere else. At most three blurred layers are visible at once.

## Shapes

Soft but not round: 8 px chips, 12 px inner blocks and tiles, 16 px boxes, 20 px cards, 24 px for the bar, 28 px for popups, and full pills only for tabs and buttons. Borders are always 1 px hairlines. A rim is drawn as a faint gradient edge, brighter at the top left. No thick coloured side borders, ever.

## Components

### Buttons and controls
- **Shape:** pills (tabs, Light/Dark) and 12 px (small icon buttons).
- **Active tab:** berry at about 84 % with a rim, white text; it slides and stretches between tabs (about 380 ms).
- **Press:** scale 0.97 with a soft glow from the contact point. **Focus:** a 2 px berry ring, 2 px offset.

### Cards (Domains, Predictions, Recommendations)
- **Corner:** 20 px, hairline, white (dark #1E161C). Grey and neutral at rest, full colour on hover.
- **Hover:** lifts 4 px, tilts up to 4 degrees toward the pointer, a faint highlight follows the cursor. "Open ›" appears at the top right only on hover.
- **Status:** a dot beside the title; never a coloured edge.

### Visit-brief boxes (amoeba)
Four title-and-date boxes in the left rail. On hover (or tap, or Enter) a droplet buds out of the right edge, pinches off, grows, and joins back as one inverted-L shape, opening the rest of the rows. The goo filter exists only while moving.

### Popups
Thick glass at 28 px radius over a dimmed, blurred page; they open from the card that was clicked. Two tabs: Status and trends (values left, chart right) and Events and episodes.

### Chips
8 px, soft berry tint with berry text (conditions, allergy) or neutral tint; status pills are 8 px with ink or white text at 4.5:1 or better.

### Charts
Her readings in berry, other series in warm neutrals (bronze, mauve, sand), thresholds as dashed lines, Green, Amber and Red bands as 13 to 17 % tints. Projections are dashed or dotted curves with a shaded 80 % range.

### Visit notes orb
A canvas of translucent ribbons on a frosted disc at the end of the right gutter. It turns pink for the doctor and violet for the patient; the panel is a notepad of chat bubbles typed word by word.

### Appointment card (schedule)
Grey and quiet for everyone but the patient being opened, who gets a berry outline, an "Up next" chip and an Open link. Past visits are marked Completed or Did not attend; free slots are just a time on a dashed line.

## Do's and Don'ts

### Do:
- **Do** keep a surface grey until it is pointed at, focused or selected; keep status dots and pills in colour.
- **Do** use berry only for interaction (active tab, links, focus, the selected tile, the main series).
- **Do** use the serif only for names and titles, and tabular sans for every number.
- **Do** keep glass to the top bar, tab switchers and popups, and give every glass surface a solid fallback (reduced transparency, high contrast, no backdrop-filter, print).
- **Do** keep contrast at 4.5:1 or better on the worst-case backdrop; clinical values at 7:1.
- **Do** let every motion respect `prefers-reduced-motion` with a short fade instead.

### Don't:
- **Don't** use berry or its tint to show a status, or a status colour to decorate.
- **Don't** put glass or blur on content cards or text bodies.
- **Don't** draw thick coloured left or top borders on cards; use a dot or a chip.
- **Don't** add gradient text, neon glows, emoji or decorative icons.
- **Don't** add provenance lines such as "synthetic", "best guess", "persona" or "built from CSV" to the clinician's screen.
- **Don't** animate numbers (no count-up) or leave any element invisible if an animation is skipped.
