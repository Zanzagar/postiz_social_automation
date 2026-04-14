---
paths: ["**/*.jsx", "**/*.tsx", "**/*.vue", "**/*.svelte", "**/*.css"]
---
# Frontend Development Workflow

Auto-loaded when editing frontend files. Guides tool selection and workflow for UI development.

## Available Tools

### Magic MCP (21st.dev)
When the `21st-magic` MCP server is connected, these tools produce production-quality React + Tailwind components:

| Tool | Purpose |
|------|---------|
| `21st_magic_component_builder` | Generate production React + Tailwind components |
| `21st_magic_component_inspiration` | Browse UI patterns and design ideas |
| `21st_magic_component_refiner` | Iterate and polish existing components |
| `logo_search` | Find brand icons and logos |

### frontend-design Skill
Invoke `frontend-design` skill before building UI to establish design direction. Prevents generic AI aesthetics by guiding creative choices (color, typography, layout personality).

### Recommended Base Libraries
| Context | Stack |
|---------|-------|
| Internal tools, dashboards | React 18 + Vite + Tailwind CSS + shadcn/ui |
| Public-facing apps | Next.js + Tailwind CSS + shadcn/ui |
| Simple prototypes | Plain HTML + Tailwind CDN |

shadcn/ui provides Radix primitives + Tailwind styling. Magic MCP builds on top of this foundation.

## Workflow

1. **Design direction** — invoke `frontend-design` skill for brand/aesthetic guidance
2. **Component inspiration** — use `21st_magic_component_inspiration` to browse patterns
3. **Build** — use `21st_magic_component_builder` for each page/component
4. **Refine** — use `21st_magic_component_refiner` to iterate
5. **Test** — Vitest + React Testing Library for component tests

## TDD for Components

Frontend components use testing-library patterns, not Superpowers' strict RED-GREEN-REFACTOR:

| What to test | How |
|-------------|-----|
| Rendering | Component renders without errors |
| User interaction | Click handlers, form submissions fire correctly |
| State changes | UI updates reflect state changes |
| Accessibility | ARIA attributes, keyboard navigation |

**Do not test:** styling, pixel-perfect layout, CSS class names.

## When This Rule Applies

This rule loads only when editing frontend files (`.jsx`, `.tsx`, `.vue`, `.svelte`, `.css`). Zero token cost for backend-only sessions.
