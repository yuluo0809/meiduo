from django.conf.urls import url

from . import views

urlpatterns = [
    # 用户注册
    url(r'^register/$', views.RegisterView.as_view(), name='register'),
    # 判断用户名是否重复
    url(r'^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/$', views.UsernameCountView.as_view()),
    # 判断手机号是否重复
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
    # 用户登录
    url(r'^login/$', views.LoginView.as_view()),
    # 用户退出登录
    url(r'^logout/$', views.LogoutView.as_view()),
    # 用户中心
    url(r'^info/$', views.InfoView.as_view()),
    # 用户邮箱设置
    url(r'^emails/$', views.EmailView.as_view()),
    # 用户邮箱激活
    url(r'^emails/verification/$', views.EmailVerifyView.as_view()),
    # 展示收货地址
    url(r'^addresses/$', views.AddressView.as_view()),
]


