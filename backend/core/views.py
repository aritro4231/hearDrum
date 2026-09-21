from django.http import JsonResponse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    HeadphoneSerializer,
    ListeningSessionSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .utils import headphone_brands, headphone_models_for_brand


@api_view(["GET"])
def list_devices(request):
    devices = [
        {"id": "wired", "label": "Wired"},
        {"id": "bluetooth", "label": "Bluetooth"},
    ]
    return Response(devices)


@api_view(["GET"])
def list_brands(request):
    listening_type = request.GET.get("type")
    return Response({"brands": headphone_brands(listening_type)})


@api_view(["GET"])
def list_headphones(request):
    brand = request.GET.get("brand")
    listening_type = request.GET.get("type")
    if not brand:
        return Response({"error": "brand is required"}, status=400)

    models = headphone_models_for_brand(brand, listening_type)
    return Response({"models": HeadphoneSerializer(models, many=True).data})


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {
            "token": token.key,
            "user": UserSerializer(user).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {
            "token": token.key,
            "user": UserSerializer(user).data,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    if request.auth:
        request.auth.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def listening_sessions(request):
    if request.method == "GET":
        sessions = (
            request.user.listening_sessions
            .select_related("headphone")
            .order_by("-created_at")
        )
        return Response(
            {"sessions": ListeningSessionSerializer(sessions, many=True).data}
        )

    serializer = ListeningSessionSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    session = serializer.save()
    return Response(
        ListeningSessionSerializer(session).data,
        status=status.HTTP_201_CREATED,
    )


def health(request):
    return JsonResponse({"status": "ok"})

