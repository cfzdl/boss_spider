from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.db import transaction
from django.conf import settings
from django.views.generic import View

from user.models import Address
from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods

from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
from datetime import datetime
from alipay import AliPay
import os
# Create your views here.


class OrderPlaceView(LoginRequiredMixin, View):

    def post(self, request):

        user = request.user
        # 获取参数
        sku_ids = request.POST.getlist('sku_ids')

        #校验数据
        if not all(sku_ids):
            return redirect(reverse('cart:show '))

        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        skus = []

        #设置商品的总件数和总价
        total_count = 0
        total_price = 0

        # 根据遍历sku_ids获得用户要购买的商品信息
        for sku_id in sku_ids:
            # 根据sku_id获得商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            #获得用户需要购买的商品数量
            count = conn.hget(cart_key, sku_id)
            #计算商品的小计
            amount = sku.price * int(count)

            sku.count = count
            sku.amount = amount

            skus.append(sku)

            total_count += int(count)
            total_price +=amount

        #运费 实际开发中，属于一个系统
        transit_price = 10

        #实付款
        total_pay = total_price + transit_price

        #获取用户的收件地址
        addrs = Address.objects.filter(user=user)


        #组织上下文
        sku_ids = ','.join(sku_ids)
        context = {
            'skus':skus,
            'total_count':total_count,
            'total_price': total_price,
            'transit_price': transit_price,
            'total_pay': total_pay,
            'addrs':addrs,
            'sku_ids':sku_ids,
        }

        return render(request, 'place_order.html', context)


class OrderCommitView(View):
    '''订单创建 '''
    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})

        # 接受参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        #校验数据
        if not all([addr_id, sku_ids, pay_method]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})

        # 验证支付方式
        if pay_method not in OrderInfo.pay_method.PAY_METHODS.keys:
            return JsonResponse({'res':2, 'errmsg':'非法支付手段'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res':3, 'errmsg':'地址非法'})

        # 组织参数
        #订单ID
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str( user.id)

        # 运费
        transit_price = 10

        #总数目和总jine
        total_count = 0
        total_price = 0

        # 设置保存点
        save_id = transaction.savepoint()
        try:
            # todo: 向df_order_info 表中添加一条记录
            order = OrderInfo.objects.create(order_id = order_id,
                                             user = user,
                                             addr = addr,
                                             pay_method = pay_method,
                                             total_count = total_count,
                                             total_price = total_price,
                                             transit_price = transit_price)

            # todo: 用户订单中有几个商品， 需要向df_order_goods表中加入几条记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id

            sku_ids = sku_ids.split(',')

            for sku_id in sku_ids:
                for i in 3:
                # 获取商品信息
                    try:
                        sku = GoodsSKU.objects.select_for_updata().get(id=sku_id)
                    except:
                        transaction.savepoint_rollback(save_id)  #  悲观锁，两个线程，谁拿到锁谁开使工作
                        return JsonResponse({'res':4, 'errmsg':'商品不存在'})

                    # 从redis中获取用户所购买商品的数量
                    count = conn.hget(cart_key, sku_id)

                    #  todo: 判断商品库存
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res':6, 'errmsg':'库存商品不足'})

                    """
                    #  乐观锁  在更新之前先检判断库存是否充足
                   使用乐观锁  需要修改MYSQL默认的 隔离级别  在日志文件中修改为READ.COMMITTED
                   
                   在冲突比较少的时候时使用乐观锁，冲突比较多的使用悲观锁，乐观锁重复代价比较大时，也是用悲观锁
                   
                    res = =GoodsSKU.objects.filter(id=sku_id, stock = orgin_stock).update(stock = new_stock)
                    if res == 0:
                        if i == 2:
                            transactions.savepoint_rollback(save_id)
                            return JsonResponse({'res':7, 'errmsg':'下单失败'})
                        continue
                   
                    """

                    # todo: 向df_order_goods表中添加一条记录
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price = sku.price)
                    # todo:更新商品的库存和销量
                    sku.stock -= int(count)
                    sku.sales += int(count)
                    sku.save()


                    # todo:累加计算订单商品的总数量和总价格

                    amount = sku.price*int(count)
                    total_count += int(count)
                    total_price += amount

                    break  # 跳出循环


            # todo: 更新订单信息表中的商品总数量和总价格

            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg':'下单失败 '})

        #todo: 清除用户购物车中的对应记录
        conn.hdel(cart_key, *sku_ids)

        return JsonResponse({'res':5, 'message':'创建订单成功 '})


class OrderPayView(View):
    '''订单支付界面'''
    def post(self, request):
        '''订单支付'''


        #  用户是否登陆
        user = request.user

        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})

        #  接收数据

        order_id = request.POST.get('order_id')

        # 校验数据
        if not order_id:
            return JsonResponse({'res':1, 'errmsg':'无效的订单ID'})

        try:
            order = OrderInfo.objects.get(order_id = order_id,
                                          user = user,
                                          pay_methed = 3,
                                          order_status = 1,)

        except OrderInfo.DoesNotExist:
            return JsonResponse({'res':2, 'errmsg':'订单错误'})


        #  业务处理：使用python SDK 调用支付宝的支付接口
        #  初始化
        alipay = AliPay(
            appid = '',  # 应用id  在测试时，使用沙箱的ID
            app_notify_url = None,  # 默认回调URL
            app_pricate_key_path = os.path.join(settings.BASE_DIR, 'apps/order/app_pricate_key.pem'),  # 协商自己私钥的路径
            alipay_public_key_path = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'),  # 存放支付宝的公钥路径
            sign_type = 'RSA2',
            debug = True,  # 使用沙箱时改为 true   默认 false
        )

        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay = order.total_price + order.transit_price  # Decimal
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 订单id
            total_amount=str(total_pay),  # 支付总金额
            subject='天天生鲜%s' % order_id,
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})


