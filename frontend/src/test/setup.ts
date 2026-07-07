import "@testing-library/jest-dom/vitest";

// Node 22+ defines an experimental global `localStorage` that is undefined
// unless --localstorage-file is passed, and it shadows jsdom's implementation
// in the vitest environment (window.localStorage resolves to the same
// undefined built-in). Install a real in-memory Storage shim so bare
// `localStorage` references (app code + tests) work deterministically.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? this.store.get(key)! : null;
  }

  key(index: number): string | null {
    return [...this.store.keys()][index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

for (const name of ["localStorage", "sessionStorage"] as const) {
  const existing = globalThis[name] as Storage | undefined;
  if (!existing || typeof existing.clear !== "function") {
    Object.defineProperty(globalThis, name, {
      value: new MemoryStorage(),
      writable: true,
      configurable: true,
    });
  }
}
