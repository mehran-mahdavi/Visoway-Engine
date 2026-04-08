from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


def country_image_upload_to(instance: "Country", filename: str) -> str:
    # Keep uploads organized per-country and stable enough for CDN caching.
    return f"countries/{instance.code.lower()}/{filename}"


class Country(TimeStampedModel):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(
        max_length=2,
        unique=True,
        help_text="ISO 3166-1 alpha-2 (e.g. US, CA, DE).",
    )
    slug = models.SlugField(max_length=180, unique=True)
    image = models.ImageField(
        upload_to=country_image_upload_to,
        blank=True,
        null=True,
    )
    is_popular = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "countries"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "is_popular"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
