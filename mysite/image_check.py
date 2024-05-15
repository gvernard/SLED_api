from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.conf import settings


def validate_image_size(image):
    max_mb = 1
    size = image.size # in bytes
    if size > max_mb * 1024**2:
        raise ValidationError("Our max accepted image size is 1 MB.")
