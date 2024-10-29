from django.urls import path
from .views import login_view  # 导入你的登录视图

urlpatterns = [
    path('login/', login_view, name='api-login'),  # 添加登录路由
]
