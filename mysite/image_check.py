from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.conf import settings


def validate_image_size(image):
    max_mb = 1
    #print(image.file.name)
    #print(image)
    #filename = image.file.upload_to + "/" + image.name
    #filename = settings.MEDIA_ROOT + "/" + image.file.name
    
    #size = default_storage.get_size(filename) # in bytes
    #if  size > max_mb * 1024**2:
    #    raise ValidationError("Our max accepted image size is 1 MB.")
    pass
