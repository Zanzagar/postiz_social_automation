---
name: django-tdd
description: Django TDD patterns with pytest-django, TestCase vs TransactionTestCase, factory_boy, DRF APIClient testing, model/view/middleware testing
---
# Django TDD Skill

## Test Infrastructure

### pytest-django Setup
```toml
# pyproject.toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = "tests.py test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "--reuse-db --strict-markers"
markers = [
    "slow: slow integration tests",
]
```

### TestCase Hierarchy

| Class | Transaction | Fixtures | Use When |
|-------|------------|----------|----------|
| `SimpleTestCase` | No DB | None | Testing utils, forms, no DB needed |
| `TestCase` | Wraps in transaction, rolls back | Yes | Most tests (fast, isolated) |
| `TransactionTestCase` | Real commits | Yes | Testing transaction behavior, signals |
| `LiveServerTestCase` | Real server | Yes | Selenium/E2E tests |

```python
from django.test import TestCase, TransactionTestCase

class TestUserModel(TestCase):  # DEFAULT: Use this
    """Wrapped in transaction — fast, auto-rollback."""

    def test_create_user(self):
        user = User.objects.create(email="test@example.com")
        assert user.pk is not None

class TestCeleryTask(TransactionTestCase):  # Only when needed
    """Real transactions — for testing on_commit hooks, signals."""
```

## factory_boy Patterns

```python
# tests/factories.py
import factory
from myapp.models import Site, Sample

class SiteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Site

    name = factory.Sequence(lambda n: f"Site-{n:03d}")
    latitude = factory.Faker("latitude")
    longitude = factory.Faker("longitude")
    active = True

class SampleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Sample

    site = factory.SubFactory(SiteFactory)
    value = factory.Faker("pyfloat", min_value=0, max_value=100)
    collected_at = factory.Faker("date_time_this_year", tzinfo=timezone.utc)

# Usage in tests
def test_sample_belongs_to_site():
    sample = SampleFactory()
    assert sample.site is not None
    assert sample.site.name.startswith("Site-")

# Batch creation
def test_aggregation():
    site = SiteFactory()
    SampleFactory.create_batch(50, site=site)
    assert site.samples.count() == 50

# Override attributes
def test_inactive_site():
    site = SiteFactory(active=False)
    assert not site.active
```

## Model Testing

```python
class TestSiteModel(TestCase):
    def test_str_representation(self):
        site = SiteFactory(name="Borehole-Alpha")
        assert str(site) == "Borehole-Alpha"

    def test_coordinates_validation(self):
        with pytest.raises(ValidationError):
            SiteFactory(latitude=999)  # Out of range

    def test_default_values(self):
        site = SiteFactory()
        assert site.active is True
        assert site.created_at is not None

    def test_ordering(self):
        SiteFactory(name="B-Site")
        SiteFactory(name="A-Site")
        sites = list(Site.objects.all())
        assert sites[0].name == "A-Site"  # If Meta.ordering = ['name']

    def test_custom_manager(self):
        SiteFactory(active=True)
        SiteFactory(active=False)
        assert Site.objects.active().count() == 1
```

## View / API Testing

### Django REST Framework
```python
from rest_framework.test import APIClient
from rest_framework import status

class TestSiteAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

    def test_list_sites(self):
        SiteFactory.create_batch(3)
        response = self.client.get("/api/sites/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_create_site(self):
        payload = {"name": "New Site", "latitude": 40.7, "longitude": -74.0}
        response = self.client.post("/api/sites/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Site.objects.filter(name="New Site").exists()

    def test_unauthorized_access(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/sites/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_filter_active_sites(self):
        SiteFactory(active=True)
        SiteFactory(active=False)
        response = self.client.get("/api/sites/?active=true")
        assert len(response.data) == 1
```

### Standard Django Views
```python
class TestSiteViews(TestCase):
    def test_site_list_page(self):
        response = self.client.get(reverse("site-list"))
        assert response.status_code == 200
        self.assertTemplateUsed(response, "sites/list.html")

    def test_site_detail_requires_login(self):
        site = SiteFactory()
        response = self.client.get(reverse("site-detail", args=[site.pk]))
        assert response.status_code == 302  # Redirect to login
```

## Middleware Testing

```python
class TestCRSMiddleware(TestCase):
    def test_adds_crs_header(self):
        response = self.client.get("/api/spatial/")
        assert response["X-CRS"] == "EPSG:4326"

    def test_respects_accept_crs(self):
        response = self.client.get(
            "/api/spatial/",
            HTTP_ACCEPT_CRS="EPSG:32617"
        )
        assert response["X-CRS"] == "EPSG:32617"
```

## Fixture Strategies

```python
# conftest.py — shared fixtures
@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def authenticated_client(api_client):
    user = UserFactory()
    api_client.force_authenticate(user=user)
    return api_client

@pytest.fixture
def sample_dataset():
    """Create a realistic test dataset."""
    site = SiteFactory()
    samples = SampleFactory.create_batch(100, site=site)
    return {"site": site, "samples": samples}
```

## Performance Testing

```python
from django.test.utils import override_settings

class TestQueryPerformance(TestCase):
    def test_site_list_query_count(self):
        SiteFactory.create_batch(20)
        with self.assertNumQueries(2):  # 1 count + 1 select
            response = self.client.get("/api/sites/")
            assert response.status_code == 200

    def test_no_n_plus_one(self):
        """Ensure prefetch_related prevents N+1."""
        sites = SiteFactory.create_batch(10)
        for site in sites:
            SampleFactory.create_batch(5, site=site)

        with self.assertNumQueries(2):  # sites + samples (prefetched)
            list(Site.objects.prefetch_related("samples").all())
```
