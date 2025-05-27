from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from .models import Product, Cart


User = get_user_model()

class ProductAPITestCase(TestCase):
    def setUp(self):
        # Создаем тестового пользователя и клиент API
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.token = self.get_user_token()
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token}')

        # Создаем тестовый товар
        self.product = Product.objects.create(
            name='Тестовая футболка',
            price=500.00,
            description='Тестовое описание',
            stock=10
        )

    def get_user_token(self):
        # Получаем токен для аутентификации
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=self.user)
        return token.key

    def test_get_products_list(self):
        # Проверяем GET-запрос к /api/products/
        url = reverse('product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Тестовая футболка')

    def test_create_product(self):
        # Проверяем POST-запрос к /api/products/
        url = reverse('product-list')
        data = {
            'name': 'Новый товар',
            'price': 1000.00,
            'description': 'Новое описание',
            'stock': 5
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)

class CartAPITestCase(TestCase):
    def setUp(self):
        # Аналогичная настройка для тестов корзины
        self.user = User.objects.create_user(username='testuser2', password='testpass')
        self.token = Token.objects.create(user=self.user).key
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token}')

    def test_get_user_cart(self):
        # Проверяем получение корзины пользователя
        url = reverse('cart-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # Корзина пуста изначально