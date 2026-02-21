---
name: cpp-coding-standards
description: C++ coding standards based on the C++ Core Guidelines (isocpp.github.io). Use when writing, reviewing, or refactoring C++ code to enforce modern, safe, and idiomatic practices.
---

# C++ Coding Standards (C++ Core Guidelines)

Comprehensive coding standards for modern C++ (C++17/20/23) derived from the [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines). Enforces type safety, resource safety, immutability, and clarity.

## When to Use

- Writing new C++ code (classes, functions, templates)
- Reviewing or refactoring existing C++ code
- Making architectural decisions in C++ projects
- Enforcing consistent style across a C++ codebase
- Choosing between language features (e.g., `enum` vs `enum class`, raw pointer vs smart pointer)

### When NOT to Use

- Non-C++ projects
- Legacy C codebases that cannot adopt modern C++ features
- Embedded/bare-metal contexts where specific guidelines conflict with hardware constraints (adapt selectively)

## Cross-Cutting Principles

These themes recur across the entire guidelines and form the foundation:

1. **RAII everywhere** (P.8, R.1, E.6, CP.20): Bind resource lifetime to object lifetime
2. **Immutability by default** (P.10, Con.1-5, ES.25): Start with `const`/`constexpr`; mutability is the exception
3. **Type safety** (P.4, I.4, ES.46-49, Enum.3): Use the type system to prevent errors at compile time
4. **Express intent** (P.3, F.1, NL.1-2, T.10): Names, types, and concepts should communicate purpose
5. **Minimize complexity** (F.2-3, ES.5, Per.4-5): Simple code is correct code
6. **Value semantics over pointer semantics** (C.10, R.3-5, F.20, CP.31): Prefer returning by value and scoped objects

## Philosophy & Interfaces (P.*, I.*)

| Rule | Summary |
|------|---------|
| **P.1** | Express ideas directly in code |
| **P.3** | Express intent |
| **P.4** | Ideally, a program should be statically type safe |
| **P.8** | Don't leak any resources |
| **P.10** | Prefer immutable data to mutable data |
| **I.1** | Make interfaces explicit |
| **I.2** | Avoid non-const global variables |
| **I.4** | Make interfaces precisely and strongly typed |
| **I.11** | Never transfer ownership by a raw pointer or reference |

```cpp
// P.10 + I.4: Immutable, strongly typed interface
struct Temperature {
    double kelvin;
};
Temperature boil(const Temperature& water);

// BAD: Weak interface, unclear ownership
double boil(double* temp);
```

## Functions (F.*)

| Rule | Summary |
|------|---------|
| **F.2** | A function should perform a single logical operation |
| **F.4** | If evaluable at compile time, declare it `constexpr` |
| **F.6** | If must not throw, declare it `noexcept` |
| **F.16** | "in" params: cheap types by value, others by `const&` |
| **F.20** | "out" values: prefer return values to output parameters |
| **F.21** | Multiple "out" values: return a struct |

```cpp
// Parameter passing
void print(int x);                         // cheap: by value
void analyze(const std::string& data);     // expensive: by const&
void transform(std::string s);             // sink: by value (will move)

// Return struct, not output params
struct ParseResult { std::string token; int position; };
ParseResult parse(std::string_view input); // GOOD

// Pure, constexpr where possible
constexpr int factorial(int n) noexcept {
    return (n <= 1) ? 1 : n * factorial(n - 1);
}
```

## Classes & Class Hierarchies (C.*)

| Rule | Summary |
|------|---------|
| **C.2** | Use `class` if invariant exists; `struct` if data members vary independently |
| **C.20** | Rule of Zero: avoid defining default operations if you can |
| **C.21** | Rule of Five: if you define any copy/move/dtor, handle them all |
| **C.35** | Base class destructor: public virtual or protected non-virtual |
| **C.46** | Declare single-argument constructors `explicit` |
| **C.128** | Virtual functions: specify exactly one of `virtual`, `override`, or `final` |

```cpp
// Rule of Zero
struct Employee {
    std::string name;
    std::string department;
    int id;
    // No destructor, copy/move needed
};

// Rule of Five (when managing a resource)
class Buffer {
public:
    explicit Buffer(std::size_t size)
        : data_(std::make_unique<char[]>(size)), size_(size) {}
    ~Buffer() = default;
    Buffer(const Buffer& other);
    Buffer& operator=(const Buffer& other);
    Buffer(Buffer&&) noexcept = default;
    Buffer& operator=(Buffer&&) noexcept = default;
private:
    std::unique_ptr<char[]> data_;
    std::size_t size_;
};

// Hierarchy
class Shape {
public:
    virtual ~Shape() = default;
    virtual double area() const = 0;
};

class Circle : public Shape {
public:
    explicit Circle(double r) : radius_(r) {}
    double area() const override { return 3.14159 * radius_ * radius_; }
private:
    double radius_;
};
```

## Resource Management (R.*)

| Rule | Summary |
|------|---------|
| **R.1** | Manage resources automatically using RAII |
| **R.3** | A raw pointer (`T*`) is non-owning |
| **R.11** | Avoid calling `new` and `delete` explicitly |
| **R.20** | Use `unique_ptr` or `shared_ptr` to represent ownership |
| **R.21** | Prefer `unique_ptr` over `shared_ptr` unless sharing |

```cpp
// RAII with smart pointers
auto widget = std::make_unique<Widget>("config");  // unique ownership
auto cache  = std::make_shared<Cache>(1024);       // shared ownership

// Raw pointer = non-owning observer
void render(const Widget* w) {  // does NOT own w
    if (w) w->draw();
}
render(widget.get());
```

