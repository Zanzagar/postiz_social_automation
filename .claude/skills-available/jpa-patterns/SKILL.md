---
name: jpa-patterns
description: JPA/Hibernate entity mapping, lazy vs eager loading, N+1 prevention with @EntityGraph, JPQL optimization, second-level caching, transaction boundaries
---
# JPA Patterns Skill

## Entity Mapping

### Basic Relationships
```java
@Entity
public class Site {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String name;

    // One site has many samples — mapped by Sample.site field
    @OneToMany(mappedBy = "site", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Sample> samples = new ArrayList<>();

    // Many sites belong to one region
    @ManyToOne(fetch = FetchType.LAZY)  // ALWAYS use LAZY for @ManyToOne
    @JoinColumn(name = "region_id")
    private Region region;
}

@Entity
public class Sample {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "site_id", nullable = false)
    private Site site;

    private Double value;
    private LocalDateTime collectedAt;
}
```

### Fetch Type Rules

| Annotation | Default | Recommendation |
|-----------|---------|---------------|
| `@ManyToOne` | EAGER | **Change to LAZY** |
| `@OneToOne` | EAGER | **Change to LAZY** |
| `@OneToMany` | LAZY | Keep LAZY |
| `@ManyToMany` | LAZY | Keep LAZY |

**Rule: Default everything to LAZY, then optimize with @EntityGraph where needed.**

## N+1 Query Prevention

### The Problem
```java
// N+1: 1 query for sites + N queries for each site's samples
List<Site> sites = siteRepository.findAll();
for (Site site : sites) {
    site.getSamples().size();  // Triggers lazy load per site
}
```

### Solution 1: @EntityGraph (Preferred)
```java
public interface SiteRepository extends JpaRepository<Site, Long> {

    // Ad-hoc entity graph
    @EntityGraph(attributePaths = {"samples", "region"})
    List<Site> findAll();

    // Named entity graph
    @EntityGraph("Site.withSamplesAndRegion")
    List<Site> findByActive(boolean active);
}

@Entity
@NamedEntityGraph(
    name = "Site.withSamplesAndRegion",
    attributeNodes = {
        @NamedAttributeNode("samples"),
        @NamedAttributeNode("region")
    }
)
public class Site { ... }
```

### Solution 2: JOIN FETCH (JPQL)
```java
@Query("SELECT s FROM Site s JOIN FETCH s.samples WHERE s.active = true")
List<Site> findActiveWithSamples();

// Warning: JOIN FETCH with pagination doesn't work well
// Use @EntityGraph + Pageable instead
```

### Solution 3: @BatchSize
```java
@OneToMany(mappedBy = "site")
@BatchSize(size = 25)  // Load samples in batches of 25 instead of 1-by-1
private List<Sample> samples;
```

## JPQL Optimization

```java
// Projection — select only needed fields
@Query("SELECT new com.example.dto.SiteSummary(s.id, s.name, COUNT(sm)) " +
       "FROM Site s LEFT JOIN s.samples sm GROUP BY s.id, s.name")
List<SiteSummary> findSummaries();

// Bulk update (bypasses entity lifecycle — be careful)
@Modifying
@Query("UPDATE Site s SET s.active = false WHERE s.lastActivity < :cutoff")
int deactivateStale(@Param("cutoff") LocalDateTime cutoff);

// Native query for complex spatial operations
@Query(value = "SELECT s.* FROM sites s " +
       "WHERE ST_DWithin(s.geom, ST_MakePoint(:lon, :lat)::geography, :radius)",
       nativeQuery = true)
List<Site> findNearby(@Param("lat") double lat, @Param("lon") double lon,
                      @Param("radius") double radius);
```

## Second-Level Cache

```yaml
# application.yml
spring:
  jpa:
    properties:
      hibernate:
        cache:
          use_second_level_cache: true
          region.factory_class: org.hibernate.cache.jcache.JCacheRegionFactory
        javax:
          cache:
            provider: org.ehcache.jsr107.EhcacheCachingProvider
```

```java
@Entity
@Cacheable
@Cache(usage = CacheConcurrencyStrategy.READ_WRITE)
public class Region {
    // Cache entities that are read frequently, written rarely
}

// Cache query results
@QueryHints(@QueryHint(name = "org.hibernate.cacheable", value = "true"))
List<Region> findAll();
```

**When to cache:**
- Reference data (regions, categories, config)
- Rarely changing entities
- Frequently accessed by ID

**When NOT to cache:**
- Frequently updated entities
- Large collections
- Entities with complex relationships

## Transaction Boundaries

```java
@Service
@Transactional(readOnly = true)  // Default: read-only for queries
public class SiteService {

    @Transactional  // Override: read-write for mutations
    public Site create(CreateSiteRequest request) {
        Site site = mapper.toEntity(request);
        return repository.save(site);
    }

    // Inherits readOnly = true — optimized for reads
    public Site findById(Long id) {
        return repository.findById(id)
            .orElseThrow(() -> new NotFoundException("Site", id));
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void auditLog(String action) {
        // Runs in its own transaction — committed even if outer fails
    }
}
```

## Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| EAGER fetch on `@ManyToOne` | Loads entire object graph | Use `FetchType.LAZY` |
| Open Session in View | Lazy loads in controllers, N+1 in templates | Disable OSIV, use DTOs |
| `.save()` inside loops | N separate INSERT statements | Use `saveAll()` batch |
| Missing `@Version` | Lost updates in concurrent access | Add optimistic locking |
| Entity as API response | Exposes internals, lazy load errors | Map to DTOs |
| No index on FK columns | Slow JOINs | Add index for every FK |

## Detached Entity Handling

```java
// Problem: modifying a detached entity
Site site = repository.findById(1L).orElseThrow();
// ... later, after transaction closed ...
site.setName("Updated");  // This is detached!
repository.save(site);     // merge() — works but loads from DB first

// Better: update within transaction
@Transactional
public void updateName(Long id, String name) {
    Site site = repository.findById(id).orElseThrow();
    site.setName(name);
    // No explicit save needed — dirty checking handles it
}
```
