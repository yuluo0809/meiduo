from django.conf.urls import url
from meiduo_admin.views.login_view import LoginView

urlpatterns = [
    url(r'^authorizations/$', LoginView.as_view()),
]
