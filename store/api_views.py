from rest_framework import viewsets, permissions, status, serializers
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from .models import Product, Cart, CartItem
from .serializers import ProductSerializer, CartSerializer, CartItemSerializer, UserRegisterSerializer, ChangePasswordSerializer
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F

User = get_user_model()

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

class CartViewSet(viewsets.ReadOnlyModelViewSet):  # Изменено на ReadOnly
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user, is_active=True)

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Находим или создаем корзину для пользователя
        cart, created = Cart.objects.get_or_create(
            user=self.request.user, 
            is_active=True
        )
        return CartItem.objects.filter(cart=cart)

    def perform_create(self, serializer):
        # Простая логика - находим или создаем корзину
        cart, created = Cart.objects.get_or_create(
            user=self.request.user, 
            is_active=True
        )
        
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        
        # Проверка наличия товара
        if quantity > product.stock:
            raise serializers.ValidationError(
                {"detail": f"Недостаточно товара на складе. Доступно: {product.stock}"}
            )
        
        # Проверяем, есть ли уже такой товар в корзине
        existing_item = CartItem.objects.filter(cart=cart, product=product).first()
        
        with transaction.atomic():
            if existing_item:
                # Обновляем количество
                new_quantity = existing_item.quantity + quantity
                if new_quantity > product.stock:
                    raise serializers.ValidationError(
                        {"detail": "Недостаточно товара на складе"}
                    )
                existing_item.quantity = new_quantity
                existing_item.save()
            else:
                # Создаем новый элемент
                serializer.save(cart=cart)
            
            # Обновляем остаток на складе
            product.stock -= quantity
            product.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        old_quantity = instance.quantity
        new_quantity = serializer.validated_data.get('quantity', old_quantity)
        
        if new_quantity == old_quantity:
            serializer.save()
            return

        product = instance.product
        delta = new_quantity - old_quantity

        with transaction.atomic():
            if delta > product.stock:
                raise serializers.ValidationError(
                    {"detail": "Недостаточно товара на складе"}
                )
            
            product.stock -= delta
            product.save()
            serializer.save()

    def perform_destroy(self, instance):
        with transaction.atomic():
            # Возвращаем товар на склад
            product = instance.product
            product.stock += instance.quantity
            product.save()
            instance.delete()

# Остальные классы (RegisterAPIView, ChangePasswordView, LogoutAPIView) оставляем без изменений
class RegisterAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserRegisterSerializer(user).data,
            "message": "User created successfully"
        }, status=status.HTTP_201_CREATED)

class ChangePasswordView(generics.UpdateAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response({"message": "Password changed successfully"})

class LogoutAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)