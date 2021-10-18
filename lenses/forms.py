# forms.py
from django.forms import modelformset_factory
from lenses.models import Lenses

LensFormSet = modelformset_factory(
    Lenses,
    fields=("ra", "dec", "access_level"),
    max_num=5,
    absolute_max=5,
)
