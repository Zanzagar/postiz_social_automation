---
paths: ["**/*.jsx", "**/*.tsx", "**/*.vue", "**/*.svelte"]
---
<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/frontend/component-standards.md -->
# Frontend Component Standards

Auto-loaded for `.jsx`, `.tsx`, `.vue`, and `.svelte` files. Framework-agnostic principles with framework-specific guidance.

## Universal Principles

### Single Responsibility
- One component = one purpose
- If a component does two things, split it
- Target: under 200 lines per component file

### Props Down, Events Up
- Data flows downward via props
- Actions flow upward via events/callbacks
- Never mutate props directly

### Composition Over Inheritance
- Build complex UIs by composing simple components
- Use slots/children for flexible layouts
- Prefer render props or hooks over HOCs

## React

### Functional Components with Hooks
```tsx
// Props interface named ComponentNameProps
interface UserCardProps {
  user: User;
  onSelect?: (id: string) => void;
}

function UserCard({ user, onSelect }: UserCardProps) {
  const handleClick = useCallback(() => {
    onSelect?.(user.id);
  }, [user.id, onSelect]);

  return (
    <article onClick={handleClick}>
      <h3>{user.name}</h3>
    </article>
  );
}
```

### Custom Hooks
```tsx
// Prefix with "use", return explicit types
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
```

### Memoization — Use Judiciously
```tsx
// GOOD: Expensive computation
const sortedItems = useMemo(
  () => items.sort((a, b) => a.name.localeCompare(b.name)),
  [items]
);

// BAD: Premature optimization
const name = useMemo(() => user.name, [user.name]);  // No benefit
```

### Error Boundaries
```tsx
// Wrap feature sections, not individual components
<ErrorBoundary fallback={<ErrorMessage />}>
  <UserProfile />
  <UserActivity />
</ErrorBoundary>
```

## Vue (Composition API)

### Script Setup
```vue
<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  user: User
}

const props = defineProps<Props>()
const emit = defineEmits<{
  select: [id: string]
}>()

const displayName = computed(() =>
  `${props.user.firstName} ${props.user.lastName}`
)
</script>

<template>
  <article @click="emit('select', user.id)">
    <h3>{{ displayName }}</h3>
  </article>
</template>
```

### Composables
```typescript
// Prefix with "use", return reactive refs
export function useCounter(initial = 0) {
  const count = ref(initial)
  const increment = () => count.value++
  const decrement = () => count.value--
  return { count, increment, decrement }
}
```

### Avoid Excessive Watchers
```vue
<script setup>
// GOOD: Computed properties for derived state
const fullName = computed(() => `${first.value} ${last.value}`)

// BAD: Watch for derived state
watch([first, last], ([f, l]) => {
  fullName.value = `${f} ${l}`  // Use computed instead
})
</script>
```

## Svelte

### Stores for Shared State
```svelte
<!-- Using Svelte stores for cross-component state -->
<script>
  import { userStore } from '$lib/stores/user'
  import { derived } from 'svelte/store'

  const displayName = derived(userStore, $user =>
    `${$user.firstName} ${$user.lastName}`
  )
</script>

<h3>{$displayName}</h3>
```

### Actions for Reusable Behavior
```svelte
<script>
  // Actions attach behavior to DOM elements
  function clickOutside(node, callback) {
    function handleClick(event) {
      if (!node.contains(event.target)) callback()
    }
    document.addEventListener('click', handleClick)
    return {
      destroy() {
        document.removeEventListener('click', handleClick)
      }
    }
  }
</script>

<div use:clickOutside={() => open = false}>
  <!-- dropdown content -->
</div>
```

### Keep Reactivity Simple
```svelte
<script>
  // Svelte's reactivity is implicit — use it simply
  let count = 0
  $: doubled = count * 2        // Reactive derived value
  $: if (count > 10) reset()    // Reactive side effect
</script>
```

## Accessibility

### Semantic HTML First
```html
<!-- GOOD: Semantic elements -->
<nav aria-label="Main navigation">
  <button type="button" onClick={toggle}>Menu</button>
</nav>

<!-- BAD: Div soup -->
<div class="nav">
  <div class="button" onClick={toggle}>Menu</div>
</div>
```

### ARIA Only When Needed
```html
<!-- Semantic elements have implicit roles — don't duplicate -->
<button>Submit</button>                          <!-- Already role="button" -->
<button role="button">Submit</button>            <!-- Redundant -->

<!-- ARIA for custom widgets only -->
<div role="tablist" aria-label="Settings">
  <button role="tab" aria-selected={active === 0}>General</button>
  <button role="tab" aria-selected={active === 1}>Security</button>
</div>
```

### Keyboard Navigation
- All interactive elements must be keyboard-accessible
- Visible focus indicators (never `outline: none` without replacement)
- Logical tab order (avoid positive `tabindex` values)
- Trap focus in modals/dialogs

### Focus Management
```tsx
// Manage focus on route changes and dynamic content
function Modal({ isOpen, onClose, children }) {
  const closeRef = useRef(null);

  useEffect(() => {
    if (isOpen) closeRef.current?.focus();
  }, [isOpen]);

  return isOpen ? (
    <dialog open>
      <button ref={closeRef} onClick={onClose}>Close</button>
      {children}
    </dialog>
  ) : null;
}
```

## Performance

### Lazy Loading
```tsx
// React: Lazy load heavy components
const Chart = lazy(() => import('./Chart'));

// Vue: Async components
const Chart = defineAsyncComponent(() => import('./Chart.vue'));
```

### List Virtualization
- For lists > 100 items, use virtual scrolling
- Libraries: `react-virtual`, `vue-virtual-scroller`

### Image Optimization
- Always provide `width` and `height` to prevent layout shift
- Use `loading="lazy"` for below-fold images
- Prefer modern formats (WebP, AVIF) with fallbacks

## Avoid

- Deeply nested components (> 3 levels of nesting signals need for refactoring)
- Inline styles for anything reusable — use CSS/utility classes
- Direct DOM manipulation — use framework reactivity
- `dangerouslySetInnerHTML` / `v-html` without sanitization
- Index as key in dynamic lists — use stable identifiers
- God components (> 300 lines) — decompose into focused pieces
