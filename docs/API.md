# TrendBox API qisqa qo‘llanma

Barcha JSON endpointlar `/api/v1/` ostida. Session cookie ishlatiladi.

1. `GET /api/v1/auth/csrf/` orqali CSRF token oling.
2. `POST /api/v1/auth/register/` yoki `POST /api/v1/auth/login/` yuboring. Har bir `POST`, `PATCH`, `DELETE` so‘rovda `X-CSRFToken` header bo‘lsin.
3. Customer katalogni `GET /products/?search=&category=&min_price=&max_price=&in_stock=true&ordering=&page=` orqali oladi.
4. Checkout: `POST /checkout/preview/`, keyin quote token va UUID idempotency key bilan `POST /orders/`.
5. Admin endpointlari `/admin/` bilan boshlanadi va faqat `role=ADMIN` uchun ochiq.

Ro‘yxat javoblari `count`, `next`, `previous`, `results` shaklida. Decimal qiymatlar JSON string sifatida keladi. Xatolar `code`, `message` va kerak bo‘lsa `field_errors` maydonlarini qaytaradi.

Sxema va interaktiv hujjatlar developmentda `/api/schema/` va `/api/docs/` manzillarida.
