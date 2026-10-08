"""#17 文件上传安全测试 (S-07): 魔数校验 / SVG 拒绝 / 空文件 / 下载鉴权。

覆盖 storage.check_magic_bytes 与 MediaUploadView / BrandLogoUploadView / MediaDownloadView。
"""
from django.core.files.storage import default_storage
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.common.storage import check_magic_bytes, save_upload


def _uploaded(name, content, ctype='application/octet-stream'):
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(name, content, content_type=ctype)


class MagicBytesTest(TestCase):
    def test_real_png_ok(self):
        f = _uploaded('a.png', b'\x89PNG\r\n\x1a\nrest', 'image/png')
        check_magic_bytes('.png', f)  # 不抛

    def test_real_pdf_ok(self):
        f = _uploaded('a.pdf', b'%PDF-1.4 ...', 'application/pdf')
        check_magic_bytes('.pdf', f)

    def test_fake_png_rejected(self):
        # exe 头伪装成 .png
        f = _uploaded('evil.png', b'MZ\x90\x00\x03\x00', 'image/png')
        with self.assertRaises(ValueError):
            check_magic_bytes('.png', f)

    def test_fake_jpg_rejected(self):
        f = _uploaded('x.jpg', b'\x89PNG\r\n\x1a\n', 'image/jpeg')
        with self.assertRaises(ValueError):
            check_magic_bytes('.jpg', f)

    def test_text_ok_and_binary_as_text_rejected(self):
        f = _uploaded('n.txt', 'hello 世界'.encode(), 'text/plain')
        check_magic_bytes('.txt', f)
        bad = _uploaded('b.csv', b'\x00\x01\x02\x03binary', 'text/csv')
        with self.assertRaises(ValueError):
            check_magic_bytes('.csv', bad)

    def test_empty_file_rejected(self):
        f = _uploaded('e.png', b'', 'image/png')
        with self.assertRaises(ValueError):
            check_magic_bytes('.png', f)

    def test_save_upload_rejects_fake_ext(self):
        f = _uploaded('trojan.png', b'MZ\x90\x00', 'image/png')
        with self.assertRaises(ValueError):
            save_upload(f)


class MediaUploadViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_user('u1', password='p')
        self.client.force_authenticate(self.user)

    def test_valid_png_201(self):
        f = _uploaded('a.png', b'\x89PNG\r\n\x1a\nxxxx', 'image/png')
        resp = self.client.post('/api/v1/media/upload/', {'file': f}, format='multipart')
        self.assertEqual(resp.status_code, 201)
        self.assertIn('/uploads/', resp.json()['data']['url'])

    def test_fake_png_400(self):
        f = _uploaded('evil.png', b'MZ\x90\x00', 'image/png')
        resp = self.client.post('/api/v1/media/upload/', {'file': f}, format='multipart')
        self.assertEqual(resp.status_code, 400)

    def test_anonymous_401(self):
        anon = APIClient()
        f = _uploaded('a.png', b'\x89PNG\r\n\x1a\n', 'image/png')
        resp = anon.post('/api/v1/media/upload/', {'file': f}, format='multipart')
        self.assertEqual(resp.status_code, 401)


class BrandLogoUploadTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_user('u2', password='p')
        self.client.force_authenticate(self.user)

    def test_svg_rejected(self):
        # 2026-10-08 (#17): SVG 持久型 XSS 载体, 必须拒绝
        f = _uploaded('logo.svg', b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', 'image/svg+xml')
        resp = self.client.post('/api/v1/brand/logo/', {'file': f}, format='multipart')
        self.assertEqual(resp.status_code, 400)

    def test_real_png_ok(self):
        f = _uploaded('logo.png', b'\x89PNG\r\n\x1a\nxx', 'image/png')
        resp = self.client.post('/api/v1/brand/logo/', {'file': f}, format='multipart')
        self.assertEqual(resp.status_code, 201)


class MediaDownloadViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_user('u3', password='p')

    def test_anonymous_401(self):
        anon = APIClient()
        resp = anon.get('/api/v1/media/secure/uploads/x.txt/')
        self.assertEqual(resp.status_code, 401)

    def test_download_existing_ok(self):
        default_storage.save('sec/hello.txt', _content_file(b'hi there'))
        self.client.force_authenticate(self.user)
        resp = self.client.get('/api/v1/media/secure/sec/hello.txt/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'hi there', b''.join(resp.streaming_content))

    def test_path_traversal_rejected(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get('/api/v1/media/secure/../../etc/passwd/')
        self.assertEqual(resp.status_code, 400)

    def test_missing_404(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get('/api/v1/media/secure/nope/ghost.txt/')
        self.assertEqual(resp.status_code, 404)


def _content_file(content):
    from django.core.files.base import ContentFile
    return ContentFile(content)
