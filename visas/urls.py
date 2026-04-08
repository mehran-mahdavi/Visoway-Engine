from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import VisaByCountryListAPIView, VisaBySlugRetrieveAPIView, VisaViewSet

router = DefaultRouter()
router.register(r"visas", VisaViewSet, basename="visa")

urlpatterns = [
    # Frontend-friendly shortcut: /api/visa/<country>/<slug>/ (in-depth)
    path("visas/<str:country>/<slug:slug>/", VisaBySlugRetrieveAPIView.as_view(), name="visa-by-slug"),
    # Frontend-friendly shortcut: /api/visa/<country>/
    path("visas/<str:country>/", VisaByCountryListAPIView.as_view(), name="visa-by-country"),
]

urlpatterns += router.urls

