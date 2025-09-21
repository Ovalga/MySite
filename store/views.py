from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views import View
from django.http import JsonResponse
import requests
import json
from django.conf import settings
from rest_framework import status
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
import logging
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from urllib.parse import urljoin
from django.contrib.auth import get_user_model

from store.models import Cart

User = get_user_model()


logger = logging.getLogger(__name__)

# Настройки API
API_BASE_URL = settings.API_BASE_URL

def index(request):
    return render(request, 'store/index.html')



def products(request):
    # СОЗДАЕМ ПОЛНЫЙ АБСОЛЮТНЫЙ URL
    full_url = f"{settings.BASE_URL.rstrip('/')}/{API_BASE_URL.lstrip('/')}products/"
    response = requests.get(full_url) #делаем гет запрос к апи
    products = response.json() if response.status_code == status.HTTP_200_OK else [] #если ответ успешный преобразуем джейсон в объекты
    return render(request, 'store/products.html', {'products': products})

#JWT аутентификация
#кастомный сериализатор токенов. Наследует стандартный сериализатор, добавляет в токен доболнительные поля
        
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Добавляем пользовательские поля
        token['username'] = user.username
        token['email'] = user.email
        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

#оставлен без изменений
class CustomTokenRefreshView(TokenRefreshView):
    # Можно добавить кастомную логику при необходимости
    pass

@login_required
def cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = int(data.get('product_id'))
        quantity = data.get('quantity', 1)

        headers = {
            'Authorization': f'Bearer {request.session["access_token"]}',
            'Content-Type': 'application/json'
        }

        # Получаем корзину ТЕКУЩЕГО пользователя
        cart_url = f"{settings.BASE_URL.rstrip('/')}/{settings.API_BASE_URL.lstrip('/')}carts/"
        cart_response = requests.get(cart_url, headers=headers)
        cart_id = cart_response.json()[0]['id'] if cart_response.json() else None

        if cart_response.status_code == 200 and cart_response.json():
            cart_id = cart_response.json()[0]['id']
        else:
            # Создаём новую корзину
            create_cart_url = f"{settings.BASE_URL.rstrip('/')}/{settings.API_BASE_URL.lstrip('/')}carts/"
            create_response = requests.post(create_cart_url, json={}, headers= headers)
            if create_response.status_code == 201:
                cart_id = create_response.json()['id']
            else:
                return JsonResponse({'status': 'error', 'message': 'Не удалось создать корзину'}, status=500)

        # Создаем элемент корзины
        item_url = f"{settings.BASE_URL.rstrip('/')}/{settings.API_BASE_URL.lstrip('/')}cart-items/"
        item_data = {
            'cart': cart_id,
            'product': product_id,
            'quantity': quantity
        }

        response = requests.post(item_url, json=item_data, headers=headers)
        return JsonResponse({
            'status': 'success' if response.status_code == 201 else 'error',
            'message': response.json() if response.content else None
        })

    elif request.method == 'DELETE':
        # Удаление товара из корзины
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        headers = {
            'Authorization': f'Bearer {request.session["access_token"]}',
            'Content-Type': 'application/json'
        }
        
        # response = requests.delete(f"{API_BASE_URL}cart-items/{item_id}/", headers=headers)
        # return JsonResponse({'status': 'success' if response.status_code == 204 else 'error'})
    
        # АБСОЛЮТНЫЙ URL
        item_url = f"{settings.BASE_URL.rstrip('/')}/{API_BASE_URL.lstrip('/')}cart-items/{item_id}/"
        response = requests.delete(item_url, headers=headers)
        return JsonResponse({'status': 'success' if response.status_code == 204 else 'error'})

    else:
        #GET запрос - отображение корзины, ее содержимое
        access_token = request.session.get('access_token', '')
        
        # Если токен отсутствует, перенаправляем на вход
        if not access_token:
            return redirect('login')
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        cart_url = f"{settings.BASE_URL.rstrip('/')}/{API_BASE_URL.lstrip('/')}carts/"
        
        try:
            response = requests.get(cart_url, headers=headers)
            
            # Если получили 401 - токен устарел, пробуем обновить
            if response.status_code == 401:
                refresh_token = request.session.get('refresh_token', '')
                if refresh_token:
                    new_tokens = refresh_jwt_token(refresh_token)
                    if new_tokens:
                        request.session['access_token'] = new_tokens['access']
                        request.session['refresh_token'] = new_tokens['refresh']
                        headers['Authorization'] = f'Bearer {new_tokens["access"]}'
                        response = requests.get(cart_url, headers=headers)
            
            if response.status_code == 200:
                cart_data = response.json()
                if cart_data:
                    cart = cart_data[0]
                    
                    # Вычисляем сумму для каждого элемента
                    for item in cart['items']:
                        try:
                            price = float(item['product_details']['price'])
                            quantity = int(item['quantity'])
                            item['total_price'] = price * quantity
                        except (TypeError, ValueError, KeyError):
                            item['total_price'] = 0
                else:
                    cart = None
            else:
                cart = None
        except Exception as e:
            print(f"Error fetching cart: {e}")
            cart = None
        
        return render(request, 'store/cart.html', {'cart': cart})

