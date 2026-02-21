---
name: python-django
description: Django patterns - ORM, middleware, signals, admin, DRF
---
# Python Django Skill

## ORM Optimization

### select_related (FK / OneToOne — single JOIN)
```python
# BAD: N+1 queries
for order in Order.objects.all():
    print(order.customer.name)  # Separate query per order

# GOOD: Single query with JOIN
for order in Order.objects.select_related("customer"):
    print(order.customer.name)  # No extra queries
```

### prefetch_related (ManyToMany / reverse FK — separate query)
```python
# BAD: N+1 queries
for author in Author.objects.all():
    print(author.books.count())  # Separate query per author

# GOOD: Two queries total
for author in Author.objects.prefetch_related("books"):
    print(author.books.count())  # Prefetched
```

### only/defer (Column selection)
```python
# Load only specific fields
User.objects.only("id", "email")     # SELECT id, email FROM ...
User.objects.defer("large_bio_field") # SELECT everything except large_bio_field
```

### Aggregation
```python
from django.db.models import Count, Avg, Q

# Annotate: per-row computation
authors = Author.objects.annotate(book_count=Count("books"))

# Aggregate: single result
avg_price = Book.objects.aggregate(avg=Avg("price"))

# Conditional aggregation
stats = Order.objects.aggregate(
    total=Count("id"),
    paid=Count("id", filter=Q(status="paid")),
)
```

## Middleware Patterns

```python
class TimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Before view
        import time
        start = time.monotonic()

        response = self.get_response(request)

        # After view
        duration = time.monotonic() - start
        response["X-Request-Duration"] = f"{duration:.3f}s"
        return response

    def process_exception(self, request, exception):
        """Called if view raises exception."""
        logger.error(f"View error: {exception}", exc_info=True)
        return None  # Let Django handle it
```

**Order matters**: Middleware runs top-to-bottom on request, bottom-to-top on response.

## Signals Best Practices

### When to Use
- Cross-app notifications (user created → send welcome email)
- Audit logging (model changed → log change)
- Cache invalidation (model saved → clear related cache)

### When to Avoid
- Same-app logic (just call the function directly)
- Complex business logic (hard to debug, implicit flow)
- Anything requiring transaction guarantees (signals fire after commit by default)

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def on_user_created(sender, instance, created, **kwargs):
    if created:
        send_welcome_email.delay(instance.id)  # Async task
```

## Admin Customization

```python
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "total", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["customer__name", "customer__email"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    # Inline related models
    inlines = [OrderItemInline]

    # Custom actions
    actions = ["mark_as_shipped"]

    @admin.action(description="Mark selected orders as shipped")
    def mark_as_shipped(self, request, queryset):
        queryset.update(status="shipped")
```

## Django REST Framework Patterns

### Serializers
```python
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value
```

### ViewSets
```python
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        # Filter by current user's organization
        return super().get_queryset().filter(
            org=self.request.user.org
        )
```

### Permissions
```python
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user
```
