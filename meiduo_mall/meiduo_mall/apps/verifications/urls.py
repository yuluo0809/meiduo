from django.conf.urls import urlfrom . import viewsurlpatterns = [    # 图形验证码    url(r'^image_codes/(?P<uuid>[\w-]+)/$', views.ImageCodeView.as_view()),    # 短信验证码    url(r'^sms_codes/(?P<mobile>1[3-9]\d{9})/$', views.SMSCodeView.as_view()),    # 验证账户    url(r'^accounts/(?P<accounts>[a-zA-Z0-9_-]{5,20})/sms/token/$', views.VerifyAccountsView.as_view()),    # 发送短信验证    url(r'^sms_codes/$', views.AccountSMSView.as_view()),    # 验证手机验证码    url(r'^accounts/(?P<accounts>[a-zA-Z0-9_-]{5,20})/password/token/$', views.VerifySMSCodeView.as_view()),]