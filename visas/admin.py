import json
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.db import transaction

from countries.models import Country
from .models import RequiredDocument, Visa, VisaFAQ, VisaRoadmapStep, VisaTip
from .services.ai_service import (
    suggest_visa_types,
    generate_visa_data,
    fill_partial_data,
    save_generated_relations,
    AIError,
)

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
    change_form_template = "admin/visas/visa/change_form.html"
    
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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "suggest-ai/",
                self.admin_site.admin_view(self.suggest_ai_view),
                name="visas_visa_suggest_ai",
            ),
            path(
                "generate-ai/",
                self.admin_site.admin_view(self.generate_ai_view),
                name="visas_visa_generate_ai",
            ),
        ]
        return custom_urls + urls

    @method_decorator(csrf_protect)
    def suggest_ai_view(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "POST required"}, status=405)
        
        try:
            data = json.loads(request.body)
            country_name = data.get("country_name")
            if not country_name:
                return JsonResponse({"error": "Country Name is required"}, status=400)
                
            # If they provide country_id we can still fetch existing types reliably,
            # but we use country_name for the AI prompt.
            country_id = data.get("country_id")
            existing_types = []
            if country_id:
                try:
                    country = Country.objects.get(pk=country_id)
                    existing_types = list(Visa.objects.filter(country=country).values_list("type", flat=True).distinct())
                except Country.DoesNotExist:
                    pass
            
            suggestions = suggest_visa_types(country_name, existing_types)
            return JsonResponse({"suggestions": suggestions})
            
        except AIError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": "Internal server error"}, status=500)

    @method_decorator(csrf_protect)
    def generate_ai_view(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "POST required"}, status=405)
            
        try:
            data = json.loads(request.body)
            country_id = data.get("country_id")
            visa_type = data.get("type")
            partial_data = data.get("partial_data", {})
            
            if not country_id:
                return JsonResponse({"error": "Country ID is required"}, status=400)
                
            country = Country.objects.get(pk=country_id)
            
            # If we have some partial data with at least a type or name, we can fill it
            if partial_data and any(v for k, v in partial_data.items() if k not in ["country", "country_id"]):
                result = fill_partial_data(country, partial_data)
            else:
                if not visa_type:
                    visa_type = partial_data.get("type") or "General"
                result = generate_visa_data(country, visa_type)
                
            return JsonResponse({"data": result})
            
        except Country.DoesNotExist:
            return JsonResponse({"error": "Country not found"}, status=404)
        except AIError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": "Internal server error"}, status=500)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        
        # If frontend sent hidden field with ai relations, we process them
        # (This implements the strict bulk_create relations requirement)
        ai_relations_json = request.POST.get("_ai_relations_data")
        if ai_relations_json:
            try:
                ai_data = json.loads(ai_relations_json)
                save_generated_relations(form.instance, ai_data)
            except Exception as e:
                pass


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
