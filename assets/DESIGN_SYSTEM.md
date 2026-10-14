# SloVerb Studio — Design System & UI Specification (`DESIGN_SYSTEM.md`)

This document is the official, definitive design specification for **SloVerb Studio**. It defines the core visual language, cyber/robotic terminal aesthetics, color palettes, typographic hierarchy, geometry rules, and reusable component blueprints for building interfaces across the application.

---

## 1. Design Philosophy & Aesthetic Core

SloVerb Studio follows a **minimalist cyber/robotic terminal aesthetic** inspired by vintage industrial audio gear, hardware DSP synthesizers, and sci-fi command terminals.

### Core Tenets
1. **Zero Curvature (Square Geometry)**: All interactive elements, cards, inputs, and containers strictly use `border_radius = 2` (or `1` for micro-bars). Rounded pill buttons or large radius bubbles (`> 2px`) are strictly prohibited.
2. **Monospaced Technical Typography**: The primary font is strictly `Consolas` across all labels, numerical values, timestamps, badges, and buttons.
3. **High-Contrast Dark Palette**: Pure cyber dark background (`#0D0E12`) paired with high-contrast neon accents (`#00FFA3` neon terminal green, `#00D2FF` digital cyan, `#FFB800` alert amber, `#FF4B4B` alert red).
4. **Iconography Over Emojis (Zero Emojis Policy)**: Emojis are strictly banned from the interface. All icons are rendered using the embedded **FontAwesome Free Solid** font (`fa-solid-900.ttf`) via unicode escape sequences.
5. **Preset Purity**: Preset buttons are strictly text-only and never include icon glyphs.
6. **State Authenticity**: Live visual feedback always reveals the underlying DSP state (e.g., distinguishing between the `CURRENT MODIFIED VERSION` and an unrendered `OLD MODIFIED VERSION`).

---

## 2. Design Tokens & Color Palette

All color constants are defined in `slowverb/config.py` and must be referenced consistently.

| Token | Hex Value | Name / Role | Usage |
| :--- | :--- | :--- | :--- |
| `COLOR_BG` | `#0D0E12` | Obsidian Canvas | Main application window background, terminal prompt boxes |
| `COLOR_SURFACE` | `#151821` | Deep Surface | Card containers, status bar container, input field background |
| `COLOR_SURFACE_LIGHT` | `#1C202C` | Elevated Surface | Button default background, modal card background |
| `COLOR_BORDER` | `#2C3242` | Charcoal Border | 1px card outlines, field outlines, dividers, slider tracks |
| `COLOR_TEXT` | `#ECEFF4` | Primary Text | Section titles, input values, primary button labels |
| `COLOR_TEXT_DIM` | `#7B849B` | Secondary Text | Card titles, labels, inactive hints, subtle secondary actions |
| `COLOR_ACCENT` | `#00FFA3` | Neon Terminal Green | Primary action borders, play buttons, active playhead, success |
| `COLOR_CYAN` | `#00D2FF` | Digital Cyan | Trim controls, preview actions, format badges, system architecture |
| `COLOR_AMBER` | `#FFB800` | Alert Amber | Pause button, warning state, unrendered slider drift |
| `COLOR_RED` | `#FF4B4B` | Danger / Stop Red | Stop button, error banners, download retry alerts |
| `COLOR_WAVE_UNPLAYED` | `#2C3446` | Unplayed Waveform | Waveform bar fill before the active playhead |
| `COLOR_WAVE_PLAYED` | `#00FFA3` | Played Waveform | Waveform bar fill traversed by the active playhead |

---

## 3. Typography Hierarchy

### Font Family
- **Monospace Font**: `Consolas` (fallback: monospace)
- **Icon Font**: `FontAwesome` (registered as `"fonts/fa-solid-900.ttf"`)

### Typographic Scales

