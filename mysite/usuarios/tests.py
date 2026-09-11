from django.test import TestCase


class LoginRoutesTests(TestCase):
    def test_login_page_is_available(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
