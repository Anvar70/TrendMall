from io import BytesIO
from pathlib import Path
from uuid import uuid4
from PIL import Image, UnidentifiedImageError
from django.core.exceptions import ValidationError


def image_path(instance, filename):
    return f'images/{uuid4().hex}{Path(filename).suffix.lower()}'


def validate_image(file):
    if file.size > 5 * 1024 * 1024:
        raise ValidationError('Image must be at most 5 MB.')
    if Path(file.name).suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
        raise ValidationError('Only JPEG, PNG and WebP images are allowed.')
    try:
        raw = file.read()
        with Image.open(BytesIO(raw)) as image:
            if image.format not in ('JPEG', 'PNG', 'WEBP') or image.width * image.height > 20_000_000 or max(image.size) > 8000:
                raise ValidationError('Image dimensions or format are not supported.')
            image.verify()
        with Image.open(BytesIO(raw)) as image:
            image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ValidationError('Invalid image.')
    finally:
        file.seek(0)
