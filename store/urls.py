from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api_views import (  # Выносим API-представления в отдельный файл
    ProductViewSet, 
    CartViewSet, 
    CartItemViewSet,
    RegisterAPIView,
    ChangePasswordView,
    LogoutAPIView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# from .views import (
#     index, 
#     products, 
#     cart, 
#     profile,
#     RegisterView,
#     LoginView,
#     logout_view,
#     CustomTokenObtainPairView  # ДОБАВЛЕНО
# )

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'carts', CartViewSet, basename='cart')
router.register(r'cart-items', CartItemViewSet, basename='cartitem')

urlpatterns = [
    # API Endpoints
    path('api/', include(router.urls)),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='api-login'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='api-refresh'),
    path('api/auth/register/', RegisterAPIView.as_view(), name='api-register'),
    path('api/auth/change-password/', ChangePasswordView.as_view(), name='api-change-password'),
    path('api/auth/logout/', LogoutAPIView.as_view(), name='api-logout'),
    # Frontend Views
    path('', views.index, name='index'),
    path('products/', views.products, name='products'),
    path('cart/', views.cart, name='cart'),
    path('profile/', views.profile, name='profile'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
]

