---
name: typescript-patterns
description: TypeScript strict mode, generics, utility types, discriminated unions, modules
---
# TypeScript Patterns Skill

## Strict Mode Configuration

```jsonc
// tsconfig.json — recommended strict settings
{
  "compilerOptions": {
    "strict": true,                    // Enables all strict checks
    "strictNullChecks": true,          // null/undefined are distinct types
    "noImplicitAny": true,             // No implicit 'any' types
    "strictFunctionTypes": true,       // Strict function parameter checking
    "noUncheckedIndexedAccess": true,  // Array/object access may be undefined
    "exactOptionalPropertyTypes": true // undefined !== missing property
  }
}
```

## Generics Patterns

### Constrained Generics
```typescript
// Ensure T has an 'id' property
function findById<T extends { id: string }>(items: T[], id: string): T | undefined {
  return items.find(item => item.id === id);
}

// Multiple constraints
function merge<T extends object, U extends object>(a: T, b: U): T & U {
  return { ...a, ...b };
}
```

### Generic Inference
```typescript
// TypeScript infers the return type from usage
function createPair<T>(value: T): [T, T] {
  return [value, value];
}
const pair = createPair("hello"); // inferred as [string, string]
```

### Conditional Types
```typescript
type IsString<T> = T extends string ? true : false;
type Result = IsString<"hello">; // true
type Result2 = IsString<42>;     // false

// Extract return type of async functions
type UnwrapPromise<T> = T extends Promise<infer U> ? U : T;
```

## Utility Types

```typescript
// Built-in utility types
Partial<User>          // All properties optional
Required<Config>       // All properties required
Pick<User, "id" | "name">  // Only selected properties
Omit<User, "password">     // All except selected
Record<string, number>     // { [key: string]: number }
Readonly<Config>            // All properties readonly

// Custom utility types
type Nullable<T> = T | null;
type DeepPartial<T> = { [P in keyof T]?: DeepPartial<T[P]> };
type ValueOf<T> = T[keyof T];
```

## Discriminated Unions

```typescript
// The 'type' field discriminates between variants
type Result<T> =
  | { type: "success"; data: T }
  | { type: "error"; error: string }
  | { type: "loading" };

function handleResult(result: Result<User>) {
  switch (result.type) {
    case "success":
      console.log(result.data);  // TypeScript knows 'data' exists
      break;
    case "error":
      console.error(result.error); // TypeScript knows 'error' exists
      break;
    case "loading":
      console.log("Loading...");
      break;
    default:
      // Exhaustive check — compile error if a case is missed
      const _exhaustive: never = result;
  }
}
```

## Module Patterns

### Barrel Exports
```typescript
// src/models/index.ts — re-export from single entry point
export { User } from "./user";
export { Order } from "./order";
export { Product } from "./product";

// Usage: import { User, Order } from "./models";
```

### Path Aliases
```jsonc
// tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"],
      "@models/*": ["./src/models/*"],
      "@utils/*": ["./src/utils/*"]
    }
  }
}
// Usage: import { User } from "@models/user";
```

### Type-Only Imports
```typescript
// Import types without runtime cost
import type { User } from "./models";
import { type Config, loadConfig } from "./config";
```

## Common Anti-Patterns

- **`any` escape hatch**: Use `unknown` instead, then narrow with type guards
- **Type assertions (`as`)**: Prefer type guards (`if ('key' in obj)`)
- **Enums**: Prefer `as const` objects or string literal unions
- **Overuse of `!` (non-null assertion)**: Handle null/undefined properly
