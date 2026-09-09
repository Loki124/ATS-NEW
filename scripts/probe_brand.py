"""品牌信息管理 (G43) 端到端探针：用 Django 测试客户端 + 真实 JWT 验证 /api/v1/brand/。"""
import django, os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()
# 探针用 Django 测试客户端，其默认 Host=testserver；放宽 ALLOWED_HOSTS 仅用于本地验证
from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

from django.test import Client
from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.models import User

# 取一个已有用户；没有就建一个最小超管用于探针（不影响业务数据语义）
user = User.objects.first()
if user is None:
    user = User(username='__brand_probe__', is_staff=True, is_superuser=True, email='probe@probe.local')
    user.set_password('probe')
    user.save()

token = str(RefreshToken.for_user(user).access_token)
c = Client()

print('=== GET /api/v1/brand/ (初始) ===')
r = c.get('/api/v1/brand/', HTTP_AUTHORIZATION=f'Bearer {token}')
print('status:', r.status_code)
body = json.loads(r.content)
print('data keys:', sorted(body.get('data', {}).keys()))
print('companyName(空):', repr(body['data'].get('companyName')))

print('\n=== PUT /api/v1/brand/ (camelCase 入参) ===')
payload = {
    'companyName': '腾讯招聘',
    'brandSlogan': '用户为本，科技向善',
    'brandIntro': '欢迎加入我们，一起创造影响数亿人的产品。',
    'logoUrl': 'https://example.com/logo.png',
    'portalTitle': '加入腾讯',
    'portalSubtitle': '与世界级的团队共事',
    'portalBannerUrl': 'https://example.com/banner.png',
    'primaryColor': '#6366F1',
    'contactEmail': 'campus@tencent.com',
    'contactPhone': '0755-12345678',
    'socialLinks': [
        {'platform': 'official_site', 'label': '官网', 'url': 'https://careers.tencent.com'},
        {'platform': 'wechat', 'label': '微信公众号', 'url': 'https://weixin.qq.com'},
    ],
}
r2 = c.put('/api/v1/brand/', data=json.dumps(payload), content_type='application/json',
           HTTP_AUTHORIZATION=f'Bearer {token}')
print('status:', r2.status_code)
body2 = json.loads(r2.content)
print('companyName:', body2['data'].get('companyName'))
print('socialLinks len:', len(body2['data'].get('socialLinks', [])))
print('updatedAt:', body2['data'].get('updatedAt'))

print('\n=== GET /api/v1/brand/ (确认持久化 + snake→camel 渲染) ===')
r3 = c.get('/api/v1/brand/', HTTP_AUTHORIZATION=f'Bearer {token}')
body3 = json.loads(r3.content)
assert body3['data']['companyName'] == '腾讯招聘', '持久化失败'
assert body3['data']['primaryColor'] == '#6366F1', '颜色未持久化'
assert len(body3['data']['socialLinks']) == 2, '链接未持久化'
print('OK 持久化校验通过; companyName =', body3['data']['companyName'])

print('\n=== 注入非法 socialLinks (缺 url) 应 400 ===')
r4 = c.put('/api/v1/brand/', data=json.dumps({'socialLinks': [{'platform': 'x'}]}),
           content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
print('status:', r4.status_code, '(期望 400)')

print('\n=== 未带 token 应 401 ===')
r5 = c.get('/api/v1/brand/')
print('status:', r5.status_code, '(期望 401)')

print('\n=== 清理探针副作用 ===')
from apps.brand.models import BrandInfo
BrandInfo.objects.all().delete()
if user.username == '__brand_probe__':
    user.delete()
print('cleanup done (brand rows + probe user removed)')
print('\nALL PROBES DONE')
