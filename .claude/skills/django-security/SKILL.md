---
name: django-security
description: Django-specific security - CSRF, XSS, SQL injection, auth, secrets
---
# Django Security Skill

## CSRF Protection

### How It Works
Django's CSRF middleware validates a token on every POST/PUT/PATCH/DELETE request.

### Template Forms
```html
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Submit</button>
</form>
```

### AJAX Requests
```javascript
// Get token from cookie
function getCookie(name) {
    const value = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return value ? value.pop() : '';
}

fetch('/api/endpoint/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
});
```

### Exemptions (Use Sparingly)
```python
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt  # Only for webhooks or external API endpoints
def stripe_webhook(request):
    # Validate with Stripe signature instead
    ...
```

## XSS Prevention

### Template Auto-Escaping
Django templates auto-escape HTML by default:
```html
{{ user_input }}          <!-- Auto-escaped: safe -->
{{ user_input|safe }}     <!-- DANGEROUS: bypasses escaping -->
{% autoescape off %}      <!-- DANGEROUS: disables for block -->
```

### mark_safe Rules
```python
from django.utils.safestring import mark_safe

# NEVER mark user input as safe
mark_safe(user_input)  # VULNERABLE

# OK for static HTML you control
mark_safe('<span class="icon">★</span>')

# Use format_html for dynamic content
from django.utils.html import format_html
format_html('<a href="{}">{}</a>', url, label)  # Both args are escaped
```

### Content Security Policy
```python
# django-csp
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "https://cdn.example.com")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # Minimize inline styles
```

## SQL Injection Prevention

### ORM Is Safe
```python
# SAFE: ORM parameterizes queries
User.objects.filter(email=user_input)
User.objects.get(id=user_id)
```

### Raw Queries: Always Parameterize
```python
# VULNERABLE
User.objects.raw(f"SELECT * FROM users WHERE email = '{email}'")

# SAFE: Parameterized
User.objects.raw("SELECT * FROM users WHERE email = %s", [email])

# SAFE: extra() with params
queryset.extra(where=["email = %s"], params=[email])
```

### Never Use string formatting in queries
```python
# VULNERABLE
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# SAFE
cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])
```

## Authentication

### Django Auth Best Practices
```python
# Custom user model (do this at project start)
class User(AbstractUser):
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

# Password validation (settings.py)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Session security
SESSION_COOKIE_SECURE = True      # HTTPS only
SESSION_COOKIE_HTTPONLY = True     # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'   # CSRF protection
SESSION_COOKIE_AGE = 86400        # 24 hours
```

## Permissions

### Object-Level Permissions
```python
# django-guardian or custom
class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user
```

### DRF Permissions
```python
class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        # Users only see their own orders
        return Order.objects.filter(user=self.request.user)
```

## Secrets Management

### django-environ
```python
import environ
env = environ.Env()
environ.Env.read_env('.env')

SECRET_KEY = env('DJANGO_SECRET_KEY')
DATABASE_URL = env.db('DATABASE_URL')
DEBUG = env.bool('DEBUG', default=False)
```

### Rules
- Never commit `.env` files (add to `.gitignore`)
- Use separate secrets per environment (dev/staging/prod)
- Rotate secrets on team member departure
- Use vault (HashiCorp, AWS Secrets Manager) in production
