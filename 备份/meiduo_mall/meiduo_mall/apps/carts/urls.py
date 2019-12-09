from django.conf.urls import url

from . import views


urlpatterns = [
    # 购物车增删改查
    url(r'^carts/$', views.CartView.as_view()),
    # 购物车全选/取消全选
    url(r'^carts/selection/$', views.CartSelectedAllView.as_view()),
    # 购物车简单展示
    url(r'^carts/simple/$', views.CartSimpleView.as_view()),
]