## Expressions & Statements (ES.*)

| Rule | Summary |
|------|---------|
| **ES.20** | Always initialize an object |
| **ES.23** | Prefer `{}` initializer syntax |
| **ES.25** | Declare objects `const` or `constexpr` unless modification intended |
| **ES.28** | Use lambdas for complex initialization of `const` variables |
| **ES.47** | Use `nullptr` rather than `0` or `NULL` |
| **ES.48** | Avoid casts (especially C-style) |

```cpp
// Always initialize, prefer {}, default to const
const int max_retries{3};
const std::vector<int> primes{2, 3, 5, 7, 11};

// Lambda for complex const initialization
const auto config = [&] {
    Config c;
    c.timeout = std::chrono::seconds{30};
    c.retries = max_retries;
    return c;
}();
```

## Error Handling (E.*)

| Rule | Summary |
|------|---------|
| **E.6** | Use RAII to prevent leaks |
| **E.14** | Use purpose-designed user-defined types as exceptions |
| **E.15** | Throw by value, catch by reference |
| **E.17** | Don't try to catch every exception in every function |

```cpp
class AppError : public std::runtime_error {
    using std::runtime_error::runtime_error;
};

class NetworkError : public AppError {
public:
    NetworkError(const std::string& msg, int code)
        : AppError(msg), status_code(code) {}
    int status_code;
};

try {
    fetch_data("https://api.example.com");
} catch (const NetworkError& e) {
    log_error(e.what(), e.status_code);
} catch (const AppError& e) {
    log_error(e.what());
}
```

## Constants & Immutability (Con.*)

```cpp
// Con.1-5: Immutability by default
class Sensor {
public:
    explicit Sensor(std::string id) : id_(std::move(id)) {}
    const std::string& id() const { return id_; }      // Con.2: const methods
    double last_reading() const { return reading_; }
    void record(double value) { reading_ = value; }    // Non-const only when needed
private:
    const std::string id_;     // Con.4: never changes
    double reading_{0.0};
};

constexpr double PI = 3.14159265358979;  // Con.5: compile-time
```

## Concurrency (CP.*)

| Rule | Summary |
|------|---------|
| **CP.20** | Use RAII, never plain `lock()`/`unlock()` |
| **CP.21** | Use `std::scoped_lock` to acquire multiple mutexes |
| **CP.42** | Don't wait without a condition |
| **CP.44** | Name your `lock_guard`s and `unique_lock`s |

```cpp
// Safe locking with RAII
class ThreadSafeQueue {
public:
    void push(int value) {
        std::lock_guard<std::mutex> lock(mutex_);  // CP.44: named!
        queue_.push(value);
        cv_.notify_one();
    }
    int pop() {
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [this] { return !queue_.empty(); }); // CP.42
        int value = queue_.front();
        queue_.pop();
        return value;
    }
private:
    std::mutex mutex_;
    std::condition_variable cv_;
    std::queue<int> queue_;
};

// CP.21: scoped_lock for multiple mutexes (deadlock-free)
void transfer(Account& from, Account& to, double amount) {
    std::scoped_lock lock(from.mutex_, to.mutex_);
    from.balance_ -= amount;
    to.balance_ += amount;
}
```

## Templates & Concepts (T.*)

```cpp
#include <concepts>

// T.10 + T.11: Constrain templates with concepts
template<std::integral T>
T gcd(T a, T b) {
    while (b != 0) { a = std::exchange(b, a % b); }
    return a;
}

// T.13: Shorthand concept syntax
void sort(std::ranges::random_access_range auto& range) {
    std::ranges::sort(range);
}

// Custom concept
template<typename T>
concept Serializable = requires(const T& t) {
    { t.serialize() } -> std::convertible_to<std::string>;
};
```

## Enumerations (Enum.*)

```cpp
// Enum.3 + Enum.5: Scoped enum, no ALL_CAPS
enum class Color { red, green, blue };
enum class LogLevel { debug, info, warning, error };

// BAD: plain enum leaks names
enum { RED, GREEN, BLUE };  // avoid
```

## Naming & Source Files (SF.*, NL.*)

- Prefer `underscore_style` names (NL.10)
- `ALL_CAPS` for macro names only (NL.9)
- No Hungarian notation (NL.5)
- No `using namespace` in headers at global scope (SF.7)
- Headers: include guards + self-contained (SF.8, SF.11)
- Use `'\n'` not `std::endl` (SL.io.50)

## Quick Reference Checklist

Before marking C++ work complete:

- [ ] No raw `new`/`delete` — use smart pointers or RAII (R.11)
- [ ] Objects initialized at declaration (ES.20)
- [ ] Variables are `const`/`constexpr` by default (Con.1, ES.25)
- [ ] `enum class` instead of plain `enum` (Enum.3)
- [ ] `nullptr` instead of `0`/`NULL` (ES.47)
- [ ] No C-style casts (ES.48)
- [ ] Single-argument constructors are `explicit` (C.46)
- [ ] Rule of Zero or Rule of Five applied (C.20, C.21)
- [ ] Templates constrained with concepts (T.10)
- [ ] Locks use RAII (`scoped_lock`/`lock_guard`) (CP.20)
- [ ] Exceptions: custom types, throw by value, catch by reference (E.14, E.15)
- [ ] No `using namespace` in headers (SF.7)
