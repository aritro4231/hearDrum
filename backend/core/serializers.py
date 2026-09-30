from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .ambient import AMBIENT_CLASS_CONTEXT
from .exposure import (
    allowable_seconds,
    exposure_percent_for_duration,
    listening_seconds,
)
from .models import Headphone, ListeningSession

User = get_user_model()


class HeadphoneSerializer(serializers.ModelSerializer):
    max_dB_SPL_wired = serializers.CharField(
        source="max_db_spl_wired",
        allow_null=True,
    )
    max_dB_SPL_bluetooth = serializers.CharField(
        source="max_db_spl_bluetooth",
        allow_null=True,
    )

    class Meta:
        model = Headphone
        fields = [
            "name",
            "type",
            "connection",
            "max_dB_SPL_wired",
            "max_dB_SPL_bluetooth",
            "notes",
        ]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        read_only_fields = ["id"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            username=attrs.get("username"),
            password=attrs.get("password"),
        )
        if not user:
            raise serializers.ValidationError("Invalid username or password.")

        attrs["user"] = user
        return attrs


class SessionHeadphoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Headphone
        fields = ["id", "name", "type", "connection"]


class ListeningSessionSerializer(serializers.ModelSerializer):
    headphone = SessionHeadphoneSerializer(read_only=True)
    headphone_id = serializers.IntegerField(write_only=True, required=False)
    headphone_name = serializers.CharField(write_only=True, required=False)
    actual_duration_seconds = serializers.SerializerMethodField()
    current_exposure_percent = serializers.SerializerMethodField()
    allowable_duration_seconds = serializers.SerializerMethodField()
    remaining_safe_seconds = serializers.SerializerMethodField()

    class Meta:
        model = ListeningSession
        fields = [
            "id",
            "headphone",
            "headphone_id",
            "headphone_name",
            "connection_type",
            "volume_percent",
            "estimated_db",
            "duration_minutes",
            "status",
            "started_at",
            "last_resumed_at",
            "paused_at",
            "ended_at",
            "accumulated_duration_seconds",
            "actual_duration_seconds",
            "allowable_duration_seconds",
            "remaining_safe_seconds",
            "exposure_percent",
            "current_exposure_percent",
            "ambient_analysis_used",
            "ambient_environment_class",
            "ambient_confidence",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "headphone",
            "status",
            "started_at",
            "last_resumed_at",
            "paused_at",
            "ended_at",
            "accumulated_duration_seconds",
            "actual_duration_seconds",
            "allowable_duration_seconds",
            "remaining_safe_seconds",
            "exposure_percent",
            "current_exposure_percent",
            "created_at",
        ]

    def validate_connection_type(self, value):
        if value not in {"wired", "bluetooth"}:
            raise serializers.ValidationError("Use 'wired' or 'bluetooth'.")
        return value

    def validate_volume_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Volume percent must be between 0 and 100."
            )
        return value

    def validate_estimated_db(self, value):
        if value < 0:
            raise serializers.ValidationError("Estimated dB must be non-negative.")
        return value

    def validate_duration_minutes(self, value):
        if value < 0:
            raise serializers.ValidationError("Duration must be non-negative.")
        return value

    def validate_ambient_environment_class(self, value):
        if value in {None, ""}:
            return None
        if value not in AMBIENT_CLASS_CONTEXT:
            raise serializers.ValidationError("Unknown ambient environment class.")
        return value

    def validate_ambient_confidence(self, value):
        if value is None:
            return None
        if value < 0 or value > 1:
            raise serializers.ValidationError(
                "Ambient confidence must be between 0 and 1."
            )
        return value

    def validate(self, attrs):
        headphone_id = attrs.pop("headphone_id", None)
        headphone_name = attrs.pop("headphone_name", None)

        if headphone_id is None and not headphone_name:
            raise serializers.ValidationError(
                {"headphone": "Provide headphone_id or headphone_name."}
            )

        try:
            if headphone_id is not None:
                attrs["headphone"] = Headphone.objects.get(id=headphone_id)
            else:
                attrs["headphone"] = Headphone.objects.get(name=headphone_name)
        except Headphone.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"headphone": "Headphone does not exist."}
            ) from exc

        ambient_used = attrs.get("ambient_analysis_used", False)
        ambient_class = attrs.get("ambient_environment_class")
        ambient_confidence = attrs.get("ambient_confidence")
        if ambient_used:
            if not ambient_class:
                raise serializers.ValidationError(
                    {
                        "ambient_environment_class": (
                            "Provide an environment class when ambient analysis is used."
                        )
                    }
                )
            if ambient_confidence is None:
                raise serializers.ValidationError(
                    {
                        "ambient_confidence": (
                            "Provide confidence when ambient analysis is used."
                        )
                    }
                )
        else:
            attrs["ambient_analysis_used"] = False
            attrs["ambient_environment_class"] = None
            attrs["ambient_confidence"] = None

        return attrs

    def create(self, validated_data):
        session = ListeningSession.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )
        if session.status == ListeningSession.STATUS_COMPLETED:
            seconds = session.duration_minutes * 60
            session.accumulated_duration_seconds = seconds
            session.exposure_percent = exposure_percent_for_duration(
                session.estimated_db,
                seconds,
            )
            session.save(
                update_fields=[
                    "accumulated_duration_seconds",
                    "exposure_percent",
                ]
            )
        return session

    def get_actual_duration_seconds(self, obj):
        return round(listening_seconds(obj))

    def get_current_exposure_percent(self, obj):
        return round(
            exposure_percent_for_duration(
                obj.estimated_db,
                listening_seconds(obj),
            ),
            2,
        )

    def get_allowable_duration_seconds(self, obj):
        return round(allowable_seconds(obj.estimated_db))

    def get_remaining_safe_seconds(self, obj):
        remaining = allowable_seconds(obj.estimated_db) - listening_seconds(obj)
        return round(max(0, remaining))
