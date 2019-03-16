from django.conf.urls import url
from user.views import RegisterView, ActiveView,LoginView,UserInfoView,UserOrderView,UserAddressView,LogoutView

urlpatterns = [
    #url(r'^register$', views.register,name='register'),
    #url(r'^register_handle$', views.register_handle, name='register_handle'),
    url(r'^register$',RegisterView.as_view(), name='register'),  # 用户注册
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),  # 用户激活
    url(r'^login$', LoginView.as_view(), name='login'),  # 登录
    url(r'^logout$', LogoutView.as_view(), name='logout'),

    url(r'^$', UserInfoView.as_view(), name='user'),
    url(r'^order(?P<page>\d+)$', UserOrderView.as_view(), name='order'),
    url(r'^address$', UserAddressView.as_view(), name='address')

]