from rest_framework import serializers

from countries.models import Country

from .models import RequiredDocument, Visa, VisaFAQ, VisaRoadmapStep, VisaTip


class CountryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ("id", "name", "code", "slug")


class VisaListSerializer(serializers.ModelSerializer):
    country = CountryMiniSerializer(read_only=True)

    class Meta:
        model = Visa
        fields = (
            "id",
            "country",
            "name",
            "slug",
            "type",
            "cost",
            "currency",
            "stay_duration_days",
            "process_time_days",
            "difficulty",
            "is_featured",
        )


class VisaRoadmapStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaRoadmapStep
        fields = ("id", "order", "title", "description", "is_optional")


class RequiredDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequiredDocument
        fields = ("id", "order", "name", "description", "is_mandatory")


class VisaTipSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaTip
        fields = ("id", "order", "title", "description")


class VisaFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaFAQ
        fields = ("id", "order", "question", "answer")


class VisaDetailSerializer(serializers.ModelSerializer):
    country = CountryMiniSerializer(read_only=True)
    roadmap_steps = VisaRoadmapStepSerializer(many=True, read_only=True)
    required_documents = RequiredDocumentSerializer(many=True, read_only=True)
    tips = VisaTipSerializer(many=True, read_only=True)
    faqs = VisaFAQSerializer(many=True, read_only=True)

    class Meta:
        model = Visa
        fields = (
            "id",
            "country",
            "name",
            "slug",
            "type",
            "description",
            "cost",
            "currency",
            "stay_duration_days",
            "process_time_days",
            "difficulty",
            "roadmap",
            "roadmap_steps",
            "required_documents",
            "tips",
            "faqs",
            "is_featured",
        )

