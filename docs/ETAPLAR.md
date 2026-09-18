# TrendBox ishlab chiqish etaplari

Har bir etap tekshiriladi va alohida commit orqali GitHub'ga yuboriladi.

1. **Poydevor va autentifikatsiya:** muhit sozlamalari, PostgreSQL/SQLite, custom User, session auth, CSRF, rol ruxsatlari va admin yaratish buyrug‘i.
2. **Interfeys poydevori:** Guest/Customer/Admin sahifalari, alohida navigatsiya, uch til, moslashuvchan dizayn va API yordamchilari.
3. **Katalog va boshqaruv:** kategoriyalar, mahsulotlar, variantlar, rasmlar va admin CRUD.
4. **Xaridor kabineti:** sevimlilar, savat, manzillar, profil va sozlamalar.
5. **Buyurtma va ombor:** atomar checkout, idempotency, qoldiq jurnali, statuslar va bildirishnomalar.
6. **Aloqa va statistika:** customer/admin xabarlari, polling, dashboard va do‘kon sozlamalari.
7. **Demo va yakuniy interfeys:** uch tildagi demo ma’lumotlar, lokal rasmlar va barcha sahifalarni API bilan ulash.
8. **Tekshiruv va hujjatlar:** xavfsizlik, integratsiya, parallel buyurtma testlari, OpenAPI va ishga tushirish yo‘riqnomasi.

## 1-etap

- 10 ta app ro‘yxatga olindi; `.env`, dependencies va PostgreSQL Compose tayyorlandi.
- Email registrga bog‘liq bo‘lmagan custom User va birinchi migratsiya yaratildi.
- Customer register/login, alohida admin login, logout, joriy foydalanuvchi va parol almashtirish API qo‘shildi.
- Rol yuborib huquq oshirish taqiqlandi; login/register uchun ham CSRF majburiy.
- Xavfsiz `next`, no-store cache, auth throttling va interaktiv `create_store_admin` qo‘shildi.
- Tekshiruv: Django system check va 6 ta autentifikatsiya testi.

## 2-etap

- Alohida Guest/Customer/Admin layout, mobil navigatsiya va uch til lugati.
- Landing, login/register, til tanlash, xavfsiz page redirect va xato sahifalari.
- Fetch API yordamchisi, CSRF, form loading/error, parolni korsatish va logout.
- Tekshiruv: 3 ta sahifa/rol/til testi va Django check.

## 3-etap

- Category, Product, ProductVariant, ProductImage va DB constraintlari.
- Customer katalog qidiruv, filter, sort, pagination; admin CRUD API.
- Avtomatik default variant, uch tildagi publish validatsiyasi, image upload himoyasi.
- Tekshiruv: 4 ta katalog/permission/variant testi va Django check.

## 4-etap

- Serverdagi savat, favorite, manzillar, profil va sozlamalar API.
- Miqdor/qoldiq tekshiruvi, unique savat/favorite, yagona default manzil.
- Object ownership va protected profile maydonlari; cart mutation lock tartibi.
- Tekshiruv: 4 ta customer data testi.
