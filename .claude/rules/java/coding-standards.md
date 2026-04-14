---
paths: ["**/*.java"]
---
<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/java/coding-standards.md -->
# Java Coding Standards

Auto-loaded for `.java` files. Focuses on modern Java (17+) and Spring Boot conventions.

## Naming Conventions

- **Classes**: `PascalCase` — `UserService`, `OrderRepository`
- **Methods/variables**: `camelCase` — `getUserById`, `maxRetries`
- **Constants**: `UPPER_SNAKE_CASE` — `MAX_CONNECTIONS`, `DEFAULT_TIMEOUT`
- **Packages**: `lowercase` — `com.example.auth`, not `com.example.Auth`

### Meaningful Names
```java
// GOOD: Intent-revealing names
Duration sessionTimeout = Duration.ofMinutes(30);
List<User> activeUsers = userRepository.findByStatus(Status.ACTIVE);

// BAD: Abbreviated or generic names
Duration d = Duration.ofMinutes(30);
List<User> list = userRepository.findByStatus(Status.ACTIVE);
```

## Spring Boot Patterns

### Constructor Injection (Always)
```java
// GOOD: Constructor injection — testable, immutable, explicit
@Service
public class UserService {
    private final UserRepository userRepository;
    private final EmailService emailService;

    public UserService(UserRepository userRepository, EmailService emailService) {
        this.userRepository = userRepository;
        this.emailService = emailService;
    }
}

// BAD: Field injection — hidden dependencies, hard to test
@Service
public class UserService {
    @Autowired
    private UserRepository userRepository;  // Don't do this
}
```

### Controller Layer
```java
@RestController
@RequestMapping("/api/v1/users")
public class UserController {
    // Thin controllers — delegate to services
    @GetMapping("/{id}")
    public ResponseEntity<UserDto> getUser(@PathVariable Long id) {
        return userService.findById(id)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }
}
```

### Service Layer
```java
@Service
@Transactional(readOnly = true)
public class UserService {
    // Business logic lives here
    // readOnly = true at class level, override for writes

    @Transactional
    public User createUser(CreateUserRequest request) {
        // Write operations explicitly override readOnly
    }
}
```

## Null Handling

### Use Optional for Return Types
```java
// GOOD: Optional for "might not exist"
public Optional<User> findById(Long id) {
    return userRepository.findById(id);
}

// BAD: Returning null
public User findById(Long id) {
    return userRepository.findById(id).orElse(null);  // Don't do this
}
```

### Never Use Optional for Parameters
```java
// GOOD: Use overloads or @Nullable
public List<User> find(String name) { ... }
public List<User> find(String name, Status status) { ... }

// BAD: Optional as parameter
public List<User> find(Optional<String> name) { ... }  // Don't do this
```

## Immutable Collections

```java
// Prefer immutable factories (Java 9+)
List<String> names = List.of("Alice", "Bob", "Charlie");
Map<String, Integer> scores = Map.of("Alice", 95, "Bob", 87);
Set<String> tags = Set.of("urgent", "review");

// For building collections
List<User> users = userStream
    .filter(User::isActive)
    .collect(Collectors.toUnmodifiableList());
```

## Exception Strategy

### Checked vs Unchecked
```java
// Checked: Recoverable conditions the caller MUST handle
public class InsufficientFundsException extends Exception {
    private final BigDecimal balance;
    private final BigDecimal requested;
    // ...
}

// Unchecked: Programming errors / bugs (no recovery)
public class InvalidConfigurationException extends RuntimeException {
    // Caller can't reasonably recover from a config error at runtime
}
```

### Custom Exception Hierarchy
```java
// Base exception for your domain
public abstract class DomainException extends RuntimeException {
    private final String code;
    protected DomainException(String code, String message) {
        super(message);
        this.code = code;
    }
}

public class UserNotFoundException extends DomainException {
    public UserNotFoundException(Long id) {
        super("USER_NOT_FOUND", "User not found: " + id);
    }
}
```

### Global Exception Handler
```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(DomainException.class)
    public ResponseEntity<ErrorResponse> handleDomain(DomainException ex) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(new ErrorResponse(ex.getCode(), ex.getMessage()));
    }
}
```

## Records (Java 16+)

```java
// Use records for DTOs and value objects
public record UserDto(Long id, String name, String email) {}

public record CreateUserRequest(
    @NotBlank String name,
    @Email String email,
    @Size(min = 8) String password
) {}
```

## Lombok (DTOs Only)

```java
// ACCEPTABLE: Lombok for DTOs, entities, builders
@Data
@Builder
public class UserEntity {
    private Long id;
    private String name;
    private String email;
}

// AVOID: Lombok on service classes — use constructor injection
// AVOID: @SneakyThrows — handle exceptions properly
// AVOID: @Cleanup — use try-with-resources
```

## Testing

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {
    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private UserService userService;

    @Test
    void shouldReturnUserWhenExists() {
        // Given
        var user = new User(1L, "Alice");
        when(userRepository.findById(1L)).thenReturn(Optional.of(user));

        // When
        var result = userService.findById(1L);

        // Then
        assertThat(result).isPresent()
            .hasValueSatisfying(u -> assertThat(u.getName()).isEqualTo("Alice"));
    }
}
```

## Avoid

- `null` returns — use `Optional` or empty collections
- Raw types — always parameterize generics: `List<String>`, not `List`
- `public` fields — use encapsulation, even with Lombok
- `static` utility classes with state — prefer injected services
- Catching `Exception` or `Throwable` broadly — catch specific types
- `synchronized` blocks — prefer `java.util.concurrent` utilities
