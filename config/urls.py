from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [path('api/v1/', include('apps.cart.urls')), path('api/v1/', include('apps.accounts.customer_urls')), path('api/v1/', include('apps.catalog.urls')), path('api/v1/auth/', include('apps.accounts.urls')), path('', include('apps.storefront.urls'))]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
handler403 = 'apps.storefront.views.error403'
handler404 = 'apps.storefront.views.error404'
handler500 = 'apps.storefront.views.error500'
