from rest_framework.routers import DefaultRouter
from . import views
router = DefaultRouter()
router.register('categories', views.CategoryViewSet, basename='category')
router.register('products', views.ProductViewSet, basename='product')
router.register('admin/categories', views.AdminCategoryViewSet, basename='admin-category')
router.register('admin/products', views.AdminProductViewSet, basename='admin-product')
router.register('admin/variants', views.AdminVariantViewSet, basename='admin-variant')
router.register('admin/images', views.AdminImageViewSet, basename='admin-image')
urlpatterns = router.urls
