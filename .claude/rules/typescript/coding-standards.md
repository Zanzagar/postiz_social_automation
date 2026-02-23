---
paths: ["**/*.ts", "**/*.tsx"]
---
<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/typescript/coding-standards.md -->
# TypeScript Coding Standards

Auto-loaded for `.ts` and `.tsx` files. These conventions ensure type safety and consistency.

## Strict Mode

- Always enable `strict: true` in `tsconfig.json`
- Never use `any` without a `// eslint-disable-next-line` comment explaining why
- Prefer `unknown` over `any` for truly unknown types — force narrowing at usage site

## Type Patterns

### Interfaces vs Types

```typescript
// Interfaces: object shapes, extendable contracts
interface UserProps {
  id: string;
  name: string;
  email: string;
}

// Types: unions, intersections, mapped types
type Status = "active" | "inactive" | "pending";
type WithTimestamp<T> = T & { createdAt: Date; updatedAt: Date };
```

**Rule**: Use `interface` for object shapes (they merge and extend cleanly). Use `type` for unions, intersections, and computed types.

### Branded Types for IDs

```typescript
type UserId = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };

// Prevents accidentally passing an OrderId where UserId is expected
function getUser(id: UserId): User { ... }
```

### Discriminated Unions

```typescript
type Result<T> =
  | { success: true; data: T }
  | { success: false; error: Error };

// TypeScript narrows automatically on the discriminant
function handle(result: Result<User>) {
  if (result.success) {
    console.log(result.data.name); // TypeScript knows data exists
  }
}
```

## Null Handling

- Prefer optional chaining: `user?.address?.city` over explicit null checks
- Prefer nullish coalescing: `value ?? defaultValue` over `value || defaultValue`
  - `||` treats `0`, `""`, `false` as falsy — `??` only catches `null`/`undefined`
- Use `NonNullable<T>` to strip null/undefined from types after validation

## Import Organization

Order imports consistently:

```typescript
// 1. External packages
import { useState, useEffect } from "react";
import { z } from "zod";

// 2. Internal modules (absolute paths)
import { UserService } from "@/services/user";
import { config } from "@/config";

// 3. Relative imports
import { formatDate } from "./utils";
import { UserCard } from "./components/UserCard";

// 4. Type-only imports (always last)
import type { User, UserRole } from "@/types";
import type { ComponentProps } from "./types";
```

**Rule**: Always use `import type` for type-only imports — this ensures they're erased at compile time and don't create runtime dependencies.

## Function Patterns

```typescript
// Prefer explicit return types on exported functions
export function calculateTotal(items: CartItem[]): number {
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

// Use const assertions for literal types
const ROUTES = {
  home: "/",
  login: "/login",
  dashboard: "/dashboard",
} as const;

// Prefer function overloads over union return types
function parse(input: string): number;
function parse(input: string[]): number[];
function parse(input: string | string[]): number | number[] {
  // implementation
}
```

## React-Specific (TSX)

### Component Typing

```typescript
// Props interface named ComponentNameProps
interface UserCardProps {
  user: User;
  onEdit?: (id: UserId) => void;
  variant?: "compact" | "full";
}

// Functional component — avoid React.FC (it adds implicit children)
function UserCard({ user, onEdit, variant = "full" }: UserCardProps) {
  return <div>...</div>;
}
```

### Custom Hooks

```typescript
// Return explicit types from hooks
function useAuth(): {
  user: User | null;
  login: (credentials: Credentials) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
} {
  // implementation
}
```

### Event Handlers

```typescript
// Use React's built-in event types
function SearchInput({ onSearch }: { onSearch: (query: string) => void }) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onSearch(e.target.value);
  };
  return <input onChange={handleChange} />;
}
```

## Error Handling

```typescript
// Define error types, don't throw raw strings
class AppError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number = 500
  ) {
    super(message);
    this.name = "AppError";
  }
}

// Use Result types for expected failures
type Result<T, E = AppError> =
  | { ok: true; value: T }
  | { ok: false; error: E };
```

## Security Essentials

### Secrets — Never Hardcode
```typescript
// DO: Validate env vars at startup, fail fast
function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) throw new Error(`Missing required env var: ${key}`);
  return value;
}

const DB_URL = requireEnv("DATABASE_URL");
const API_KEY = requireEnv("API_KEY");

// DON'T: Hardcoded secrets or silent fallbacks
const API_KEY = "sk-abc123"; // NEVER
const API_KEY = process.env.API_KEY ?? "default"; // Silent failure
```

### Input Validation with Zod
```typescript
import { z } from "zod";

// Validate at system boundaries (API input, form data, env vars)
const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
  age: z.number().int().positive().optional(),
});

type CreateUserInput = z.infer<typeof CreateUserSchema>; // DRY: derive type

function createUser(raw: unknown): User {
  const input = CreateUserSchema.parse(raw); // throws ZodError on invalid
  return db.users.create(input);
}
```

### XSS Prevention
- Never use `dangerouslySetInnerHTML` without sanitization (use `DOMPurify`)
- Prefer React's built-in JSX escaping — it handles most cases automatically
- Sanitize URL inputs: `new URL(input)` to validate before using in `href`

## Immutability

```typescript
// Prefer spread over mutation
const updated = { ...user, name: "New Name" }; // NOT: user.name = "New Name"
const filtered = items.filter(x => x.active);   // NOT: items.splice(...)

// Use Readonly<T> for function params you shouldn't mutate
function processItems(items: Readonly<Item[]>): Summary {
  // items.push() would be a type error
  return items.reduce(/* ... */);
}
```

## Avoid

- `enum` — use `as const` objects or union types instead (better tree-shaking)
- `namespace` — use ES modules
- Non-null assertion `!` — prefer optional chaining or explicit narrowing
- `Function` type — use specific signatures `(args: T) => R`
- Barrel files (`index.ts` re-exports) in large projects — they break tree-shaking
- `console.log` in production code — use a structured logger

See `typescript-patterns` skill for comprehensive patterns reference.
