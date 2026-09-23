import os
from io import BytesIO
from uuid import NAMESPACE_URL, uuid5

from PIL import Image, ImageDraw, ImageEnhance, ImageOps
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.accounts.models import User, Address
from apps.catalog.models import Category, Product, ProductVariant, ProductImage
from apps.cart.services import change_cart
from apps.core.demo_catalog import CATEGORIES, PRODUCTS, DETAILS
from apps.core.models import StoreSettings
from apps.inventory.services import adjust_stock
from apps.messaging.models import Conversation
from apps.messaging.services import send_message
from apps.orders.models import Order
from apps.orders.services import preview, checkout, transition


def illustration(kind, index):
    """Return a realistic local catalog photo, with a deterministic drawn fallback."""
    photo_map = {
        'lamp': 'lamp.png',
        'fan': 'fan.png',
        'organizer': 'organizer.png',
        'box': 'organizer.png',
        'tools': 'tools.png',
        'bottle': 'bottle.png',
        'phone': 'electronics.png',
        'charger': 'electronics.png',
        'stand': 'electronics.png',
        'cable': 'electronics.png',
        'clock': 'electronics.png',
        'pillow': 'organizer.png',
    }
    photo_path = settings.BASE_DIR / 'static' / 'images' / 'products' / photo_map.get(kind, 'organizer.png')
    if photo_path.exists():
        source = Image.open(photo_path).convert('RGB')
        # Keep each catalog card visually distinct while preserving the product.
        zoom = 1.0 + (index % 4) * 0.035
        center = (0.42 + (index % 3) * 0.08, 0.5)
        image = ImageOps.fit(source, (640, 640), method=Image.Resampling.LANCZOS, centering=center, bleed=min(0.04, (zoom - 1) / 2))
        if index % 2:
            image = ImageOps.mirror(image)
        image = ImageEnhance.Color(image).enhance(0.88 + (index % 5) * 0.06)
        image = ImageEnhance.Contrast(image).enhance(0.96 + (index % 4) * 0.025)
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=90, optimize=True)
        return buffer.getvalue()
    backgrounds = ['#e8edf2', '#eee7df', '#e5ece6', '#e7e8f0', '#f0e5dc', '#e6ecee']
    image = Image.new('RGB', (640, 640), backgrounds[index % len(backgrounds)])
    draw = ImageDraw.Draw(image)
    ink, accent, light = '#25364a', '#f97316', '#ffffff'
    draw.ellipse((105, 490, 550, 555), fill='#d0d5da')
    if kind == 'lamp':
        draw.rounded_rectangle((190, 465, 465, 505), 20, fill=ink)
        draw.line((325, 465, 325, 220, 445, 160), fill=ink, width=24)
        draw.rounded_rectangle((235, 145, 460, 195), 22, fill=accent)
        draw.polygon([(260, 200), (445, 200), (505, 420), (180, 420)], fill='#fff4dc')
        draw.line((325, 465, 325, 250), fill=ink, width=24)
    elif kind == 'fan':
        draw.rounded_rectangle((250, 410, 390, 500), 20, fill=ink)
        draw.ellipse((155, 135, 485, 465), fill=light, outline=ink, width=12)
        for box in [(285, 185, 355, 325), (205, 270, 335, 345), (320, 300, 435, 380)]:
            draw.ellipse(box, fill=accent)
        draw.ellipse((285, 285, 355, 355), fill=ink)
    elif kind == 'bottle':
        draw.rounded_rectangle((240, 155, 400, 490), 45, fill=light, outline=ink, width=6)
        draw.rounded_rectangle((265, 105, 375, 170), 15, fill=ink)
        draw.rounded_rectangle((245, 295, 395, 425), 15, fill=accent)
        draw.line((280, 200, 280, 270), fill='#d8e4ee', width=12)
    elif kind in ('phone', 'clock', 'charger'):
        box = (180, 230, 460, 425) if kind == 'clock' else (230, 150, 410, 475)
        draw.rounded_rectangle(box, 28, fill=ink)
        draw.rounded_rectangle((box[0]+18, box[1]+25, box[2]-18, box[3]-35), 15, fill=light)
        if kind == 'clock':
            draw.text((240, 300), '10:24', fill=ink, font_size=45)
        elif kind == 'charger':
            draw.rounded_rectangle((275, 260, 365, 280), 5, fill=ink)
            draw.rounded_rectangle((275, 305, 365, 325), 5, fill=accent)
        else:
            draw.rounded_rectangle((250, 225, 390, 380), 15, fill=accent)
    elif kind == 'stand':
        draw.polygon([(210, 490), (390, 220), (435, 220), (310, 490)], fill=ink)
        draw.rounded_rectangle((180, 465, 470, 505), 18, fill=ink)
        draw.rounded_rectangle((235, 155, 405, 365), 18, fill=accent)
    elif kind == 'cable':
        draw.arc((150, 160, 480, 490), 0, 300, fill=ink, width=22)
        draw.rounded_rectangle((425, 260, 490, 370), 12, fill=accent)
        draw.rounded_rectangle((200, 140, 260, 250), 12, fill=accent)
    elif kind == 'pillow':
        draw.arc((170, 150, 470, 490), 140, 400, fill=accent, width=110)
        draw.ellipse((163, 365, 270, 480), fill=accent)
        draw.ellipse((380, 365, 487, 480), fill=accent)
    elif kind == 'tools':
        for x in (210, 310, 410):
            draw.rounded_rectangle((x, 265, x+28, 500), 12, fill=ink)
            draw.rounded_rectangle((x-22, 150, x+50, 300), 22, fill=accent)
    else:
        draw.rounded_rectangle((140, 220, 500, 480), 25, fill=light, outline=ink, width=5)
        draw.rounded_rectangle((130, 195, 510, 250), 16, fill=accent)
        draw.rounded_rectangle((260, 290, 380, 335), 10, fill=ink)
        if kind == 'organizer':
            for x in (175, 285, 395):
                draw.rounded_rectangle((x, 380, x+70, 445), 12, fill=accent)
    buffer = BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


