from django.conf.urls import url

from . import views


urlpatterns = [
    # 拼接支付url
    url(r'^payment/(?P<order_id>\d+)/$', views.PaymentURLView.as_view()),
    # 保存支付结果
    url(r'^payment/status/$', views.PaymentStatusView.as_view()),
]