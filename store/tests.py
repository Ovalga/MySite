from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from .models import Product, Cart, CartItem

User = get_user_model()

class ProductAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.token = Token.objects.create(user=self.user).key
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token}')
        self.product = Product.objects.create(
            name='Тестовая футболка',
            price=500.00,
            description='Тестовое описание',
            stock=10
        )

    def test_get_products_list(self):
        url = reverse('product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Тестовая футболка')

    def test_create_product(self):
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

class CartItemTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass1')
        self.user2 = User.objects.create_user(username='user2', password='pass2')
        self.product = Product.objects.create(
            name="Test Product", 
            price=100.00, 
            stock=10  # Увеличим начальный stock для тестов
        )
        
        # Создаем корзины для пользователей
        self.cart1 = Cart.objects.create(user=self.user1)
        self.cart2 = Cart.objects.create(user=self.user2)
        
        # Токены и клиенты
        self.token1 = Token.objects.create(user=self.user1).key
        self.token2 = Token.objects.create(user=self.user2).key
        self.client1 = APIClient()
        self.client1.credentials(HTTP_AUTHORIZATION=f'Token {self.token1}')
        self.client2 = APIClient()
        self.client2.credentials(HTTP_AUTHORIZATION=f'Token {self.token2}')

    def test_add_item_to_cart(self):
        """Тест добавления товара в корзину"""
        initial_stock = self.product.stock
        url = reverse('cartitem-list')
        data = {'product': self.product.id, 'quantity': 2}
        
        response = self.client1.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Проверяем обновление остатка
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock - 2)
        
        # Проверяем связь с корзиной
        item = CartItem.objects.first()
        self.assertEqual(item.cart.user, self.user1)

    def test_update_cart_item(self):
        # """Тест обновления количества товара"""
        initial_stock = self.product.stock  # Исходный stock = 10
        
        # Создаем элемент корзины с quantity=2
        item = CartItem.objects.create(
            cart=self.cart1,
            product=self.product,
            quantity=2
        )
        self.product.stock -= 2
        self.product.save()

        # Обновляем до quantity=3 (delta = +1)
        url = reverse('cartitem-detail', args=[item.id])
        data = {'quantity': 3}
        
        response = self.client1.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем обновление остатка: 10 - 2 - 1 = 7
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock - 3)
        def test_delete_cart_item(self):
            """Тест удаления товара"""
            initial_stock = self.product.stock
            item = CartItem.objects.create(
                cart=self.cart1, 
                product=self.product, 
                quantity=3
            )
            self.product.stock -= 3
            self.product.save()

            url = reverse('cartitem-detail', args=[item.id])
            response = self.client1.delete(url)
            
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(CartItem.objects.count(), 0)
            
            # Проверяем восстановление остатка
            self.product.refresh_from_db()
            self.assertEqual(self.product.stock, initial_stock)

    def test_access_other_users_cart(self):
        """Тест доступа к чужой корзине"""
        item = CartItem.objects.create(
            cart=self.cart1, 
            product=self.product, 
            quantity=1
        )
        
        url = reverse('cartitem-detail', args=[item.id])
        response = self.client2.patch(url, {'quantity': 5}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_cart_items(self):
        """Тест получения списка товаров в корзине"""
        CartItem.objects.create(
            cart=self.cart1, 
            product=self.product, 
            quantity=2
        )
        
        url = reverse('cartitem-list')
        response = self.client1.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['quantity'], 2)
        self.assertEqual(response.data[0]['product'], self.product.id)

    def test_add_item_exceeding_stock(self):
        """Попытка добавить товар с количеством, превышающим stock"""
        initial_stock = self.product.stock  # 10
        url = reverse('cartitem-list')
        data = {'product': self.product.id, 'quantity': 15}  # Превышение
        
        response = self.client1.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Проверяем что stock не изменился
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock)

    def test_negative_quantity(self):
        """Проверка отрицательного значения quantity"""
        url = reverse('cartitem-list')
        data = {'product': self.product.id, 'quantity': -2}
        
        response = self.client1.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_nonexistent_item(self):
        """Попытка обновить несуществующий элемент корзины"""
        fake_item_id = 9999
        url = reverse('cartitem-detail', args=[fake_item_id])
        data = {'quantity': 5}
        
        response = self.client1.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_item(self):
        """Попытка удалить несуществующий элемент корзины"""
        fake_item_id = 9999
        url = reverse('cartitem-detail', args=[fake_item_id])
        
        response = self.client1.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

