# -*- coding: utf-8 -*-

from django_auth_ldap.config import _LDAPConfig
from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client
from django.test.utils import override_settings
from okupy.tests import _mock_ldap
import logging

logger = logging.getLogger('django_auth_ldap')

@override_settings(AUTH_LDAP_USER_DN_TEMPLATE='uid=%(user)s,ou=people,o=test')
class LoginTestsEmptyDB(TestCase):
    def setUp(self):
        self.client = Client()
        self.ldap = _LDAPConfig.ldap = _mock_ldap
        self.account = {'username': 'alice', 'password': 'ldaptest'}

    def tearDown(self):
        _mock_ldap.reset()

    def test_template(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('login_form' in response.context)
        self.assertTrue('notification' in response.context)

    def test_empty_user(self):
        response = self.client.post('/login/')
        self.assertEqual(response.context['login_form']['username'].errors, [u'This field is required.'])
        self.assertEqual(response.context['login_form']['password'].errors, [u'This field is required.'])
        self.assertEqual(response.context['notification']['error'], u'Login failed')
        self.assertEqual(User.objects.count(), 0)

    def test_correct_user_leading_space_in_username(self):
        account = {'username': ' alice', 'password': 'ldaptest'}
        response = self.client.post('/login/', account)
        self.assertRedirects(response, '/')
        user = User.objects.get(pk=1)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, 'alice')
        self.assert_(not user.has_usable_password())

    def test_correct_user_trailing_space_in_username(self):
        account = {'username': 'alice ', 'password': 'ldaptest'}
        response = self.client.post('/login/', account)
        self.assertRedirects(response, '/')
        user = User.objects.get(pk=1)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, 'alice')
        self.assert_(not user.has_usable_password())

    def test_incorrect_user(self):
        wrong_account = {'username': 'username', 'password': 'password'}
        response = self.client.post('/login/', wrong_account)
        self.assertEqual(response.context['notification']['error'], u'Login failed')
        self.assertEqual(User.objects.count(), 0)

    def test_correct_user(self):
        response = self.client.post('/login/', self.account)
        self.assertRedirects(response, '/')
        user = User.objects.get(pk=1)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, 'alice')
        self.assert_(not user.has_usable_password())
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
        self.assertEqual(user.email, '')

    def test_no_ldap(self):
        _LDAPConfig.ldap = None
        response = self.client.post('/login/', self.account)
        self.assertEqual(response.context['notification']['error'], u'Login failed')
        self.assertEqual(User.objects.count(), 0)

    def test_weird_account(self):
        account = {'username': 'dreßler', 'password': 'password'}
        response = self.client.post('/login/', account)
        self.assertRedirects(response, '/')
        user = User.objects.get(pk=1)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, u'dreßler')
        self.assert_(not user.has_usable_password())
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
        self.assertEqual(user.email, '')

@override_settings(AUTH_LDAP_USER_DN_TEMPLATE='uid=%(user)s,ou=people,o=test')
class LoginTestsOneAccountInDB(TestCase):
    fixtures = ['alice']

    def setUp(self):
        self.client = Client()
        self.ldap = _LDAPConfig.ldap = _mock_ldap
        self.account1 = {'username': 'alice', 'password': 'ldaptest'}
        self.account2 = {'username': 'bob', 'password': 'ldapmoretest'}

    def tearDown(self):
        _mock_ldap.reset()

    def test_dont_authenticate_from_db_when_ldap_is_down(self):
        _LDAPConfig.ldap = None
        response = self.client.post('/login/', self.account1)
        self.assertEqual(response.context['notification']['error'], u'Login failed')
        self.assertEqual(User.objects.count(), 1)
        self.assert_(not User.objects.get(pk=1).has_usable_password())

    def test_authenticate_account_that_is_already_in_db(self):
        response = self.client.post('/login/', self.account1)
        self.assertRedirects(response, '/')
        user = User.objects.get(pk=1)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, 'alice')
        self.assert_(not user.has_usable_password())
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
        self.assertEqual(user.email, '')

    def test_authenticate_new_account(self):
        response = self.client.post('/login/', self.account2)
        self.assertRedirects(response, '/')
        self.assertEqual(User.objects.count(), 2)
        user1 = User.objects.get(pk=1)
        self.assertEqual(user1.username, 'alice')
        self.assert_(not user1.has_usable_password())
        self.assertEqual(user1.first_name, '')
        self.assertEqual(user1.last_name, '')
        self.assertEqual(user1.email, '')
        user2 = User.objects.get(pk=2)
        self.assertEqual(user2.username, 'bob')
        self.assert_(not user2.has_usable_password())
        self.assertEqual(user2.first_name, '')
        self.assertEqual(user2.last_name, '')
        self.assertEqual(user2.email, '')