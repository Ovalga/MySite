from rest_framework import serializers
from .models import Product, Cart, CartItem
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model


# serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()




class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Пароли не совпадают")
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user




#наследует от сериалайзер
#валидирует данные при смене пароля
#проверяет начличие старого пароля, потом проверяет пароль с помощью встроенного валидатора джанго
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]
    )

#преобразует объекты в джейсон и обратно, определяет какие поля доступны в апи

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'description', 'stock']
        
#работает с элементами корзины
class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=True) #для записи, обновления
    product_details = ProductSerializer(source='product', read_only=True) #для чтения, возвращает полные данные товара

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_details', 'quantity']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Количество не может быть меньше 1")
        return value

#список элементов корзины через CartItemSerializer
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField() #поле, значение которого считается через get_total_price

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'is_active', 'created_at']

    def get_total_price(self, obj):
        return obj.get_total_price()
        # return sum(item.product.price * item.quantity for item in obj.items.all())