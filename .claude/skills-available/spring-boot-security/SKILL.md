---
name: spring-boot-security
description: Spring Security configuration, OAuth2/JWT integration, CORS policies, CSRF protection, method-level security, security filter chain patterns
---
# Spring Boot Security Skill

## Security Filter Chain (Spring Security 6+)

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf
                .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
                .ignoringRequestMatchers("/api/**")  // Disable for stateless API
            )
            .cors(cors -> cors.configurationSource(corsConfigSource()))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/public/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .requestMatchers("/api/**").authenticated()
                .anyRequest().permitAll()
            )
            .sessionManagement(session -> session
                .sessionCreationPolicy(SessionCreationPolicy.STATELESS)
            )
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()));

        return http.build();
    }
}
```

## JWT Configuration

```java
// application.yml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: https://auth.example.com/
          audiences: my-api

// Custom JWT decoder
@Bean
public JwtDecoder jwtDecoder() {
    NimbusJwtDecoder decoder = JwtDecoders.fromIssuerLocation(issuerUri);
    decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(
        JwtValidators.createDefaultWithIssuer(issuerUri),
        new JwtClaimValidator<>("aud", aud -> aud.contains("my-api"))
    ));
    return decoder;
}

// JWT to Spring authorities mapping
@Bean
public JwtAuthenticationConverter jwtAuthConverter() {
    JwtGrantedAuthoritiesConverter authConverter = new JwtGrantedAuthoritiesConverter();
    authConverter.setAuthoritiesClaimName("roles");
    authConverter.setAuthorityPrefix("ROLE_");

    JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
    converter.setJwtGrantedAuthoritiesConverter(authConverter);
    return converter;
}
```

## CORS Configuration

```java
@Bean
public CorsConfigurationSource corsConfigSource() {
    CorsConfiguration config = new CorsConfiguration();
    config.setAllowedOrigins(List.of("https://app.example.com"));
    config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE"));
    config.setAllowedHeaders(List.of("Authorization", "Content-Type"));
    config.setExposedHeaders(List.of("X-Total-Count"));
    config.setAllowCredentials(true);
    config.setMaxAge(3600L);

    UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
    source.registerCorsConfiguration("/api/**", config);
    return source;
}
```

## Method-Level Security

```java
@Configuration
@EnableMethodSecurity  // Replaces @EnableGlobalMethodSecurity
public class MethodSecurityConfig {}

@Service
public class SiteService {

    @PreAuthorize("hasRole('ADMIN')")
    public void deleteSite(Long id) { ... }

    @PreAuthorize("#site.owner == authentication.name")
    public void updateSite(@P("site") Site site) { ... }

    @PostAuthorize("returnObject.owner == authentication.name")
    public Site getSite(Long id) { ... }

    @PreFilter("filterObject.owner == authentication.name")
    public void batchUpdate(List<Site> sites) { ... }
}
```

## Password Encoding

```java
@Bean
public PasswordEncoder passwordEncoder() {
    return new BCryptPasswordEncoder(12);  // Cost factor 12
}

// NEVER: MD5, SHA-1, SHA-256 without salt
// PREFER: BCrypt (default), Argon2, SCrypt
```

## Common Security Misconfigurations

| Misconfiguration | Risk | Fix |
|-----------------|------|-----|
| CSRF disabled globally | Cross-site request forgery | Disable only for stateless API endpoints |
| `permitAll()` too broad | Unauthenticated access to sensitive endpoints | Use specific matchers |
| Hardcoded secrets | Credential exposure | Use environment variables or Vault |
| Missing rate limiting | Brute force attacks | Add `spring-boot-starter-actuator` + rate limiter |
| No HTTPS enforcement | Man-in-the-middle | `http.requiresChannel().anyRequest().requiresSecure()` |
| Verbose error messages | Information leakage | Custom error handler, no stack traces in prod |
| Missing security headers | XSS, clickjacking | Add Content-Security-Policy, X-Frame-Options |

## Security Headers

```java
http.headers(headers -> headers
    .contentSecurityPolicy(csp -> csp
        .policyDirectives("default-src 'self'; script-src 'self'"))
    .frameOptions(frame -> frame.deny())
    .xssProtection(xss -> xss.headerValue(
        XXssProtectionHeaderWriter.HeaderValue.ENABLED_MODE_BLOCK))
    .httpStrictTransportSecurity(hsts -> hsts
        .maxAgeInSeconds(31536000)
        .includeSubDomains(true))
);
```

## Testing Security

```java
@SpringBootTest
@AutoConfigureMockMvc
class SecurityTest {

    @Autowired MockMvc mockMvc;

    @Test
    void publicEndpointAccessible() throws Exception {
        mockMvc.perform(get("/api/public/health"))
            .andExpect(status().isOk());
    }

    @Test
    void protectedEndpointRequiresAuth() throws Exception {
        mockMvc.perform(get("/api/sites"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(roles = "ADMIN")
    void adminEndpointWithRole() throws Exception {
        mockMvc.perform(delete("/api/admin/sites/1"))
            .andExpect(status().isOk());
    }

    @Test
    @WithMockUser(roles = "USER")
    void adminEndpointForbidden() throws Exception {
        mockMvc.perform(delete("/api/admin/sites/1"))
            .andExpect(status().isForbidden());
    }
}
```
