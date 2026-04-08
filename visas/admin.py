from django.contrib import admin

from .models import RequiredDocument, Visa, VisaFAQ, VisaRoadmapStep, VisaTip


class VisaRoadmapStepInline(admin.TabularInline):
    model = VisaRoadmapStep
    extra = 0
    fields = ("order", "title", "description", "is_optional")
    ordering = ("order", "id")


class RequiredDocumentInline(admin.TabularInline):
    model = RequiredDocument
    extra = 0
    fields = ("order", "name", "description", "is_mandatory")
    ordering = ("order", "id")


class VisaTipInline(admin.TabularInline):
    model = VisaTip
    extra = 0
    fields = ("order", "title", "description")
    ordering = ("order", "id")


class VisaFAQInline(admin.TabularInline):
    model = VisaFAQ
    extra = 0
    fields = ("order", "question", "answer")
    ordering = ("order", "id")


@admin.register(Visa)
class VisaAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "type",
        "cost",
        "currency",
        "difficulty",
        "is_active",
        "is_featured",
        "updated_at",
    )
    list_filter = ("country", "type", "difficulty", "is_active", "is_featured")
    search_fields = ("name", "slug", "country__name", "country__code")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("country__name", "name")
    readonly_fields = ("created_at", "updated_at")
    inlines = (VisaRoadmapStepInline, RequiredDocumentInline, VisaTipInline, VisaFAQInline)

    fieldsets = (
        (None, {"fields": ("country", "name", "slug", "type")}),
        ("Overview", {"fields": ("description", "roadmap")}),
        (
            "Details",
            {
                "fields": (
                    ("cost", "currency"),
                    ("stay_duration_days", "process_time_days"),
                    "difficulty",
                )
            },
        ),
        ("Visibility", {"fields": ("is_active", "is_featured")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(VisaRoadmapStep)
class VisaRoadmapStepAdmin(admin.ModelAdmin):
    list_display = ("visa", "order", "title", "is_optional", "updated_at")
    list_filter = ("is_optional", "visa__country")
    search_fields = ("title", "visa__name", "visa__country__name", "visa__country__code")
    ordering = ("visa", "order", "id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(RequiredDocument)
class RequiredDocumentAdmin(admin.ModelAdmin):
    list_display = ("visa", "order", "name", "is_mandatory", "updated_at")
    list_filter = ("is_mandatory", "visa__country")
    search_fields = ("name", "visa__name", "visa__country__name", "visa__country__code")
    ordering = ("visa", "order", "id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VisaTip)
class VisaTipAdmin(admin.ModelAdmin):
    list_display = ("visa", "order", "title", "updated_at")
    list_filter = ("visa__country",)
    search_fields = ("title", "description", "visa__name", "visa__country__name", "visa__country__code")
    ordering = ("visa", "order", "id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VisaFAQ)
class VisaFAQAdmin(admin.ModelAdmin):
    list_display = ("visa", "order", "question", "updated_at")
    list_filter = ("visa__country",)
    search_fields = ("question", "answer", "visa__name", "visa__country__name", "visa__country__code")
    ordering = ("visa", "order", "id")
    readonly_fields = ("created_at", "updated_at")

