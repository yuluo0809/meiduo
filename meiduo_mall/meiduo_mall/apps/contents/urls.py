from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.IndexView.as_view()),  # 首页路由

    url(r'^index\.html$', views.IndexView.as_view()),
]