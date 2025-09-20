from rest_framework import serializers
from .models import Product, Cart, CartItem
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True) #говорит о том, что пароль не возвращается в API
# преобразует данные регистрации в объект User
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email')

#переопределяем метод криэйт, используем криэйт юзер обеспечивая хеширование паролей и правильно обрабатывает пустые имейлы
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
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
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Количество не может быть меньше 1")
        return value

#список элементов корзины через CartItemSerializer
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price']

    def get_total_price(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())