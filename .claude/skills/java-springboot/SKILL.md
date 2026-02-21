---
name: java-springboot
description: Spring Boot patterns, dependency injection, JPA/Hibernate, security, actuator
---
# Java Spring Boot Skill

## Spring Boot Patterns

### Auto-Configuration
- Spring Boot auto-configures beans based on classpath dependencies
- Override with `@ConditionalOnProperty`, `@ConditionalOnMissingBean`
- `application.yml` / `application.properties` for configuration

### Profiles
```yaml
# application.yml (default)
spring:
  profiles:
    active: dev

# application-dev.yml (development)
server:
  port: 8080
logging:
  level:
    root: DEBUG

# application-prod.yml (production)
server:
  port: 443
logging:
  level:
    root: WARN
```

Activate: `SPRING_PROFILES_ACTIVE=prod` or `--spring.profiles.active=prod`

## Dependency Injection

### Constructor Injection (Preferred)
```java
@Service
public class UserService {
    private final UserRepository repository;
    private final PasswordEncoder encoder;

    // Single constructor — @Autowired not needed
    public UserService(UserRepository repository, PasswordEncoder encoder) {
        this.repository = repository;
        this.encoder = encoder;
    }
}
```

### Why Constructor Injection
- Fields are `final` (immutable)
- Dependencies are explicit
- Easy to test (pass mocks via constructor)
- Fails fast if dependency is missing

### Avoid
- `@Autowired` on fields (hard to test, hides dependencies)
- Setter injection (allows partially initialized objects)

## JPA / Hibernate Patterns

### Entity Mapping
```java
@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String email;

    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Order> orders = new ArrayList<>();

    @CreationTimestamp
    private Instant createdAt;
}
```

### Lazy Loading
- `@OneToMany` defaults to LAZY (good)
- `@ManyToOne` defaults to EAGER (consider changing to LAZY)
- Use `@EntityGraph` or `JOIN FETCH` to avoid N+1

```java
@EntityGraph(attributePaths = {"orders", "orders.items"})
Optional<User> findWithOrdersById(Long id);

// Or JPQL
@Query("SELECT u FROM User u JOIN FETCH u.orders WHERE u.id = :id")
Optional<User> findWithOrdersById(@Param("id") Long id);
```

### Repository Pattern
```java
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
    List<User> findByActiveTrue();

    @Query("SELECT u FROM User u WHERE u.createdAt > :since")
    List<User> findRecentUsers(@Param("since") Instant since);
}
```

## Security Configuration

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(csrf -> csrf.disable()) // Disable for API
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/public/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
```

### CORS Configuration
```java
@Bean
public CorsConfigurationSource corsConfigurationSource() {
    CorsConfiguration config = new CorsConfiguration();
    config.setAllowedOrigins(List.of("https://myapp.com"));
    config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE"));
    config.setAllowedHeaders(List.of("*"));

    UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
    source.registerCorsConfiguration("/api/**", config);
    return source;
}
```

## Actuator Endpoints

```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, prometheus
  endpoint:
    health:
      show-details: when-authorized
```

Key endpoints:
- `/actuator/health` — Application health (DB, disk, custom checks)
- `/actuator/info` — Build info, git commit
- `/actuator/metrics` — JVM, HTTP, custom metrics
- `/actuator/prometheus` — Prometheus-format metrics

### Custom Health Indicator
```java
@Component
public class ExternalServiceHealth extends AbstractHealthIndicator {
    @Override
    protected void doHealthCheck(Health.Builder builder) {
        if (externalService.isAvailable()) {
            builder.up().withDetail("version", externalService.getVersion());
        } else {
            builder.down().withDetail("error", "Service unreachable");
        }
    }
}
```
