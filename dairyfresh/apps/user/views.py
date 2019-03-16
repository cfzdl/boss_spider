from django.shortcuts import render,redirect
from django.core.urlresolvers import reverse
from django_redis import get_redis_connection
from django.views.generic import View
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from celery_tasks.tasks import send_register_active_email
from django.core.mail import send_mail
from django.core.paginator import Paginator
from utils.mixin import LoginRequiredMixin
import re
from user.models import User, Address
from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods


class RegisterView(View):
    '''注册'''
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 获取数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        apassword = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 校验数据
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if password != apassword:
            return render(request, 'register.html', {'errmsg': '两次密码不一致'})

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user:
            # 用户名已存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})


        # 业务处理
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        # 加密用户的身份信息，生成激活token
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)  # bytes
        token = token.decode()

        send_register_active_email.delay(email, username, token)


        return redirect(reverse('goods:index'))


class ActiveView(View):
    '''用户激活'''
    def get(self, request, token):
        '''进行用户激活'''
        # 进行解密，获取要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取待激活用户的id
            user_id = info['confirm']

            # 根据id获取用户信息
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            # 跳转到登录页面
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            # 激活链接已过期
            return HttpResponse('激活链接已过期')


class LoginView(View):
    '''登录'''
    def get(self, request):
        '''显示登录页面'''
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''

        return render(request, 'login.html',{'username':username,'checked':checked})

    def post(self, request):
        '''登陆校验'''
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        remember = request.POST.get('remember')

        if not all([username, password]):
            return render(request, 'login.html', {'errmsg':'数据不完整'})

        user = authenticate(username=username, password=password)
        if user is not None:
            # 用户名密码正确
            if user.is_active:
                # 用户已激活
                # 记录用户的登录状态
                login(request, user)
                next_url = request.GET.get('next', reverse('goods:index'))
                response = redirect(next_url)

                #判断是否需要记住用户名
                if remember == 'on':
                    response.set_cookie('username', username, max_age=24*3600)
                else:
                    response.delete_cookie('username')

                return response

            else:
                return render(request, 'login.html', {'errmsg': '用户未激活'})

        else:
            return render(request, 'login.html', {'errmsg': '用户名或密码错'})


class LogoutView(View):
    '''退出登录'''
    def get(self, request):
        '''退出登录'''

        logout(request)

        return redirect(reverse('goods:index'))


class UserInfoView(LoginRequiredMixin, View):
    def get(self, request):

        user = request.user
        address = Address.objects.get_default_address(user)

        con = get_redis_connection('default')  # 连接redis数据库

        history_key = 'history_%d'%user.id  # 获得用户对应的KEY

        sku_ids = con.lrange(history_key, 0, 4)  # 获取用户的浏览记录

        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)  # 获得用户浏览记录对应商品的查询集

        goods_li = []

        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        context = {'page': 'user',
                   'address': address,
                   'goods_li':goods_li,
                   }


        return render(request, 'user_center_info.html', context)



class UserOrderView(LoginRequiredMixin, View):
    def get(self, request, page):
        """显示"""
        
        user = request.user
        orders = OrderGoods.objecets.filter(user =user)
        
        # 遍历获取订单商品信息
        for order in orders:
            # 查询订单信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)
            for  order_sku in order_skus:
                # 计算小计
                amount = order_sku.count*order_sku.price

                # 动态添加属性
                order_sku.amount = amount
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(order, 1)

        try:
            page = int(page)

        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # huo qu page ye de shu ju

        order_page = paginator.page(page)

        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages+1)

        elif page <=3:
            pages = range(1, 6)

        elif num_pages-page <= 2:
            pages = range(num_pages-4, num_pages+1)

        else:
            pages = range(num_pages-2, num_pages+3)

        context = {
            'order_page':order_page,
            'pages':pages,
            'page':'order',
        }


        return render(request, 'user_center_order.html',context)


class UserAddressView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user

        address = Address.objects.get_default_address(user)

        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})

    def post(self, request):
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        if  not all([receiver, addr, zip_code, phone]):
            return render(request, 'user_center_site.html', {'errmsg':'数据不完整'})

        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg':'手机格式不正确'})

        user = request.user

        address = Address.objects.get_default_address(user)  # 获取网页中是否有地址

        # 如果有地址就是添加的就不是默认地址，反之则是
        if address:
            is_default = False
        else:
            is_default = True

        # 添加地址
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)

        # 返回应答,刷新地址页面
        return redirect(reverse('user:address'))  # get请求方式