class CheckPayView(View):
    '''查看订单支付的结果'''
    def post(self, request):
        '''查询支付结果'''
        # 用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单id'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理:使用python sdk调用支付宝的支付接口
        # 初始化
        alipay = AliPay(
            appid="2016090800464054",  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )

        # 调用支付宝的交易查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)

            # response = {
            #         "trade_no": "2017032121001004070200176844", # 支付宝交易号
            #         "code": "10000", # 接口调用是否成功
            #         "invoice_amount": "20.00",
            #         "open_id": "20880072506750308812798160715407",
            #         "fund_bill_list": [
            #             {
            #                 "amount": "20.00",
            #                 "fund_channel": "ALIPAYACCOUNT"
            #             }
            #         ],
            #         "buyer_logon_id": "csq***@sandbox.com",
            #         "send_pay_date": "2017-03-21 13:29:17",
            #         "receipt_amount": "20.00",
            #         "out_trade_no": "out_trade_no15",
            #         "buyer_pay_amount": "20.00",
            #         "buyer_user_id": "2088102169481075",
            #         "msg": "Success",
            #         "point_amount": "0.00",
            #         "trade_status": "TRADE_SUCCESS", # 支付结果
            #         "total_amount": "20.00"
            # }

            code = response.get('code')

            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                # 更新订单状态
                order.trade_no = trade_no
                order.order_status = 4 # 待评价
                order.save()
                # 返回结果
                return JsonResponse({'res':3, 'message':'支付成功'})
            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                # 等待买家付款
                # 业务处理失败，可能一会就会成功
                import time
                time.sleep(5)
                continue
            else:
                # 支付出错
                print(code)
                return JsonResponse({'res':4, 'errmsg':'支付失败'})


class CommentView(LoginRequiredMixin, View):
    """订单评论"""
    def get(self, request, order_id):
        """提供评论页面"""
        user = request.user

        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))

        # 根据订单的状态获取订单的状态标题
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 获取订单商品信息
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品的小计
            amount = order_sku.count*order_sku.price
            # 动态给order_sku增加属性amount,保存商品小计
            order_sku.amount = amount
        # 动态给order增加属性order_skus, 保存订单商品信息
        order.order_skus = order_skus

        # 使用模板
        return render(request, "order_comment.html", {"order": order})

    def post(self, request, order_id):
        """处理评论内容"""
        user = request.user
        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))

        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)

        # 循环获取订单中商品的评论内容
        for i in range(1, total_count + 1):
            # 获取评论的商品的id
            sku_id = request.POST.get("sku_%d" % i) # sku_1 sku_2
            # 获取评论的商品的内容
            content = request.POST.get('content_%d' % i, '') # cotent_1 content_2 content_3
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

        order.order_status = 5 # 已完成
        order.save()

        return redirect(reverse("user:order", kwargs={"page": 1}))

