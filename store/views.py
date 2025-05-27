from django.shortcuts import render
from rest_framework import viewsets, permissions, serializers
from .models import Product, Cart, CartItem
from .serializers import ProductSerializer, CartSerializer, CartItemSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

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