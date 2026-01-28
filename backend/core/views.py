from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils import ALL_HEADPHONES

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

    def matches_type(hp):
        if not listening_type:
            return True
        if hp.get("connection") == listening_type:
            return True
        if listening_type == "wired":
            return hp.get("max_dB_SPL_wired") is not None
        if listening_type == "bluetooth":
            return hp.get("max_dB_SPL_bluetooth") is not None
        return True

    filtered = [hp for hp in ALL_HEADPHONES if matches_type(hp)]
    brands = sorted({hp["name"].split()[0] for hp in filtered})
    return Response({"brands": brands})

@api_view(["GET"])
def list_headphones(request):
    brand = request.GET.get("brand")
    listening_type = request.GET.get("type")
    if not brand:
        return Response({"error": "brand is required"}, status=400)

    def matches_type(hp):
        if not listening_type:
            return True
        if hp.get("connection") == listening_type:
            return True
        if listening_type == "wired":
            return hp.get("max_dB_SPL_wired") is not None
        if listening_type == "bluetooth":
            return hp.get("max_dB_SPL_bluetooth") is not None
        return True

    models = [
        hp for hp in ALL_HEADPHONES
        if hp["name"].lower().startswith(brand.lower()) and matches_type(hp)
    ]

    # this is the duplicate case, kind of annoying
    unique = {}
    for m in models:
        if m["name"] not in unique:
            unique[m["name"]] = m  

    return Response({"models": list(unique.values())})

