---
name: django-verification
description: Django system checks, manage.py check --deploy, migration verification, template validation, URL resolution testing, settings validation
---
# Django Verification Skill

## Django System Checks

### Built-in Check Framework
```bash
# Run all checks
python manage.py check

# Run with deployment checks (stricter)
python manage.py check --deploy

# Check specific app
python manage.py check myapp

# Check specific tags
python manage.py check --tag security
python manage.py check --tag models
python manage.py check --tag templates
```

### Common --deploy Findings

| Check ID | Issue | Fix |
|----------|-------|-----|
| `security.W001` | DEBUG=True | Set DEBUG=False in production |
| `security.W004` | No SECURE_HSTS_SECONDS | Add HSTS header config |
| `security.W008` | SECURE_SSL_REDIRECT=False | Enable SSL redirect in prod |
| `security.W012` | SESSION_COOKIE_SECURE=False | Set True in production |
| `security.W018` | SECURE_BROWSER_XSS_FILTER missing | Add XSS filter header |

### Custom System Checks
```python
# myapp/checks.py
from django.core.checks import Error, Warning, register

@register()
def check_required_env_vars(app_configs, **kwargs):
    """Verify required environment variables are set."""
    errors = []
    required = ["DATABASE_URL", "SECRET_KEY", "ALLOWED_HOSTS"]
    for var in required:
        if not os.environ.get(var):
            errors.append(
                Error(
                    f"Environment variable {var} is not set",
                    hint=f"Set {var} in .env or environment",
                    id="myapp.E001",
                )
            )
    return errors

@register(Tags.models)
def check_spatial_indexes(app_configs, **kwargs):
    """Verify spatial models have GiST indexes."""
    warnings = []
    for model in apps.get_models():
        for field in model._meta.get_fields():
            if hasattr(field, 'geom_type') and not has_spatial_index(model, field):
                warnings.append(
                    Warning(
                        f"{model.__name__}.{field.name} lacks a spatial index",
                        hint="Add a GiST index for spatial query performance",
                        id="myapp.W001",
                    )
                )
    return warnings
```

## Migration Verification

```bash
# Check for missing migrations
python manage.py makemigrations --check --dry-run

# Show migration plan
python manage.py showmigrations

# Check for migration conflicts
python manage.py makemigrations --merge --check
```

### Migration Safety Checks
```python
# tests/test_migrations.py
from django.test import TestCase

class TestMigrations(TestCase):
    def test_no_pending_migrations(self):
        """Ensure all model changes have migrations."""
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        try:
            call_command("makemigrations", "--check", "--dry-run", stdout=out)
        except SystemExit:
            self.fail(f"Pending migrations detected:\n{out.getvalue()}")

    def test_migrations_reversible(self):
        """Critical migrations should be reversible."""
        from django.core.management import call_command
        # Migrate forward then backward
        call_command("migrate", "myapp", "0005", verbosity=0)
        call_command("migrate", "myapp", "0004", verbosity=0)
        call_command("migrate", "myapp", "0005", verbosity=0)
```

### Dangerous Migration Patterns

| Pattern | Risk | Safer Alternative |
|---------|------|------------------|
| `RemoveField` on large table | Locks table | Add new nullable column, migrate data, remove old |
| `ALTER COLUMN SET NOT NULL` | Full table scan | Add check constraint first |
| `RunSQL` without reverse | Can't roll back | Always provide `reverse_sql` |
| `RenameField` | May break running code | Add new field, copy data, deploy, remove old |
| `AddIndex` on huge table | Long lock | `AddIndex(... concurrently=True)` (Postgres) |

## Template Validation

```python
# tests/test_templates.py
from django.template.loader import get_template
from django.test import TestCase

class TestTemplates(TestCase):
    def test_all_templates_render(self):
        """Verify templates have no syntax errors."""
        from pathlib import Path
        template_dir = Path("templates")
        for template_path in template_dir.rglob("*.html"):
            relative = str(template_path.relative_to(template_dir))
            try:
                get_template(relative)
            except Exception as e:
                self.fail(f"Template {relative} failed: {e}")

    def test_template_context(self):
        """Verify views pass required context."""
        response = self.client.get(reverse("site-list"))
        self.assertIn("sites", response.context)
        self.assertIn("total_count", response.context)
```

## URL Verification

```python
from django.test import TestCase
from django.urls import reverse, resolve, NoReverseMatch

class TestURLs(TestCase):
    def test_all_named_urls_resolve(self):
        """Verify all named URLs can be resolved."""
        url_names = [
            ("site-list", []),
            ("site-detail", [1]),
            ("api-sites", []),
            ("api-site-detail", [1]),
        ]
        for name, args in url_names:
            try:
                url = reverse(name, args=args)
                resolve(url)  # Verify it maps to a view
            except NoReverseMatch:
                self.fail(f"URL '{name}' cannot be reversed")

    def test_api_versioning(self):
        """Verify API URLs are versioned."""
        url = reverse("api-sites")
        assert url.startswith("/api/v1/") or url.startswith("/api/v2/")
```

## Settings Verification

```python
# tests/test_settings.py
import importlib
from django.test import TestCase, override_settings

class TestSettings(TestCase):
    def test_production_settings_importable(self):
        """Production settings should not crash on import."""
        try:
            importlib.import_module("config.settings.production")
        except Exception as e:
            self.fail(f"Production settings import failed: {e}")

    def test_required_apps_installed(self):
        from django.conf import settings
        required = ["django.contrib.auth", "rest_framework"]
        for app in required:
            assert app in settings.INSTALLED_APPS, f"{app} missing"

    def test_database_not_sqlite_in_prod(self):
        """Production should not use SQLite."""
        from django.conf import settings
        if not settings.DEBUG:
            engine = settings.DATABASES["default"]["ENGINE"]
            assert "sqlite" not in engine
```

## Full Django Verification Pipeline

```
/verify (Django project):
├─ Phase 1: python manage.py check --deploy
├─ Phase 2: python manage.py makemigrations --check
├─ Phase 3: ruff check .
├─ Phase 4: pytest --cov=src
├─ Phase 5: bandit -r src/
└─ Phase 6: git diff review
```
