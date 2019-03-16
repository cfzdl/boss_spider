from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from utils.mixin import LoginRequiredMixin

from django_redis import get_redis_connection
from goods.models import GoodsSKU
# Create your views here.

class CartAddView(View):
    '''购物车记录添加'''
    def post(self, request):
        user = request.user
        # 判断用户是否登录
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})
        #接受数据
        sku_id = request.POST.get()
        count = request.POST.get()

        # 校验数据

        if not all([sku_id, count]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})

        #校验添加的商品数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res':2, 'errmsg':'商品数量出错'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)

        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res':3, 'errmsg':'商品不存在'})

        # 业务处理
        #获取用户对应的购物记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        # 尝试获得sku_id 的值
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            count += int(cart_count)

        if count > sku.stock:
            return JsonResponse({'res':4, 'errmsg':'库存商品不足'})
         # 设置sku_id 的值
        conn.hset(cart_key, sku_id, count)

        total_count = conn.hlen(cart_key)

        return JsonResponse({'res':5, 'total_count':total_count, 'message':'添加成功'})


class CartInfoView(LoginRequiredMixin ,View):
    def get(self, request):
        user = request.user

        conn = get_redis_connection('default')

        cart_key = 'cart_%d'%user.id

        cart_dict = conn.hgetall(cart_key)

        skus = []

        total_count = 0
        total_price = 0

        for sku_id, count in cart_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)
            # 获取商品的小计
            amount = sku.price * int(count)
            # 动态增加属性
            sku.amount = amount
            sku.count = count

            skus.append(sku)
            total_count += int(count)
            total_price += amount

        context = {
            'total_count':total_count,
            'total_price':total_price,
            'skus':skus
        }

        return render(request, 'cart.html', context)



class CartUpdateView(View):
    '''购物车记录更新'''

    def post(self, request):

        user = request.user
        # 判断用户是否登录
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 接受数据
        sku_id = request.POST.get()
        count = request.POST.get()

        # 校验数据

        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验添加的商品数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数量出错'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)

        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 业务处理
        # 获取用户对应的购物记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        if count > sku.stock:
            return JsonResponse({'res':4, 'errmsg':'库存不足'})

        conn.hset(cart_key, sku_id, count)

        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({'res':5,'total_count':total_count,    'errmsg': '更新成功'})


class CartDeleteView(View):

    def post(self, request):
        user = request.user
        # 判断用户是否登录
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 接受数据
        sku_id = request.POST.get()
        count = request.POST.get()

        # 校验数据

        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验商品是否存在
        try:
                sku = GoodsSKU.objects.get(id=sku_id)

        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res':2 , 'errmsg': '商品不存在'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        # 刪除购物记录

        conn.hdel(cart_key, sku_id)


        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)


        return JsonResponse({'res':3,'total_count':total_count,  'message':'删除成功'})
