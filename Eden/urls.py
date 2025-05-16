import os
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from Website.views import home, raspberry, api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', home.login_view, name='login'),
    path('statuses/', home.statuses_page, name='statuses'),
    path('logout/', home.logout_view, name='logout'),
    path('', home.home_page, name='home'),

    path('<int:id>/threshold/', raspberry.manage_greenhouse, name='raspberry_threshold'),
    path('<int:id>/graphs/', raspberry.graph_page, name='raspberry_charts'),
    path('raspberry/update/<int:id>/', raspberry.raspberry_update, name='raspberry_update'),
    path('raspberry/delete/<int:id>/', raspberry.raspberry_delete, name='raspberry_delete'),
    path('raspberry/<int:id>/<str:device>', raspberry.toggle_device, name='toggle_device'),

    path('api/sensor-data/', api.receive_sensor_data, name='receive_sensor_data'),
    path('api/sensor-data/<int:raspberry_id>/', api.get_latest_sensor_data, name='get_latest_sensor_data'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'Website.views.home.handler404'
