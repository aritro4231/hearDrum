from pathlib import Path

from django.db.models import Q

from .models import Headphone

DATA_DIR = Path(__file__).resolve().parent / "data"
HEADPHONES_PATH = DATA_DIR / "headphones_databasev2.json"


def headphones_for_type(listening_type=None):
    headphones = Headphone.objects.all().order_by("name", "id")

    if listening_type == "wired":
        return headphones.filter(
            Q(connection="wired") | Q(max_db_spl_wired__isnull=False)
        )

    if listening_type == "bluetooth":
        return headphones.filter(
            Q(connection="bluetooth") | Q(max_db_spl_bluetooth__isnull=False)
        )

    return headphones


def headphone_brands(listening_type=None):
    names = headphones_for_type(listening_type).values_list("name", flat=True)
    return sorted({name.split()[0] for name in names if name})


def headphone_models_for_brand(brand, listening_type=None):
    return headphones_for_type(listening_type).filter(name__istartswith=brand)