| Level | Size | Weight | Color | Case | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **App Title** | `16px` | Bold (`ft.FontWeight.BOLD`) | `#00FFA3` | Uppercase | `SLOVERB STUDIO` |
| **Section Title** | `11px` | Bold | `#7B849B` | Uppercase | `PEEK`, `EFFECTS`, `RENDER` |
| **Field Label** | `11px` | Regular | `#ECEFF4` | Uppercase | `TRACK SPEED (SLOWED / SPED UP):` |
| **Time Display** | `13px` | Bold | `#00FFA3` | Monospace | `00:42.1 / 02:18.4` |
| **Metric / Peak** | `11px` | Regular | `#7B849B` | Uppercase | `PEAK: -3.2 dB` |
| **Button Text** | `11px` | Bold | Contextual | Uppercase | `PREVIEW EFFECTS`, `EXPORT` |
| **Badge / Codec** | `10px - 11px` | Bold | `#00D2FF` | Uppercase | `CODEC: OPUS @ 128KBPS` |
| **Status Banner** | `11px - 12px` | Bold | `#00FFA3` / `#FF4B4B` | Uppercase | `>> PLAYING PREVIEW...` |

---

## 4. Spacing, Geometry & Layout Metrics

### Geometry Rules
- **Corner Radius**: `border_radius = ft.BorderRadius.all(2)` for all containers, buttons, cards, inputs.
- **Waveform Micro-Bars**: `border_radius = ft.BorderRadius.all(1)`.
- **Border Width**: Strictly `1px` (`ft.Border.all(width=1, color=...)`).
- **Dividers**: `ft.Divider(height=1, color=COLOR_BORDER)`.

### Spacing Scale
- **Page Padding**: `16px` (`padding=16` on `ft.Page`) for main window; `24px` for modal/setup views.
- **Card Padding**: `12px` internal padding (`padding=ft.Padding.all(12)`).
- **Control Spacing**: Vertical spacing between slider groups is `2px`, between sections `8px - 10px`.
- **Button Padding**: `ft.Padding.symmetric(horizontal=12, vertical=8)` for standard buttons; `ft.Padding.symmetric(horizontal=16, vertical=10)` for hero actions.

### Waveform Layout Geometry
- **Number of Bars**: 90 vertical bars.
- **Bar Dimensions**: Width = `6px`, Spacing = `2px`.
- **Total Waveform Width**: $90 \times 6 + 89 \times 2 = 718\text{px}$.
- **Container Height**: `110px`.
- **Mouse Seek Ratio Formula**:
  $$\text{start\_x} = \frac{\text{container\_width} - 718\text{px}}{2}$$
  $$\text{ratio} = \frac{\text{local\_x} - \text{start\_x}}{718\text{px}} \quad (\text{clamped } [0.0, 1.0])$$

---

## 5. Iconography Dictionary (FontAwesome Solid)

Icons must be imported from `slowverb/config.py`. Never hardcode raw Unicode or emojis.

```python
FA_PLAY = "\uf04b"          # Play arrow
FA_PAUSE = "\uf04c"         # Pause bars
FA_STOP = "\uf04d"          # Stop square
FA_REWIND = "\uf04a"        # Rewind to start
FA_FOLDER_OPEN = "\uf07c"   # Browse directory
FA_BOLT = "\uf0e7"          # Lightning / setup / download
FA_EXPORT = "\uf019"        # Export / download tray
FA_MAGIC = "\uf0d0"         # Magic wand / quick effects
FA_CHECK = "\uf00c"         # Success checkmark
FA_WARNING = "\uf071"       # Warning alert triangle
FA_MUSIC = "\uf001"         # Music note / preview
FA_UNDO = "\uf0e2"          # Reset / undo action
FA_SLIDERS = "\uf1de"       # Equalizer / filter sliders
FA_SCISSORS = "\uf0c4"      # Trim start / end scissors
```

---

## 6. Reusable Component Blueprints

### 6.1. Minimalist Square Button (`_make_square_button`)
```python
def make_square_button(
    text: str,
    on_click,
    accent_color: str = COLOR_TEXT,
    bg_color: str = COLOR_SURFACE_LIGHT,
    width: Optional[int] = None,
    fa_icon: Optional[str] = None,
) -> ft.Container:
    controls = []
    if fa_icon:
        controls.append(
            ft.Text(
                fa_icon,
                font_family=FONT_AWESOME_FONT,
                size=11,
                color=accent_color,
            )
        )
    controls.append(
        ft.Text(
            text,
            font_family=ROBOTIC_FONT,
            size=11,
            weight=ft.FontWeight.BOLD,
            color=accent_color,
            text_align=ft.TextAlign.CENTER,
        )
    )

    content = controls[0] if len(controls) == 1 else ft.Row(
        controls,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=6,
    )

    return ft.Container(
        content=content,
        bgcolor=bg_color,
        border=ft.Border.all(width=1, color=accent_color),
        border_radius=ft.BorderRadius.all(2),
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        alignment=ft.Alignment.CENTER,
        width=width,
        on_click=on_click,
        ink=True,
    )
```

