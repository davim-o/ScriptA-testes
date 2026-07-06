from django.test import TestCase


class LoginRoutesTests(TestCase):
    def test_login_page_is_available_at_login_url(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, 200)
