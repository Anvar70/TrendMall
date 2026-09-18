from django.urls import path
from .views import page, language, translations, CUSTOMER_PAGES, ADMIN_PAGES

urlpatterns = [path('', page), path('login/', page, {'name': 'login'}),
    path('register/', page, {'name': 'register'}), path('language/', language),
    path('api/v1/translations/', translations),
    path('admin/login/', page, {'name': 'admin_login'}),
    path('shop/products/<slug:slug>/', page, {'section': 'customer', 'name': 'product_detail'}),
    path('shop/orders/<str:public_number>/', page, {'section': 'customer', 'name': 'order_detail'}),
    path('admin/orders/<str:public_number>/', page, {'section': 'admin_panel', 'name': 'order_detail'}),
]
for name in CUSTOMER_PAGES + ['checkout', 'order_success']:
    urlpatterns.append(path('shop/' + ('' if name == 'home' else name + '/'), page, {'section': 'customer', 'name': name}))
for name in ADMIN_PAGES:
    urlpatterns.append(path('admin/' + name + '/', page, {'section': 'admin_panel', 'name': name}))
