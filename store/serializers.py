from rest_framework import serializers
from .models import Product, Cart, CartItem
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]
    )

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'description', 'stock']
        
class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Количество не может быть меньше 1")
        return value

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'created_at', 'items']