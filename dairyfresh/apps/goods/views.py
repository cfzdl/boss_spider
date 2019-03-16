from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django.core.cache import cache
from django.core.paginator import Paginator
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner,GoodsSKU
from order.models import OrderGoods
from django_redis import get_redis_connection


class IndexView(View):
    '''首页'''
    def get(self, request):

        #get cache
        context = cache.get('index_page_data')

        if context is None:


            # 获取商品种类信息
            types = GoodsType.objects.all()

            # 获取商品轮播信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            #获取首页促销活动信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            #获取首页分类商品展示信息
            for goods_type in types:
                # 获取goods_type种类首页分类商品的图片展示信息
                image_banners = IndexTypeGoodsBanner.objects.filter(type=goods_type, display_type=1).order_by('index')
                # 获取goods_type种类首页分类商品的文字展示信息
                title_banners = IndexTypeGoodsBanner.objects.filter(type=goods_type, display_type=0).order_by('index')

                # 给goods_type种类动态添加属性
                goods_type.image_banners = image_banners
                goods_type.title_banners = title_banners


            context = {'types':types,
                       'goods_banners':goods_banners,
                       'promotion_banners':promotion_banners,
                       }

            # set cache

            cache.set('index_page_data', context)

        #获取用户购物车中商品数目
        user = request.user
        cart_count=0
        if user.is_authenticated():
            conn =get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)




        context.update(cart_count=cart_count)


        return render(request, 'index.html', context)



class DetailView(View):

    def get(self, request, goods_id):
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))

        types = GoodsType.objects.all()

        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('create_time')

        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        user = request.user
        cart_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

            conn = get_redis_connection('default')
            history_key = 'history_%d' % user.id

            conn.lrem(history_key, 0, goods_id)

            conn.lpush(history_key, 0, goods_id)

            conn.ltrim(history_key, 0, 4)

        context = {
            'sku':sku,
            'types':types,
            'sku_orders':sku_orders,
            'new_skus':new_skus,
            'same_spu_skus': same_spu_skus,
            'cart_count':cart_count
        }



        return render(request, 'detail.html', context)



class ListView(View):
    def get(self, request, type_id, page):

        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods:index'))


        types = GoodsType.objects.all()

        sort = request.GET.get('sort')
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

         # fen ye chu li
        paginator = Paginator(skus, 1)

        try:
            page = int(page)

        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # huo qu page ye de shu ju

        sku_page = paginator.page(page)

        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages+1)

        elif page <=3:
            pages = range(1, 6)

        elif num_pages-page <= 2:
            pages = range(num_pages-4, num_pages+1)

        else:
            pages = range(num_pages-2, num_pages+3)

        new_skus = GoodsSKU.objects.filter(type=type).order_by('create_time')

        user = request.user
        cart_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        context = {
            'type': type,
            'types': types,
            'sku_page': sku_page,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'pages':pages,
            'sort':sort
        }

        return render(request, 'list.html', context)


