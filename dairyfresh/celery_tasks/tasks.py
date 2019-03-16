from django.core.mail import send_mail
from django.conf import settings
from celery import Celery

from django.template import loader

import time

# 在任务处理者一端加这几句
import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dairyfresh.settings")
# django.setup()
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from django_redis import get_redis_connection

# 创建一个Celery类的实例对象
app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/6 ')


# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    # 组织邮件信息
    subject = '天天生鲜欢迎信息'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (username, token, token)

    send_mail(subject, message, sender, receiver, html_message=html_message)


@app.task
def genegrate_static_index_html():
    '''create static index html'''
    # 获取商品种 lei xin xi
    types = GoodsType.objects.all()

    # 获取商品轮播信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    for goods_type in types:
        # 获取goods_type种类首页分类商品的图片展示信息
        image_banners = IndexTypeGoodsBanner.objects.filter(type=goods_type, display_type=1).order_by('index')
        # 获取goods_type种类首页分类商品的文字展示信息
        title_banners = IndexTypeGoodsBanner.objects.filter(type=goods_type, display_type=0).order_by('index')

        # 给goods_type种类动态添加属性
        goods_type.image_banners = image_banners
        goods_type.title_banners = title_banners



    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners,
               }

    #use templates

    temp = loader.get_template('static_index.html')
    static_index_html = temp.render(context)

    save_path =os.path.join(settings.BASE_DIR, 'static/index.html')

    with open(save_path, 'w') as f:
        f.write(static_index_html)