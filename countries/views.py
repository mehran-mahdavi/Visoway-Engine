from django.db.models import Prefetch
from rest_framework import filters, viewsets

from visas.models import Visa

from .models import Country
from .serializers import CountryDetailSerializer, CountryListSerializer


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    v = value.strip().lower()
    if v in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "f", "no", "n", "off"}:
        return False
    return None


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("name", "code")
    ordering_fields = ("name", "code", "is_popular", "is_featured", "updated_at")
    ordering = ("name",)
    lookup_field = "slug"

    def get_queryset(self):
        qs = Country.objects.all()

        # Default to active countries unless explicitly overridden
        is_active = _parse_bool(self.request.query_params.get("is_active"))
        qs = qs.filter(is_active=True) if is_active is None else qs.filter(is_active=is_active)

        is_popular = _parse_bool(self.request.query_params.get("is_popular"))
        if is_popular is not None:
            qs = qs.filter(is_popular=is_popular)

        is_featured = _parse_bool(self.request.query_params.get("is_featured"))
        if is_featured is not None:
            qs = qs.filter(is_featured=is_featured)

        if self.action == "retrieve":
            visa_qs = (
                Visa.objects.filter(is_active=True)
                .only("id", "country_id", "name", "slug", "type", "cost", "currency", "difficulty")
                .order_by("name")
            )
            qs = qs.prefetch_related(Prefetch("visas", queryset=visa_qs))

        return qs

    def get_serializer_class(self):
        return CountryDetailSerializer if self.action == "retrieve" else CountryListSerializer
