from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CartViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'carts', CartViewSet, basename='cart')

urlpatterns = [
    path('api/', include(router.urls)),
]