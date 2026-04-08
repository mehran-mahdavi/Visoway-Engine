from rest_framework import serializers

from .models import Country


class CountryListSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    flag_url = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = (
            "id",
            "name",
            "code",
            "slug",
            "image_url",
            "flag_url",
            "is_popular",
            "is_featured",
        )

    def get_image_url(self, obj: Country) -> str | None:
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url

    def get_flag_url(self, obj: Country) -> str | None:
        if not obj.code:
            return None
        return f"https://flagcdn.com/{obj.code.lower()}.svg"


class CountryVisaMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    type = serializers.CharField()
    cost = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    currency = serializers.CharField()
    difficulty = serializers.IntegerField()


class CountryDetailSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    flag_url = serializers.SerializerMethodField()
    visas = CountryVisaMiniSerializer(many=True, read_only=True)

    class Meta:
        model = Country
        fields = (
            "id",
            "name",
            "code",
            "slug",
            "image_url",
            "flag_url",
            "is_popular",
            "is_featured",
            "visas",
        )

    def get_image_url(self, obj: Country) -> str | None:
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url

    def get_flag_url(self, obj: Country) -> str | None:
        if not obj.code:
            return None
        return f"https://flagcdn.com/{obj.code.lower()}.svg"

