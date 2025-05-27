from django.core.management.base import BaseCommand
from store.models import User, Product, Cart, CartItem

class Command(BaseCommand):
    help = 'Fill database with test data'

    def handle(self, *args, **options):
        # Создаем пользователя
        user = User.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='12345'
        )

        # Создаем товары
        products = [
            Product(name='Футболка', price=500, description='Хлопок', stock=10),
            Product(name='Джинсы', price=2000, description='Синие', stock=5),
        ]
        Product.objects.bulk_create(products)

        # Создаем корзину
        cart = Cart.objects.create(user=user)

        # Добавляем товары в корзину
        CartItem.objects.create(cart=cart, product=products[0], quantity=2)
        CartItem.objects.create(cart=cart, product=products[1], quantity=1)

        self.stdout.write(self.style.SUCCESS('Тестовые данные созданы!'))