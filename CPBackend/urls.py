from django.urls import path
from .views import login_view, start_mission_planner  # 导入你的登录视图和任务规划视图

urlpatterns = [
    path('login/', login_view, name='api-login'),  # 登录路由
    path('start_mission_planner/', start_mission_planner, name='start_mission_planner'),  # 添加任务规划路由
]
