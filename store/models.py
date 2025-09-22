from django.db import models 
from django.contrib.auth.models import AbstractUser, Group, Permission

# Зачем это нужно?
# При создании кастомной модели пользователя в Django требуется явно переопределить связи groups и user_permissions,
#  чтобы избежать конфликтов имен.

# кастомная модель пользователя наследуется от AU, чтобы использовать стандартные поля
class User(AbstractUser):
    phone = models.CharField(max_length=15, blank=True)
    # переопределение для поля groups с моделью Group
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to...',
        related_name="store_user_groups",  # Уникальное имя, для доступа пользователя из группы
        related_query_name="user",
    )
    # переопределение для поля user_permissions для прав доступа с моделью Permission
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user...',
        related_name="store_user_permissions",  # Уникальное имя
        related_query_name="user", # имя для запросов
    )

# модель товара
class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    stock = models.PositiveIntegerField(default=0)
    # stock кол-во на складе, положит целое число, по умолч 0

    # возвращает название товара для удобного отображения в админке и shell
    def __str__(self):
        return self.name
    
    
# модель корзины
class Cart(models.Model):
    # связь с пользователем, 1 польз - мн корзин, при удалении пользователя корз удал CASCADE
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # дата создания корзины, автомат устанавл при создании
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # возвращает строку вида "Cart #1 - username"
    def __str__(self):
        return f"Cart #{self.id} - {self.user.username}"
    
    def get_total_price(self):
        return sum(item.total_price() for item in self.items.all())

# модель элемента корзины
class CartItem(models.Model):
    # связь с корзиной
    # related_name='items' позволяет обращаться к элементам корзины через cart.items
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    # связь с товаром
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # кол-во товара в корзине, положит число, по умолч 1
    quantity = models.PositiveIntegerField(default=1)

    # метод вычисл общ стоимости позиции (цена на кол-во)
    def total_price(self):
        return self.product.price * self.quantity
