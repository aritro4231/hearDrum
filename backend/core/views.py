from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import ambient as ambient_service
from .exposure import (
    complete_session,
    current_session_for_user,
    daily_exposure_summary,
    pause_session,
    resume_session,
)
from .models import ListeningSession
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


def _session_response(session, request, response_status=status.HTTP_200_OK, **extra):
    body = {
        "session": ListeningSessionSerializer(session).data,
        "today": daily_exposure_summary(request.user),
    }
    body.update(extra)
    return Response(body, status=response_status)


def _owned_session(request, session_id):
    return get_object_or_404(
        request.user.listening_sessions.select_related("headphone"),
        id=session_id,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_listening_session(request):
    session = current_session_for_user(request.user)
    if not session:
        return Response({"session": None, "today": daily_exposure_summary(request.user)})
    return _session_response(session, request)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def today_listening_summary(request):
    return Response(daily_exposure_summary(request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_listening_session(request):
    existing = current_session_for_user(request.user)
    if existing:
        return _session_response(existing, request, recovered=True)

    serializer = ListeningSessionSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    now = timezone.now()
    session = ListeningSession.objects.create(
        user=request.user,
        headphone=serializer.validated_data["headphone"],
        connection_type=serializer.validated_data["connection_type"],
        volume_percent=serializer.validated_data["volume_percent"],
        estimated_db=serializer.validated_data["estimated_db"],
        duration_minutes=0,
        status=ListeningSession.STATUS_ACTIVE,
        started_at=now,
        last_resumed_at=now,
        ambient_analysis_used=serializer.validated_data.get(
            "ambient_analysis_used",
            False,
        ),
        ambient_environment_class=serializer.validated_data.get(
            "ambient_environment_class"
        ),
        ambient_confidence=serializer.validated_data.get("ambient_confidence"),
    )
    return _session_response(session, request, response_status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pause_listening_session(request, session_id):
    session = _owned_session(request, session_id)
    if session.status == ListeningSession.STATUS_COMPLETED:
        return Response(
            {"detail": "Completed sessions cannot be paused."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    pause_session(session)
    return _session_response(session, request)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resume_listening_session(request, session_id):
    session = _owned_session(request, session_id)
    if session.status == ListeningSession.STATUS_COMPLETED:
        return Response(
            {"detail": "Completed sessions cannot be resumed."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    resume_session(session)
    return _session_response(session, request)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_listening_session(request, session_id):
    session = _owned_session(request, session_id)
    complete_session(session)
    return _session_response(session, request, completed=True)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def edit_listening_session_settings(request, session_id):
    session = _owned_session(request, session_id)
    complete_session(session)
    return _session_response(
        session,
        request,
        finalized_for_edit=True,
        next_settings={
            "headphone_name": session.headphone.name,
            "connection_type": session.connection_type,
            "volume_percent": session.volume_percent,
            "estimated_db": session.estimated_db,
        },
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def analyze_ambient(request):
    audio = request.FILES.get("audio")
    if audio is None:
        return Response(
            {"audio": "Upload an audio file in the 'audio' field."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = ambient_service.analyze_ambient_recording(audio)
    except ValidationError as exc:
        return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
    except ambient_service.AmbientModelUnavailable:
        return Response(
            {"detail": "Ambient model is not available on this server."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception:
        return Response(
            {"detail": "Ambient audio could not be analyzed."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(result)


def health(request):
    return JsonResponse({"status": "ok"})