### 6.2. Cyber Panel Card (`_make_card`)
```python
def make_card(title: str, content: ft.Control, badge: Optional[str] = None) -> ft.Container:
    header_controls = [
        ft.Text(
            title,
            font_family=ROBOTIC_FONT,
            size=11,
            weight=ft.FontWeight.BOLD,
            color=COLOR_TEXT_DIM,
        )
    ]
    if badge:
        header_controls.append(
            ft.Text(
                badge,
                font_family=ROBOTIC_FONT,
                size=10,
                color=COLOR_CYAN,
            )
        )

    return ft.Container(
        content=ft.Column([
            ft.Row(header_controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=1, color=COLOR_BORDER),
            content,
        ], spacing=8),
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(width=1, color=COLOR_BORDER),
        border_radius=ft.BorderRadius.all(2),
        padding=ft.Padding.all(12),
    )
```

### 6.3. Robotic Text Field (`ft.TextField`)
```python
file_path_field = ft.TextField(
    hint_text="ENTER AUDIO FILE PATH OR BROWSE...",
    text_size=12,
    text_style=ft.TextStyle(font_family=ROBOTIC_FONT, color=COLOR_TEXT),
    bgcolor=COLOR_SURFACE,
    border_color=COLOR_BORDER,
    focused_border_color=COLOR_ACCENT,
    border_radius=ft.BorderRadius.all(2),
    expand=True,
    dense=True,
)
```

### 6.4. Hardware-Style Slider (`ft.Slider`)
```python
speed_slider = ft.Slider(
    min=MIN_SPEED,
    max=MAX_SPEED,
    value=DEFAULT_SPEED,
    divisions=20,
    label="{value}x",
    active_color=COLOR_ACCENT,
    inactive_color=COLOR_BORDER,
    thumb_color=COLOR_ACCENT,
)
```

### 6.5. Real-Time Cyber Progress Bar (`ft.ProgressBar`)
```python
progress_bar = ft.ProgressBar(
    value=0.0,
    color=COLOR_ACCENT,
    bgcolor=COLOR_SURFACE,
    height=8,
    border_radius=ft.BorderRadius.all(2),
)
```

### 6.6. Technical Diagnostic Info Box
```python
info_box = ft.Container(
    content=ft.Column([
        ft.Text("STATUS: ACTIVE // REAL-TIME DSP READY", font_family=ROBOTIC_FONT, size=11, weight=ft.FontWeight.BOLD, color=COLOR_ACCENT),
        ft.Text("SAMPLE RATE: 44100 HZ // STEREO 2-CH", font_family=ROBOTIC_FONT, size=10, color=COLOR_TEXT_DIM),
    ], spacing=4),
    bgcolor=COLOR_BG,
    border=ft.Border.all(width=1, color=COLOR_BORDER),
    border_radius=ft.BorderRadius.all(2),
    padding=ft.Padding.all(12),
)
```

---

## 7. Status & State Indicators

### Version Status Indicator
Used to indicate whether the currently playing or previewed buffer matches the active slider parameters:

1. **Current Buffer (`CURRENT MODIFIED VERSION`)**:
   - Icon: `FA_CHECK` (`\uf00c`)
   - Accent: `COLOR_ACCENT` (`#00FFA3`)
   - Border: `1px solid #00FFA3`
2. **Stale / Drifted Buffer (`OLD MODIFIED VERSION`)**:
   - Icon: `FA_WARNING` (`\uf071`)
   - Accent: `COLOR_AMBER` (`#FFB800`)
   - Border: `1px solid #FFB800`

---

## 8. Development Checklist for New Interfaces

When adding any new dialog, window, view, or control to SloVerb Studio:
- [ ] Is the typography strictly `Consolas`?
- [ ] Are all container borders strictly `border_radius = 2`?
- [ ] Are borders single-pixel (`width=1`) using `#2C3242` or an accent color?
- [ ] Are emojis completely omitted in favor of FontAwesome icons?
- [ ] Are preset buttons text-only without icons?
- [ ] Is the background strictly `#0D0E12` or surface `#151821`?
- [ ] Are UI updates thread-safe via `_ui_lock` and `page.update()`?
