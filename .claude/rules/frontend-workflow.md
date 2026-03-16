# Frontend Component Workflow (MANDATORY)

When creating or significantly modifying React components (pages, UI components, layouts):

## Required Pipeline

1. **`frontend-design` skill** — Get creative direction BEFORE writing any JSX
2. **Magic MCP `component_inspiration`** — Search for design inspiration matching the direction
3. **Magic MCP `component_builder`** — Generate the initial component from inspiration
4. **Magic MCP `component_refiner`** — Iterate on the generated component
5. **Manual refinement** — Integrate with app state, API calls, routing

## When This Applies

- New pages
- New reusable components
- Visual redesigns of existing components
- Adding significant UI sections to existing pages

## When This Does NOT Apply

- Bug fixes (e.g., fixing a click handler)
- Adding a prop or state variable
- Wiring up an API call
- Tests
- Non-visual logic changes

## Why

Components built with Magic MCP + frontend-design have higher design quality than hand-written JSX. The v1 frontend was built without these tools — upgrades MUST use them.
