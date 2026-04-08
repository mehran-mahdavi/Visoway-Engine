from decimal import Decimal, InvalidOperation

from django.db.models import Prefetch
from rest_framework import filters, generics, viewsets
from rest_framework.exceptions import NotFound

from .models import RequiredDocument, Visa, VisaFAQ, VisaRoadmapStep, VisaTip
from .serializers import VisaDetailSerializer, VisaListSerializer


def _parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None


class VisaViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("name", "country__name", "country__code", "type")
    ordering_fields = (
        "name",
        "cost",
        "difficulty",
        "process_time_days",
        "stay_duration_days",
        "updated_at",
    )
    ordering = ("country__name", "name")
    lookup_field = "slug"

    def get_queryset(self):
        qs = Visa.objects.select_related("country").filter(is_active=True, country__is_active=True)

        # Filters
        country = self.request.query_params.get("country")
        if country:
            # Supports country id or country code (ISO2)
            if country.isdigit():
                qs = qs.filter(country_id=int(country))
            else:
                qs = qs.filter(country__code__iexact=country.strip())

        visa_type = self.request.query_params.get("type")
        if visa_type:
            qs = qs.filter(type=visa_type.strip())

        difficulty = _parse_int(self.request.query_params.get("difficulty"))
        if difficulty:
            qs = qs.filter(difficulty=difficulty)

        cost_min = _parse_decimal(self.request.query_params.get("cost_min"))
        if cost_min is not None:
            qs = qs.filter(cost__gte=cost_min)

        cost_max = _parse_decimal(self.request.query_params.get("cost_max"))
        if cost_max is not None:
            qs = qs.filter(cost__lte=cost_max)

        if self.action == "retrieve":
            qs = qs.prefetch_related(
                Prefetch("roadmap_steps", queryset=VisaRoadmapStep.objects.order_by("order", "id")),
                Prefetch("required_documents", queryset=RequiredDocument.objects.order_by("order", "id")),
                Prefetch("tips", queryset=VisaTip.objects.order_by("order", "id")),
                Prefetch("faqs", queryset=VisaFAQ.objects.order_by("order", "id")),
            )

        return qs

    def get_serializer_class(self):
        return VisaDetailSerializer if self.action == "retrieve" else VisaListSerializer


class VisaByCountryListAPIView(generics.ListAPIView):
    """
    List visas for a given country identifier.

    `country` can be: country slug, ISO2 code, or full name (case-insensitive).
    """

    serializer_class = VisaListSerializer
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("name", "cost", "difficulty", "process_time_days", "stay_duration_days", "updated_at")
    ordering = ("name",)

    def get_queryset(self):
        country = self.kwargs.get("country", "").strip()
        if not country:
            raise NotFound("Country is required.")

        qs = Visa.objects.select_related("country").filter(is_active=True, country__is_active=True)

        # Prefer exact-ish identifiers first (slug/code), then name.
        filtered = qs.filter(country__slug__iexact=country)
        if not filtered.exists():
            filtered = qs.filter(country__code__iexact=country)
        if not filtered.exists():
            filtered = qs.filter(country__name__iexact=country)
        if not filtered.exists():
            filtered = qs.filter(country__name__icontains=country)

        if not filtered.exists():
            raise NotFound(f"No visas found for country '{country}'.")

        return filtered


class VisaBySlugRetrieveAPIView(generics.RetrieveAPIView):
    """
    Retrieve a single visa by country and slug with nested details.
    """

    serializer_class = VisaDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        country = self.kwargs.get("country", "").strip()

        qs = (
            Visa.objects.select_related("country")
            .filter(is_active=True, country__is_active=True)
            .prefetch_related(
                Prefetch("roadmap_steps", queryset=VisaRoadmapStep.objects.order_by("order", "id")),
                Prefetch("required_documents", queryset=RequiredDocument.objects.order_by("order", "id")),
                Prefetch("tips", queryset=VisaTip.objects.order_by("order", "id")),
                Prefetch("faqs", queryset=VisaFAQ.objects.order_by("order", "id")),
            )
        )

        if country:
            filtered = qs.filter(country__slug__iexact=country)
            if not filtered.exists():
                filtered = qs.filter(country__code__iexact=country)
            if not filtered.exists():
                filtered = qs.filter(country__name__iexact=country)
            qs = filtered

        return qs

