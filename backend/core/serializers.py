from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

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
            "created_at",
        ]
        read_only_fields = ["id", "headphone", "created_at"]

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
        if value < 1:
            raise serializers.ValidationError("Duration must be at least 1 minute.")
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

        return attrs

    def create(self, validated_data):
        return ListeningSession.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )
