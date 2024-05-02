from django.core.exceptions import ValidationError


def validate_image_size(image):
    max_mb = 1
    if image.file.size > max_mb * 1024**2:
        raise ValidationError("Our max accepted image size is 1 MB.")