# функция для обновления токена
def refresh_jwt_token(refresh_token):
    refresh_url = f"{settings.BASE_URL.rstrip('/')}/{API_BASE_URL.lstrip('/')}auth/refresh/"
    data = {"refresh": refresh_token}
    
    try:
        response = requests.post(refresh_url, json=data)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error refreshing token: {e}")
    return None

@login_required
def profile(request):
    return render(request, 'store/profile.html', {'user': request.user})

class RegisterView(View):
    
    template_name = 'store/register.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')

        if not username or not password:
            return render(request, self.template_name, {'error': 'Имя пользователя и пароль обязательны'})

        data = {
            'username': username,
            'password': password,
            'password2': password,
            'email': email,
        }

        try:
            register_url = urljoin(settings.BASE_URL, f"{settings.API_BASE_URL}auth/register/")
            response = requests.post(register_url, json=data)

            if response.status_code == 201:
                # Аутентификация в Django
                user = authenticate(
                    username=data['username'],
                    password=data['password']
                )
                if user:
                    login(request, user)  # Сохраняем сессию Django

                # Получаем JWT токены
                login_data = {
                    'username': data['username'],
                    'password': data['password']
                }
                login_url = urljoin(settings.BASE_URL, f"{settings.API_BASE_URL}auth/login/")
                login_response = requests.post(login_url, json=login_data)
                if login_response.status_code == status.HTTP_200_OK:
                    tokens = login_response.json()
                    request.session['access_token'] = tokens['access']
                    request.session['refresh_token'] = tokens['refresh']
                    return redirect('index')
                else:
                    error_detail = login_response.json() if login_response.content else {'detail': 'Ошибка входа'}
                    return render(request, self.template_name, {'error': error_detail})

            else:
                try:
                    error_detail = response.json()
                except:
                    error_detail = {'detail': 'Неизвестная ошибка регистрации'}
                return render(request, self.template_name, {'error': error_detail})

        except requests.exceptions.RequestException as e:
            return render(request, self.template_name, {'error': f'Ошибка подключения к серверу: {str(e)}'})
        except Exception as e:
            return render(request, self.template_name, {'error': f'Неизвестная ошибка: {str(e)}'})
    
class LoginView(View):
    template_name = 'store/login.html'
    
    #отображает форму входа
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        data = {
            'username': request.POST.get('username'),
            'password': request.POST.get('password')
        }
        

        # ИСПРАВЛЕННЫЙ URL - АБСОЛЮТНЫЙ
        login_url = f"{settings.BASE_URL.rstrip('/')}/{API_BASE_URL.lstrip('/')}auth/login/"
        
        
        response = requests.post(login_url, json=data)
        if response.status_code == status.HTTP_200_OK:
            tokens = response.json()
            request.session['access_token'] = tokens['access']
            request.session['refresh_token'] = tokens['refresh']
                
            # Аутентификация в Django
            user = authenticate(
                username=data['username'],
                password=data['password']
            )
            if user:
                login(request, user)
            return redirect('index')
            
        error = response.json().get('detail', 'Неверные учетные данные')
        return render(request, self.template_name, {'error': error})
 
@csrf_exempt
@require_POST
def logout_view(request):
    # Выход из API
    if request.session.get('access_token'):
        try:
            headers = {
                'Authorization': f'Bearer {request.session["access_token"]}',
                'Content-Type': 'application/json'
            }
            data = {'refresh': request.session.get('refresh_token', '')}
            logout_url = f"{settings.BASE_URL.rstrip('/')}/api/auth/logout/"
            response = requests.post(logout_url, json=data, headers=headers)
            
            # Логируем результат выхода из API
            print(f"API logout status: {response.status_code}")
        except Exception as e:
            print(f"API logout error: {str(e)}")
    
    # Выход из Django
    logout(request)
    
    # Очистка сессии
    request.session.flush()
    
    # Выход из Django
    if request.user.is_authenticated:
        Cart.objects.filter(user=request.user).delete()
    # Добавляем сообщение об успешном выходе
    messages.success(request, "Вы успешно вышли из системы")
    
    return redirect('index')

@login_required
def profile(request):
    # Здесь будет логика получения данных профиля
    return render(request, 'store/profile.html', {'user': request.user})