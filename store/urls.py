from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ProductViewSet, CartViewSet, CartItemViewSet, RegisterView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)
from .views import LogoutView


router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'carts', CartViewSet, basename='cart')
router.register(r'cart-items', CartItemViewSet, basename='cartitem')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/register/', RegisterView.as_view(), name='register'),
]