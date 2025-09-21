from rest_framework import viewsets, permissions, status, serializers
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from .models import Product, Cart, CartItem
from .serializers import ProductSerializer, CartSerializer, CartItemSerializer, UserRegisterSerializer, ChangePasswordSerializer
from django.contrib.auth import get_user_model # получает модель пользователя (стандарт или кастомную)
from django.db import transaction
from django.db.models import F

User = get_user_model()

# CRUD операция для товаров
# ModelViewSet автоматически создает все CRUD операция
class ProductViewSet(viewsets.ModelViewSet):
    # какие данные использовать (все товары)
    queryset = Product.objects.all()
    # как преобразовывать данные в JSON и обратно
    serializer_class = ProductSerializer
    # доступ разрешен всем, даже неавторизованным пользователям
    permission_classes = [permissions.AllowAny]

# CRUD операция для корзин
class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    # только авторизованные пользователей
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).prefetch_related('items')

    # Добавьте вычисление общей суммы при создании
    def perform_create(self, serializer):
        cart = serializer.save(user=self.request.user)
        cart.total_price = sum(item.product.price * item.quantity for item in cart.items.all())
        cart.save()

# CRUD операция для элементов корзины

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    # работает только с элементами корзины текущего пользователя
    def get_queryset(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user) #создает корзину, если ее нет
        return CartItem.objects.filter(cart=cart)
   

    # создание элемента корзины
   

    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        
        # Блокируем строку продукта для обновления
        with transaction.atomic():
            product = Product.objects.select_for_update().get(id=product.id)
            
            if quantity > product.stock:
                raise serializers.ValidationError(
                    {"detail": "Недостаточно товара на складе"}
                )
            
            # Используем F-выражение для атомарного обновления
            product.stock = F('stock') - quantity
            product.save(update_fields=['stock'])
            product.refresh_from_db()  # если нужно получить актуальное значение
            
            serializer.save(cart=cart)

    #  удаление элемента корзины
    # возвращает товар на склад, при удалении из корзины
    def perform_destroy(self, instance):
        with transaction.atomic():
            product = instance.product
            product.stock = F('stock') + instance.quantity
            product.save(update_fields=['stock'])
            super().perform_destroy(instance)
    # обновление элемента корзины
    # коррект. кол-во тов. на складе при измен. кол-ва в корзине
    # вычисл разницу дельта между старым и новым кол-ом
    def perform_update(self, serializer):
        old_quantity = serializer.instance.quantity
        new_quantity = serializer.validated_data.get('quantity', old_quantity)
        
        delta = new_quantity - old_quantity
        if delta == 0:
            return serializer.save()  # ничего не меняем

        product = serializer.instance.product

        with transaction.atomic():
            product = Product.objects.select_for_update().get(id=product.id)
            
            # Проверка, если увеличиваем количество
            if delta > 0 and delta > product.stock:
                raise serializers.ValidationError(
                    {"detail": "Недостаточно товара на складе"}
                )
            
            product.stock = F('stock') - delta
            product.save(update_fields=['stock'])
            product.refresh_from_db()

            serializer.save()

# API для регистрации пользователя
class RegisterAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny]
    # permissions.AllowAny разрешает регистрацию без авторизации

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserRegisterSerializer(user).data,
            "message": "User created successfully"
        }, status=status.HTTP_201_CREATED)

# API для смены пароля, только для авториз пользователей
class ChangePasswordView(generics.UpdateAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    # возвращает текущего пользователя
    def get_object(self):
        return self.request.user

    # спец-ный сериализатор для смены пароля
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response({"message": "Password changed successfully"})
    
# class LogoutAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         try:
#             refresh_token = request.data["refresh"]
#             token = RefreshToken(refresh_token)
#             token.blacklist()
#             return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# API для выхода из системы
class LogoutAPIView(APIView):
    permission_classes = [permissions.AllowAny]  # Разрешаем доступ всем

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