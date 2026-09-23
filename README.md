# TrendBox

Django + Django REST Framework asosidagi bitta do‘konli loyiha. Frontend — Django Templates, CSS va Vanilla JavaScript ES modules. Node.js build talab qilinmaydi.

## Etaplar

Har bir etap alohida commit orqali GitHub’ga yuborilgan. Batafsil tavsif: [docs/ETAPLAR.md](docs/ETAPLAR.md).

1. Poydevor, custom User, session auth va CSRF.
2. Guest/Customer/Admin layout va uch til.
3. Katalog, kategoriya, variant va admin CRUD.
4. Savat, favorites, profil va manzillar.
5. Atomar checkout, ombor, order status va notification.
6. Chat, dashboard va Store Settings.
7. Ishlaydigan ekranlar, lokal rasmlar va idempotent demo.
8. Xavfsizlik, PostgreSQL concurrency, OpenAPI va hujjatlar.

## Talablar

- Python 3.11 yoki yangiroq (ushbu muhitda Python 3.13).
- PostgreSQL tavsiya etiladi; Docker Compose PostgreSQL 17 uchun sozlangan.
- Oddiy lokal demo uchun SQLite ishlaydi. SQLite parallel stock locking kafolatini bermaydi.
- Aniq Python paket versiyalari: [requirements.txt](requirements.txt).
- Brauzer ES modules, native dialog va Fetch API’ni qo‘llashi kerak.

## Windows PowerShell

~~~powershell
git clone https://github.com/Anvar70/TrendMall.git
cd TrendMall
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
~~~

.env ichida SECRET_KEY uchun tasodifiy qiymat va demo akkauntlari uchun kuchli parollarni kiriting. Kalit yaratish:

~~~powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
~~~

SQLite uchun .env ichida DB_ENGINE=sqlite:

~~~powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver
~~~

## Linux / macOS

~~~bash
git clone https://github.com/Anvar70/TrendMall.git
cd TrendMall
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
test -f .env || cp .env.example .env
# .env ichidagi SECRET_KEY va demo parollarini o‘zingiz kiriting.
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
~~~

## PostgreSQL

.env ichida:

~~~dotenv
DB_ENGINE=postgres
POSTGRES_DB=trendbox
POSTGRES_USER=trendbox
POSTGRES_PASSWORD=YOUR_LOCAL_PASSWORD
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
~~~

~~~bash
docker compose up -d db
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
~~~

Docker bo‘lmasa, lokal PostgreSQL’da shu baza va foydalanuvchini yarating. Test suite vaqtinchalik test_<POSTGRES_DB> bazasini yaratadi; test foydalanuvchisiga CREATEDB huquqi kerak. Testlarni production bazasi bilan ishlatmang.

## Kirish va rollar

| Rol | Manzil | Huquq |
|---|---|---|
| Guest | /, /login/, /register/ | Landing va autentifikatsiya |
| Customer | /shop/ | Katalog, savat, buyurtma, profil va support |
| Admin | /admin/login/ → /admin/dashboard/ | Maxsus boshqaruv paneli |

Customer va admin bir-birining login formasi orqali kira olmaydi. Ochiq register faqat CUSTOMER yaratadi. Admin panel standart Django Admin emas.

Demo akkauntlar:

- Admin: admin@trendbox.local — parol DEMO_ADMIN_PASSWORD qiymati.
- Xaridorlar: customer1@trendbox.local, customer2@trendbox.local, customer3@trendbox.local — parol DEMO_CUSTOMER_PASSWORD qiymati.

Bu o‘zgaruvchilarning qiymatlarini lokal .env faylga yoki shell muhitiga siz berasiz; parollar repozitoriyga kiritilmaydi. Ushbu ishchi nusxada lokal demo uchun tasodifiy qiymatlar .env ichida tayyorlangan.

O‘zingizning admin akkauntingizni yaratish:

~~~bash
python manage.py create_store_admin --email admin@example.com --name "Store Admin" --phone +998901234567
~~~

Parol interaktiv so‘raladi. Command oddiy store admin yaratadi; superuser huquqi berilmaydi.

## Demo ma’lumotlar

