from django.shortcuts import render
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, serializers
from .models import Product, Cart, CartItem
from .serializers import ProductSerializer, CartSerializer, CartItemSerializer
from rest_framework import generics
from rest_framework.response import Response
from django.contrib.auth.models import User
from .serializers import UserRegisterSerializer, ChangePasswordSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView

User = get_user_model()

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Оптимизируем запрос, загружая связанные элементы
        return Cart.objects.filter(user=self.request.user).prefetch_related('items')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Получаем корзину текущего пользователя
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return CartItem.objects.filter(cart=cart)

    def perform_create(self, serializer):
        # Автоматически связываем с корзиной пользователя
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        serializer.save(cart=cart)
        
        # Обновляем остатки
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        if quantity > product.stock:
            raise serializers.ValidationError(
                {"detail": "Недостаточно товара на складе"}
            )
        product.stock -= quantity
        product.save()

    def perform_destroy(self, instance):
        # Восстанавливаем остатки при удалении
        instance.product.stock += instance.quantity
        instance.product.save()
        super().perform_destroy(instance)

    def perform_update(self, serializer):
        old_quantity = serializer.instance.quantity
        new_quantity = serializer.validated_data.get('quantity', old_quantity)
        
        # Корректный расчет разницы
        delta = new_quantity - old_quantity
        product = serializer.instance.product
        product.stock -= delta
        product.save()
        
        serializer.save()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny]  # Разрешить доступ всем

class ChangePasswordView(generics.UpdateAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response({"message": "Password changed successfully"})
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()  # Добавляем refresh-токен в черный список
        return Response({"message": "Успешный выход!"})