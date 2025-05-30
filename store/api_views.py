from rest_framework import viewsets, permissions, status, serializers
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from .models import Product, Cart, CartItem
from .serializers import ProductSerializer, CartSerializer, CartItemSerializer, UserRegisterSerializer, ChangePasswordSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).prefetch_related('items')

    # Добавьте вычисление общей суммы при создании
    def perform_create(self, serializer):
        cart = serializer.save(user=self.request.user)
        cart.total_price = sum(item.product.price * item.quantity for item in cart.items.all())
        cart.save()

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return CartItem.objects.filter(cart=cart)

    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        serializer.save(cart=cart)
        
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        if quantity > product.stock:
            raise serializers.ValidationError(
                {"detail": "Недостаточно товара на складе"}
            )
        product.stock -= quantity
        product.save()

    def perform_destroy(self, instance):
        instance.product.stock += instance.quantity
        instance.product.save()
        super().perform_destroy(instance)

    def perform_update(self, serializer):
        old_quantity = serializer.instance.quantity
        new_quantity = serializer.validated_data.get('quantity', old_quantity)
        
        delta = new_quantity - old_quantity
        product = serializer.instance.product
        product.stock -= delta
        product.save()
        
        serializer.save()

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