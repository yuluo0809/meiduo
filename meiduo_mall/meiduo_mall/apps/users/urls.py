from django.conf.urls import url

from . import views

urlpatterns = [
    # 用户注册
    url(r'^register/$', views.RegisterView.as_view(), name='register'),
]


