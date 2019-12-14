from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import date, timedelta
from users.models import User
from rest_framework.generics import ListAPIView
from goods.models import GoodsVisitCount
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action

from meiduo_admin.constants import NowDayZeroTime
from meiduo_admin.serializers.home_serializers import GoodsVisitCountModelSerializer


class HomeViewSet(ViewSet):
    @action(methods=['get'], detail=False)
    def total_count(self, request):
        total_users = User.objects.all().count()

        times = NowDayZeroTime()

        return Response({
            "count": total_users,
            "date": times.get("time_date")
        })

    @action(methods=['get'], detail=False)
    def day_increment(self, request):
        times = NowDayZeroTime()
        ZeroTime_local = times.get("ZeroTime_local")
        total_increments = User.objects.filter(date_joined__gte=ZeroTime_local).count()

        return Response({
            "count": total_increments,
            "date": times.get("time_date")
        })

    @action(methods=['get'], detail=False)
    def day_active(self, request):
        times = NowDayZeroTime()
        ZeroTime_local = times.get('ZeroTime_local')
        total_login_users = User.objects.filter(last_login__gte=ZeroTime_local).count()

        return Response({
            "count": total_login_users,
            "date": times.get("time_date")
        })

    @action(methods=['get'], detail=False)
    def day_orders(self, request):
        times = NowDayZeroTime()
        ZeroTime_local = times.get("ZeroTime_local")
        total_orders = User.objects.filter(orderinfo__create_time__gte=ZeroTime_local).count()

        return Response({
            "count": total_orders,
            "date": times.get("time_date")
        })

    @action(methods=['get'], detail=False)
    def month_increment(self, request):
        times = NowDayZeroTime()
        today = times.get("time_date")
        start_day = today - timedelta(days=29)

        date_list = []
        for index in range(30):
            first_day_date = start_day + timedelta(days=index)
            next_day_date = first_day_date + timedelta(days=1)

            count = User.objects.filter(
                date_joined__gte=first_day_date,
                date_joined__lt=next_day_date
            ).count()

            date_list.append({
                "count": count,
                "date": first_day_date
            })

        return Response(date_list)


class GoodsVisitCountView(ListAPIView):
    queryset = GoodsVisitCount.objects.all()
    serializer_class = GoodsVisitCountModelSerializer

    def get_queryset(self):
        times = NowDayZeroTime()
        ZeroTime_local = times.get("ZeroTime_local")
        queryset = GoodsVisitCount.objects.filter(create_time__gte=ZeroTime_local)
        return queryset
