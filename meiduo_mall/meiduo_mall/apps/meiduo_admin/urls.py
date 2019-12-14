from django.conf.urls import url
from meiduo_admin.views.login_view import LoginView
from meiduo_admin.views.Home_View import *
from meiduo_admin.views.user_view import *
from meiduo_admin.views.sku_view import *
from rest_framework_jwt.views import obtain_jwt_token
from rest_framework.routers import SimpleRouter

urlpatterns = [
    # url(r'^authorizations/$', LoginView.as_view()),

    url(r'^authorizations/$', obtain_jwt_token),

    url(r'^statistical/goods_day_views/$', GoodsVisitCountView.as_view()),

    url(r"^users/$", UserListCreateView.as_view()),

    url(r'^skus/$', SKUViewSet.as_view({'get': 'list'}))
]

router = SimpleRouter()
router.register(prefix='statistical', viewset=HomeViewSet, base_name='home')
urlpatterns += router.urls
