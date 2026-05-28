# Maritime Logbook Design System

This directory contains the official design system specification for the **Maritime Logbook** project. It is stored as a reference for all UI/UX decisions, typography styling, color tokens, and layout guidelines.

## Design Principles

*   **High contrast for outdoor daylight visibility:** Crucial for readability under direct sunlight when out on the water.
*   **Large touch targets for mobile usability:** Designed for wet/moving environments where precision touch might be difficult.
*   **Clear distinction between read-only data & interactive elements:** Prevents accidental triggers or navigation.

---

## Brand Colors

| Palette / Usage | Variable | Hex Code | Tailwind Class | Recommended Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Brand Primary** | `primary` | `#1E3A8A` | `blue-900` | Top navigation, active states, primary branding |
| **Brand Secondary** | `secondary` | `#0369A1` | `sky-700` | Secondary buttons, subtle highlights |
| **Brand Accent** | `accent` | `#EA580C` | `orange-600` | Primary CTAs, "Start Trip" buttons, active recording indicators |
| **Background Base** | `base` | `#F8FAFC` | `slate-50` | Main application background |
| **Background Surface**| `surface` | `#FFFFFF` | `white` | Cards, dropdowns, forms |
| **Background Highlight**| `surfaceHighlight`| `#F1F5F9` | `slate-100` | Hover states on list items and table rows |
| **Text Primary** | `primary` | `#0F172A` | `slate-900` | Headings, primary body copy |
| **Text Secondary** | `secondary` | `#475569` | `slate-600` | Timestamps, secondary descriptions, metadata |
| **Text Inverse** | `inverse` | `#FFFFFF` | `white` | Text on primary and accent background colors |
| **Status Success** | `success` | `#15803D` | `green-700` | Trip completed, GPX upload success |
| **Status Warning** | `warning` | `#B45309` | `amber-700` | Offline queue notifications |
| **Status Danger** | `danger` | `#B91C1C` | `red-700` | Delete boat, end trip prematurely |

---

## Typography

### Font Families
*   **Sans Font (All general UI, headings, buttons):** `Inter, system-ui, -apple-system, sans-serif`
*   **Mono Font (Coordinates, GPX data, timestamps, hashtags):** `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`

### Hierarchy & Scale

| Style | Font Size | Weight | Line Height |
| :--- | :--- | :--- | :--- |
| **Heading 1 (`h1`)** | `2.25rem` (36px) | `700` (Bold) | `2.5rem` |
| **Heading 2 (`h2`)** | `1.5rem` (24px) | `600` (Semi-bold) | `2rem` |
| **Heading 3 (`h3`)** | `1.25rem` (20px) | `600` (Semi-bold) | `1.75rem` |
| **Body (`body`)** | `1rem` (16px) | `400` (Regular) | `1.5rem` |

---

## Raw Configuration JSON

To access this configuration programmatically, you can read the JSON file directly at [design_system.json](file:///Users/aquiles/Documents/Web/Sailboat_Log/.agents/design_system.json) or refer to the copy below:

```json
{
  "designSystem": {
    "name": "Maritime Logbook",
    "version": "1.0.0",
    "designPrinciples": [
      "High contrast for outdoor daylight visibility",
      "Large touch targets for mobile usability on the water",
      "Clear distinction between read-only data and interactive elements"
    ],
    "tokens": {
      "colors": {
        "brand": {
          "primary": {
            "value": "#1E3A8A",
            "tailwind": "blue-900",
            "usage": "Top navigation, active states, primary branding"
          },
          "secondary": {
            "value": "#0369A1",
            "tailwind": "sky-700",
            "usage": "Secondary buttons, subtle highlights"
          },
          "accent": {
            "value": "#EA580C",
            "tailwind": "orange-600",
            "usage": "Primary CTAs, 'Start Trip' buttons, active recording indicators"
          }
        },
        "background": {
          "base": {
            "value": "#F8FAFC",
            "tailwind": "slate-50",
            "usage": "Main application background"
          },
          "surface": {
            "value": "#FFFFFF",
            "tailwind": "white",
            "usage": "Cards, dropdowns, forms"
          },
          "surfaceHighlight": {
            "value": "#F1F5F9",
            "tailwind": "slate-100",
            "usage": "Hover states on list items and table rows"
          }
        },
        "text": {
          "primary": {
            "value": "#0F172A",
            "tailwind": "slate-900",
            "usage": "Headings, primary body copy"
          },
          "secondary": {
            "value": "#475569",
            "tailwind": "slate-600",
            "usage": "Timestamps, secondary descriptions, metadata"
          },
          "inverse": {
            "value": "#FFFFFF",
            "tailwind": "white",
            "usage": "Text on primary and accent background colors"
          }
        },
        "status": {
          "success": {
            "value": "#15803D",
            "tailwind": "green-700",
            "usage": "Trip completed, GPX upload success"
          },
          "warning": {
            "value": "#B45309",
            "tailwind": "amber-700",
            "usage": "Offline queue notifications"
          },
          "danger": {
            "value": "#B91C1C",
            "tailwind": "red-700",
            "usage": "Delete boat, end trip prematurely"
          }
        }
      },
      "typography": {
        "fonts": {
          "sans": {
            "family": "Inter, system-ui, -apple-system, sans-serif",
            "usage": "All general UI text, headings, and buttons"
          },
          "mono": {
            "family": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            "usage": "Coordinates, GPX data, log timestamps, hashtags"
          }
        },
        "sizes": {
          "h1": { "size": "2.25rem", "weight": "700", "lineHeight": "2.5rem" },
          "h2": { "size": "1.5rem", "weight": "600", "lineHeight": "2rem" },
          "h3": { "size": "1.25rem", "weight": "600", "lineHeight": "1.75rem" },
          "body": { "size": "1rem", "weight": "400", "lineHeight": "1.5rem" }
        }
      }
    }
  }
}
```
