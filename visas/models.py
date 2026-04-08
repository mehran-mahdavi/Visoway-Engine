from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class VisaType(models.TextChoices):
    WORK = "work", "Work"
    EDUCATION = "education", "Education"
    DIGITAL_NOMAD = "digital_nomad", "Digital nomad"
    TOURIST = "tourist", "Tourist"
    RESIDENCY = "residency", "Residency"
    INVESTMENT = "investment", "Investment"
    FAMILY = "family", "Family"


class VisaDifficulty(models.IntegerChoices):
    EASY = 1, "1 (Easy)"
    MEDIUM = 2, "2 (Medium)"
    HARD = 3, "3 (Hard)"


class Visa(TimeStampedModel):
    country = models.ForeignKey(
        "countries.Country",
        on_delete=models.PROTECT,
        related_name="visas",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    type = models.CharField(max_length=32, choices=VisaType.choices)

    description = models.TextField(blank=True)
    roadmap = models.TextField(
        blank=True,
        help_text="Optional overview/notes. Use Roadmap Steps below for ordered steps.",
    )

    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="ISO 4217 currency code (e.g. USD, EUR).",
    )
    stay_duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Typical allowed stay in days (if applicable).",
    )
    process_time_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Typical processing time in days (if known).",
    )
    difficulty = models.PositiveSmallIntegerField(
        choices=VisaDifficulty.choices,
        default=VisaDifficulty.MEDIUM,
    )

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["country__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["country", "slug"],
                name="uniq_visa_country_slug",
            ),
        ]
        indexes = [
            models.Index(fields=["country", "type"]),
            models.Index(fields=["is_active", "is_featured"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} — {self.country.code}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:220]
        super().save(*args, **kwargs)


class VisaRoadmapStep(TimeStampedModel):
    visa = models.ForeignKey(
        "visas.Visa",
        on_delete=models.CASCADE,
        related_name="roadmap_steps",
    )
    order = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_optional = models.BooleanField(default=False)

    class Meta:
        verbose_name = "visa roadmap step"
        verbose_name_plural = "visa roadmap steps"
        ordering = ["visa", "order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["visa", "order"],
                name="uniq_visa_roadmap_step_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.visa}: Step {self.order} — {self.title}"


class RequiredDocument(TimeStampedModel):
    visa = models.ForeignKey(
        "visas.Visa",
        on_delete=models.CASCADE,
        related_name="required_documents",
    )
    order = models.PositiveSmallIntegerField(default=1)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        ordering = ["visa", "order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["visa", "order"],
                name="uniq_visa_required_document_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.visa}: {self.name}"


class VisaTip(TimeStampedModel):
    visa = models.ForeignKey(
        "visas.Visa",
        on_delete=models.CASCADE,
        related_name="tips",
    )
    order = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "visa tip"
        verbose_name_plural = "visa tips"
        ordering = ["visa", "order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["visa", "order"],
                name="uniq_visa_tip_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.visa}: Tip {self.order}"


class VisaFAQ(TimeStampedModel):
    visa = models.ForeignKey(
        "visas.Visa",
        on_delete=models.CASCADE,
        related_name="faqs",
    )
    order = models.PositiveSmallIntegerField(default=1)
    question = models.CharField(max_length=300)
    answer = models.TextField()

    class Meta:
        verbose_name = "visa FAQ"
        verbose_name_plural = "visa FAQs"
        ordering = ["visa", "order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["visa", "order"],
                name="uniq_visa_faq_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.visa}: {self.question}"

