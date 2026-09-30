from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Headphone(models.Model):
    CONNECTION_CHOICES = [
        ("wired", "Wired"),
        ("wireless", "Wireless"),
        ("both", "Both"),
    ]

    name = models.CharField(max_length=200, unique=True)
    type = models.CharField(max_length=50)
    connection = models.CharField(
        max_length=20,
        choices=CONNECTION_CHOICES
    )

    max_db_spl_wired = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )

    max_db_spl_bluetooth = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    def __str__(self):
        return self.name


class ListeningSession(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_COMPLETED, "Completed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listening_sessions",
    )

    headphone = models.ForeignKey(
        Headphone,
        on_delete=models.PROTECT,
        related_name="listening_sessions",
    )

    connection_type = models.CharField(max_length=20)
    volume_percent = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    estimated_db = models.FloatField(validators=[MinValueValidator(0)])
    duration_minutes = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_COMPLETED,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    last_resumed_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    accumulated_duration_seconds = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    exposure_percent = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    ambient_analysis_used = models.BooleanField(default=False)
    ambient_environment_class = models.CharField(
        max_length=40,
        null=True,
        blank=True,
    )
    ambient_confidence = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status__in=["active", "paused"]),
                name="one_unfinished_listening_session_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.headphone.name} - {self.created_at}"
