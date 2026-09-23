# QA natijalari

Tasdiqlangan tekshiruvlar:

- `python manage.py check` — muvaffaqiyatli.
- `python manage.py makemigrations --check --dry-run` — o‘zgarish yo‘q.
- SQLite test suite — 40 test, 37 passed, 3 PostgreSQL-only skipped.
- PostgreSQL concurrency suite — 3 test passed: oxirgi dona, parallel idempotency va parallel cancel.
- `seed_demo` ketma-ket ikki marta ishga tushirildi: 6 kategoriya, 24 mahsulot, 48 variant va 6 order nusxalanmadi.
- Local HTTP smoke — 66 check passed: guest, customer, admin route/API/static oqimlari.
- OpenAPI `spectacular --validate --fail-on-warn` — muvaffaqiyatli.
- JavaScript ES module syntax — barcha static JS fayllar tekshirildi.

Brauzer UI screenshot/viewport QA bu muhitda brauzer connector mavjud bo‘lmagani sabab bajarilmadi. Local HTTP smoke va responsive CSS kod tekshirildi; vizual QA uchun loyiha ishga tushgach Chrome’da `/`, `/login/`, `/shop/` va `/admin/dashboard/` sahifalarini ko‘rish kerak.