class Command(BaseCommand):
    help = 'Create an idempotent local demo: 6 categories, 24 products and complete store activity.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_demo is disabled when DEBUG=False.')
        admin = self.account('admin@trendbox.local', 'ADMIN', 'Demo Admin', 'DEMO_ADMIN_PASSWORD')
        customers = [self.account(f'customer{n}@trendbox.local', 'CUSTOMER', f'Demo Customer {n}', 'DEMO_CUSTOMER_PASSWORD') for n in range(1, 4)]
        StoreSettings.load()
        categories = []
        for slug, uz, ru, en in CATEGORIES:
            category, _ = Category.objects.get_or_create(slug=slug, defaults={'name_uz': uz, 'name_ru': ru, 'name_en': en, 'sort_order': len(categories)})
            categories.append(category)
        variants = []
        for index, (slug, category, uz, ru, en, price, kind) in enumerate(PRODUCTS):
            names = dict(zip(('uz', 'ru', 'en'), (uz, ru, en)))
            details = dict(zip(('uz', 'ru', 'en'), DETAILS[kind]))
            defaults = {'category': categories[category], 'is_active': True, 'is_trending': index % 3 == 0}
            for language in names:
                defaults['name_' + language] = names[language]
                defaults['short_description_' + language] = details[language]
                defaults['description_' + language] = names[language] + '. ' + details[language]
            product, _ = Product.objects.get_or_create(slug=slug, defaults=defaults)
            variant, created = ProductVariant.objects.get_or_create(sku=f'DEMO-{index+1:03}-A', defaults={
                'product': product, 'price': price, 'compare_at_price': price + 20000, 'stock': 0})
            if created:
                stock = 0 if index % 8 == 0 else 3 if index % 8 == 1 else 25
                if stock:
                    adjust_stock(admin, variant.pk, stock, 'Demo initial stock', 'INITIAL')
            alternate, created = ProductVariant.objects.get_or_create(sku=f'DEMO-{index+1:03}-B', defaults={
                'product': product, 'price': price + 10000, 'attributes': {'color': 'black'}, 'stock': 0})
            if created and index % 8 != 0:
                adjust_stock(admin, alternate.pk, 10, 'Demo initial stock', 'INITIAL')
            photo = product.images.order_by('id').first()
            if photo is None:
                photo = ProductImage(product=product, is_primary=True)
            photo.alt_uz, photo.alt_ru, photo.alt_en = uz, ru, en
            photo.image.save(slug+'.jpg', ContentFile(illustration(kind, index)), save=True)
            variants.append(variant)
        for index, status in enumerate(['NEW', 'CONFIRMED', 'PACKING', 'SHIPPED', 'DELIVERED', 'CANCELLED']):
            customer = customers[index % len(customers)]
            address, _ = Address.objects.get_or_create(user=customer, label='Demo', defaults={
                'recipient_name': customer.full_name, 'phone': customer.phone, 'region': 'Toshkent',
                'city': 'Yunusobod', 'address_line': 'Demo street, 12', 'is_default': True})
            key = uuid5(NAMESPACE_URL, 'trendbox-demo-order-' + status)
            if not Order.objects.filter(customer=customer, idempotency_key=key).exists():
                change_cart(customer, variant_id=variants[2].pk, quantity=1)
                payload = {'address_id': address.pk, 'comment': 'Demo'}
                quote = preview(customer, payload)
                order, _ = checkout(customer, {**payload, 'quote_token': quote['quote_token'], 'idempotency_key': key})
                if status == 'CANCELLED':
                    transition(admin, order.public_number, status, 'Demo cancellation')
                else:
                    for target in ['CONFIRMED', 'PACKING', 'SHIPPED', 'DELIVERED']:
                        if status == 'NEW':
                            break
                        transition(admin, order.public_number, target, 'Demo status')
                        if target == status:
                            break
        for customer in customers:
            conversation, _ = Conversation.objects.get_or_create(customer=customer)
            if not conversation.messages.exists():
                send_message(conversation, customer, 'Assalomu alaykum! Buyurtmam bo‘yicha yordam kerak.')
                send_message(conversation, admin, 'Assalomu alaykum! Buyurtma raqamini yuboring, yordam beramiz.')
        self.stdout.write(self.style.SUCCESS('Demo ready: 6 categories, 24 products, 48 variants, 6 orders and 3 conversations.'))
        self.stdout.write('Admin: admin@trendbox.local; customers: customer1@trendbox.local through customer3@trendbox.local')
        self.stdout.write('Passwords are read from your local environment and are never printed.')

    def account(self, email, role, name, variable):
        existing = User.objects.filter(email=email).first()
        if existing:
            if existing.role != role:
                raise CommandError(f'{email} already exists with a different role.')
            return existing
        password = os.getenv(variable)
        if not password:
            raise CommandError(f'Set {variable} before creating demo accounts.')
        user = User(email=email, role=role, full_name=name, phone='+998901234567')
        validate_password(password, user)
        user.set_password(password)
        user.full_clean()
        user.save()
        return user
