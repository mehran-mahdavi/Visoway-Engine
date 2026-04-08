from django.contrib import admin

from .models import Country


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_active",
        "is_popular",
        "is_featured",
        "updated_at",
    )
    list_filter = ("is_active", "is_popular", "is_featured")
    search_fields = ("name", "code", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "code", "slug", "image")}),
        ("Visibility", {"fields": ("is_active", "is_popular", "is_featured")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