seed_demo faqat DEBUG=True holatida ishlaydi. 6 kategoriya, 24 mahsulot, 48 variant, uch tildagi kontent, original PNG illustratsiyalar, turli qoldiqlar, 6 buyurtma va 3 support conversation yaratadi.

Qayta ishga tushirilsa nusxa yaratmaydi va mavjud parollarni o‘zgartirmaydi. Ombor va buyurtmalar service layer orqali yaratiladi. Rasmlar ishlab chiqaruvchi fotosi emas, lokal demo illustratsiyalaridir. Internetdan rasm yuklash talab qilinmaydi.

## Muhim xatti-harakatlar

- Email registrga bog‘liq bo‘lmagan unique; telefon +998 formatiga keltiriladi.
- Private resurslar rol va egalik bo‘yicha tekshiriladi.
- Session auth: login/register ham CSRF talab qiladi; logout faqat POST.
- Narxlar Decimal; API summalari string ko‘rinishida.
- Savat stock’ni band qilmaydi. Checkout oldidan server quote olinadi.
- Quote o‘zgarsa qayta tasdiq kerak. UUID idempotency kaliti retry’da saqlanadi.
- Checkout user/cart/variant lock, transaction va snapshot bilan ishlaydi.
- NEW → CONFIRMED → PACKING → SHIPPED → DELIVERED. DELIVERED bilan PAID bir transaction’da yoziladi.
- Customer faqat NEW’ni bekor qiladi; admin NEW/CONFIRMED/PACKING’ni bekor qila oladi. Stock bir marta qaytadi.
- Chat faol oynada 5 soniya; admin Orders va notification soni 12 soniyada yangilanadi. Yashirin tabda polling to‘xtaydi; xatoda interval ortadi.
- Rasmlar JPEG/PNG/WebP, 5 MB, 8000 piksel va 20 megapiksel bilan cheklangan; nomlar tasodifiy.
- Store Settings nom, logo, landing matnlari, support va shipping narxini boshqaradi.

## API

- JSON API: /api/v1/
- OpenAPI: /api/schema/
- Interaktiv hujjat: /api/docs/
- Tayyor sxema: [schema.yml](schema.yml)
- Kontrakt va misollar: [docs/API.md](docs/API.md)

API hujjatlari development’da ochiq; DEBUG=False bo‘lsa faqat ADMIN uchun. Swagger UI fayllari CDN’dan keladi; internet bo‘lmasa schema.yml yoki /api/schema/ orqali hujjatdan foydalaning.

## Tekshiruvlar

~~~bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py spectacular --file schema.yml --validate --fail-on-warn
~~~

PostgreSQL .env sozlamasi bilan concurrency:

~~~bash
python manage.py test apps.orders.test_concurrency --verbosity 2
~~~

SQLite’da 3 concurrency test ochiq ravishda skipped bo‘ladi; ular SQLite bilan tasdiqlangan hisoblanmaydi.

JavaScript uchun ixtiyoriy Node tekshiruvi:

~~~powershell
Get-ChildItem static/js -Recurse -Filter *.js | ForEach-Object {
    Get-Content -Raw -Encoding UTF8 $_.FullName | node --input-type=module --check
    if ($LASTEXITCODE -ne 0) { throw "JavaScript syntax error" }
}
~~~

Natijalar va qolgan vizual tekshiruv: [docs/QA.md](docs/QA.md).

## Production

Bu topshirish lokal ishlash uchun; internetga deployment qilinmagan.

- DEBUG=False, tasodifiy SECRET_KEY, aniq ALLOWED_HOSTS va PostgreSQL ishlating.
- HTTPS reverse proxy va WSGI/ASGI server sozlang; runserver production server emas.
- Session/CSRF cookie’lari DEBUG=False holatida Secure bo‘ladi. HTTPS redirect va HSTS’ni deployment konfiguratsiyasida yoqing.
- collectstatic orqali static fayllarni tayyorlang; media/static’ni web server orqali bering.
- Bir nechta worker bo‘lsa throttling uchun umumiy cache backend kerak; lokal xotira cache’i workerlar orasida umumiy emas.
- .env, media, baza, virtual muhit va loglarni Git’ga qo‘shmang.
- Demo seed production’da bloklangan. Demo akkauntlarini production’ga ko‘chirmang.

