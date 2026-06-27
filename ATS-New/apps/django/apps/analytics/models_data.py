"""G35 DataSubscription 等模型 - 临时 stub
远端 origin/main 缺这个文件,实际功能未实现。先建空 stub 让 Django 启动。
"""
from django.db import models


class DataSubscription(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'analytics'
        db_table = 'analytics_data_subscription'
