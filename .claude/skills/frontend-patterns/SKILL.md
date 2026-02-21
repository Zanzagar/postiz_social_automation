---
name: frontend-patterns
description: React/Vue/Svelte patterns, state management, accessibility, performance
---
# Frontend Patterns Skill

## React Patterns

### Custom Hooks
```tsx
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
```

### Composition over Props Drilling
```tsx
// BAD: Prop drilling through 4 levels
<App user={user}> → <Layout user={user}> → <Header user={user}> → <Avatar user={user}>

// GOOD: Composition with children
<App>
  <Layout header={<Header avatar={<Avatar user={user} />} />}>
    {children}
  </Layout>
</App>
```

### Error Boundaries
```tsx
class ErrorBoundary extends Component<Props, State> {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) return <ErrorFallback error={this.state.error} />;
    return this.props.children;
  }
}
```

## Vue Patterns (Composition API)

### Composables
```typescript
// useCounter.ts
export function useCounter(initial = 0) {
  const count = ref(initial);
  const increment = () => count.value++;
  const decrement = () => count.value--;
  return { count, increment, decrement };
}
```

### Provide/Inject (Dependency Injection)
```typescript
// Parent
provide('theme', ref('dark'));

// Deep child (no prop drilling)
const theme = inject('theme');
```

## Svelte Patterns

### Stores
```typescript
// stores.ts
import { writable, derived } from 'svelte/store';

export const items = writable<Item[]>([]);
export const total = derived(items, $items =>
  $items.reduce((sum, item) => sum + item.price, 0)
);
```

## State Management

### When to Lift State
- **Local**: UI-only state (open/closed, input value) → `useState` / `ref()`
- **Shared**: Sibling components need it → Lift to common parent
- **Global**: App-wide state (auth, theme, cart) → Context / Store / Zustand

### Avoid
- Global state for everything (makes testing hard)
- Derived state in state (compute it instead)
- Deeply nested state objects (normalize or use Immer)

## Accessibility

### ARIA Roles
```html
<nav aria-label="Main navigation">
<button aria-expanded="false" aria-controls="menu">Menu</button>
<div role="alert">Error: Invalid email</div>
<div role="dialog" aria-labelledby="dialog-title" aria-modal="true">
```

### Keyboard Navigation
- All interactive elements must be focusable
- Tab order should be logical (avoid positive `tabindex`)
- Escape closes modals/dropdowns
- Arrow keys navigate within components (tabs, menus, lists)

### Focus Management
```tsx
// Return focus after modal closes
const triggerRef = useRef<HTMLButtonElement>(null);
const onClose = () => {
  setOpen(false);
  triggerRef.current?.focus();
};
```

## Performance

### Lazy Loading
```tsx
// React
const HeavyComponent = lazy(() => import('./HeavyComponent'));
<Suspense fallback={<Spinner />}><HeavyComponent /></Suspense>
```

### Virtualization
- For lists >100 items: use `react-window` or `@tanstack/virtual`
- Render only visible items, recycle DOM nodes

### Memoization
```tsx
// Expensive computation
const sorted = useMemo(() => items.sort(compareFn), [items]);

// Stable callback reference
const onClick = useCallback(() => doThing(id), [id]);

// Component memoization (only for expensive renders)
const MemoList = memo(ExpensiveList);
```

**Rule**: Don't memoize everything — profile first, optimize measured bottlenecks.
