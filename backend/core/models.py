from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


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
        validators=[MinValueValidator(1)]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.headphone.name} - {self.created_at}"
