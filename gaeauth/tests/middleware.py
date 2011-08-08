from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from flexmock import flexmock
from google.appengine.api import users


class GoogleRemoteUserMiddlewareTest(TestCase):
    urls = 'gaeauth.tests.urls'
    middleware = 'gaeauth.middleware.GoogleRemoteUserMiddleware'
    backend = 'gaeauth.backends.GoogleAccountBackend'

    def setUp(self):
        self.curr_middleware = settings.MIDDLEWARE_CLASSES
        self.curr_auth = settings.AUTHENTICATION_BACKENDS
        settings.MIDDLEWARE_CLASSES += (self.middleware,)
        settings.AUTHENTICATION_BACKENDS = (self.backend,)
        self.email = 'user@example.com'
        flexmock(users)
        users.should_receive('get_current_user').and_return(users.User(
            email=self.email, _auth_domain='example.com', _user_id=12345))

    def tearDown(self):
        settings.MIDDLEWARE_CLASSES = self.curr_middleware
        settings.AUTHENTICATION_BACKENDS = self.curr_auth

    def test_no_google_user(self):
        """
        Tests that no user is created when there is no Google user returned by
        the App Engine users API.
        """
        num_users = User.objects.count()
        users.should_receive('get_current_user').and_return(None)
        response = self.client.get('/remote_user/')
        self.assertTrue(response.context['user'].is_anonymous())
        self.assertEqual(User.objects.count(), num_users)

    def test_unknown_user(self):
        """
        Tests the case where the Google user returned by the App Engine users
        API does not yet exist as a Django User.
        """
        num_users = User.objects.count()
        response = self.client.get('/remote_user/', USER_EMAIL=self.email)
        self.assertEqual(response.context['user'].username, 'user')
        self.assertEqual(User.objects.count(), num_users + 1)
        User.objects.get(username='user')

    def test_known_user(self):
        """
        Tests the case where the Google user already exists as a Django user.
        """
        User.objects.create(username='user', password='12345')
        num_users = User.objects.count()
        response = self.client.get('/remote_user/', USER_EMAIL=self.email)
        self.assertEqual(response.context['user'].username, 'user')
        self.assertEqual(User.objects.count(), num_users)
        # Test that a different user passed in the headers causes the new user
        # to be created.
        email2 = 'user2@example.com'
        users.should_receive('get_current_user').and_return(users.User(
            email=email2, _auth_domain='example.com', _user_id=123456))
        response = self.client.get('/remote_user/', USER_EMAIL=email2)
        self.assertEqual(response.context['user'].username, 'user2')
        self.assertEqual(User.objects.count(), num_users + 1)


