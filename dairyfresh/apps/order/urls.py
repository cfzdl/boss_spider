from django.conf.urls import url
from order.views import OrderPlaceView, OrderCommitView, OrderPayView, CommentView


urlpatterns = [
    url(r'^place$', OrderPlaceView.as_view(), name='place'),
    url(r'^commit$', OrderCommitView.as_view(), name='commit'),
    url(r'^pay', OrderPayView.as_view(), name='pay'),
    url(r'^comment', OrderCommitView.as_view(), name='comment')
]