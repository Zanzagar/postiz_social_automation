---
name: spring-boot-tdd
description: JUnit 5 + Mockito patterns, @SpringBootTest vs @WebMvcTest slice testing, @DataJpaTest for repositories, TestContainers for integration tests
---
# Spring Boot TDD Skill

## Test Slice Annotations

Use the narrowest slice for fast, focused tests:

| Annotation | What It Loads | Speed | Use For |
|-----------|--------------|-------|---------|
| `@SpringBootTest` | Full context | Slow | Integration tests, E2E |
| `@WebMvcTest` | Web layer only | Fast | Controller tests |
| `@DataJpaTest` | JPA + DB only | Medium | Repository tests |
| `@JsonTest` | JSON serialization | Fast | DTO/serialization tests |
| `@RestClientTest` | REST client | Fast | External API client tests |
| No annotation | Plain JUnit | Fastest | Unit tests, services with mocks |

## Controller Testing (@WebMvcTest)

```java
@WebMvcTest(SiteController.class)
class SiteControllerTest {

    @Autowired MockMvc mockMvc;
    @MockBean SiteService siteService;  // Mock the service layer

    @Test
    void listSites_returnsOk() throws Exception {
        // Arrange
        when(siteService.findAll()).thenReturn(List.of(
            new Site(1L, "Site-A", 40.7, -74.0)
        ));

        // Act & Assert
        mockMvc.perform(get("/api/sites")
                .contentType(MediaType.APPLICATION_JSON))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].name").value("Site-A"))
            .andExpect(jsonPath("$", hasSize(1)));
    }

    @Test
    void createSite_withValidData_returnsCreated() throws Exception {
        // Arrange
        String json = """
            {"name": "New Site", "latitude": 40.7, "longitude": -74.0}
            """;
        when(siteService.create(any())).thenReturn(new Site(1L, "New Site", 40.7, -74.0));

        // Act & Assert
        mockMvc.perform(post("/api/sites")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.name").value("New Site"));
    }

    @Test
    void createSite_withInvalidData_returnsBadRequest() throws Exception {
        String json = """
            {"name": "", "latitude": 999}
            """;
        mockMvc.perform(post("/api/sites")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json))
            .andExpect(status().isBadRequest());
    }
}
```

## Repository Testing (@DataJpaTest)

```java
@DataJpaTest
class SiteRepositoryTest {

    @Autowired SiteRepository repository;
    @Autowired TestEntityManager em;

    @Test
    void findByActive_returnsOnlyActiveSites() {
        // Arrange
        em.persist(new Site("Active", 40.7, -74.0, true));
        em.persist(new Site("Inactive", 41.0, -73.5, false));
        em.flush();

        // Act
        List<Site> active = repository.findByActive(true);

        // Assert
        assertThat(active).hasSize(1);
        assertThat(active.get(0).getName()).isEqualTo("Active");
    }

    @Test
    void findNearby_usesIndex() {
        // Test spatial query if using PostGIS
        em.persist(new Site("Near", 40.71, -74.01, true));
        em.persist(new Site("Far", 50.0, -80.0, true));
        em.flush();

        List<Site> nearby = repository.findWithinRadius(40.7, -74.0, 5000);
        assertThat(nearby).extracting("name").containsOnly("Near");
    }
}
```

## Service Testing (Plain JUnit + Mockito)

```java
@ExtendWith(MockitoExtension.class)
class SiteServiceTest {

    @Mock SiteRepository repository;
    @Mock EventPublisher eventPublisher;
    @InjectMocks SiteService service;

    @Test
    void create_savesSiteAndPublishesEvent() {
        // Arrange
        Site site = new Site("Test", 40.7, -74.0);
        when(repository.save(any())).thenReturn(site.withId(1L));

        // Act
        Site result = service.create(site);

        // Assert
        assertThat(result.getId()).isEqualTo(1L);
        verify(repository).save(site);
        verify(eventPublisher).publish(any(SiteCreatedEvent.class));
    }

    @Test
    void create_withDuplicateName_throwsException() {
        when(repository.existsByName("Existing")).thenReturn(true);

        assertThatThrownBy(() -> service.create(new Site("Existing", 0, 0)))
            .isInstanceOf(DuplicateNameException.class);

        verify(repository, never()).save(any());
    }
}
```

## TestContainers for Integration

```java
@SpringBootTest
@Testcontainers
class SiteIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgis/postgis:16-3.4")
        .withDatabaseName("testdb");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired SiteRepository repository;

    @Test
    void fullCrudCycle() {
        // Create
        Site site = repository.save(new Site("IntTest", 40.7, -74.0));
        assertThat(site.getId()).isNotNull();

        // Read
        Site found = repository.findById(site.getId()).orElseThrow();
        assertThat(found.getName()).isEqualTo("IntTest");

        // Update
        found.setName("Updated");
        repository.save(found);
        assertThat(repository.findById(site.getId()).get().getName()).isEqualTo("Updated");

        // Delete
        repository.deleteById(site.getId());
        assertThat(repository.findById(site.getId())).isEmpty();
    }
}
```

## Mockito Patterns

```java
// Argument matchers
when(repo.findById(anyLong())).thenReturn(Optional.of(site));
when(repo.findByName(eq("exact"))).thenReturn(site);
when(repo.save(argThat(s -> s.getName().startsWith("Site")))).thenReturn(site);

// Verify interactions
verify(repo, times(1)).save(any());
verify(repo, never()).delete(any());
verify(repo, atLeastOnce()).findById(anyLong());

// Argument captor
ArgumentCaptor<Site> captor = ArgumentCaptor.forClass(Site.class);
verify(repo).save(captor.capture());
assertThat(captor.getValue().getName()).isEqualTo("Expected");

// Exception throwing
when(repo.findById(999L)).thenThrow(new NotFoundException("Not found"));

// Void method throws
doThrow(new RuntimeException("DB down")).when(repo).delete(any());

// Sequential returns
when(repo.count()).thenReturn(0L, 1L, 2L);  // Returns 0, then 1, then 2
```

## Test Organization

```
src/test/java/com/example/
├── unit/                    # Fast, no Spring context
│   ├── service/
│   │   └── SiteServiceTest.java
│   └── util/
│       └── CoordinateUtilTest.java
├── integration/             # Spring context, real DB
│   ├── repository/
│   │   └── SiteRepositoryTest.java
│   └── api/
│       └── SiteApiIntegrationTest.java
└── e2e/                     # Full stack
    └── SiteWorkflowTest.java
```
