# -*- coding: utf-8 -*-

from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django_auth_ldap.config import _LDAPConfig
from django_auth_ldap.tests import MockLDAP
from django.contrib.auth.models import User
import logging

class LoginTestsEmptyDB(TestCase):
    logging_configured = False

    def configure_logger(cls):
        if not cls.logging_configured:
            logger = logging.getLogger('django_auth_ldap')
            formatter = logging.Formatter("LDAP auth - %(levelname)s - %(message)s")
            handler = logging.StreamHandler()

            handler.setLevel(logging.DEBUG)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            logger.setLevel(logging.DEBUG)

            cls.logging_configured = True

    configure_logger = classmethod(configure_logger)

    alice = ("uid=alice,ou=people,o=test", {
        "uid": ["alice"],
        "userPassword": ["ldaptest"],
        "objectClass": ["person", "organizationalPerson", "inetOrgPerson", "posixAccount"],
        "uidNumber": ["1000"],
        "gidNumber": ["1000"],
        "givenName": ["Alice"],
        "sn": ["Adams"],
    })
    bob = ("uid=bob,ou=people,o=test", {
        "uid": ["bob"],
        "objectClass": ["person", "organizationalPerson", "inetOrgPerson", "posixAccount"],
        "userPassword": ["ldapmoretest"],
        "uidNumber": ["1001"],
        "gidNumber": ["50"],
        "givenName": ["Robert"],
        "sn": ["Barker"]
    })
    dressler = (u"uid=dreßler,ou=people,o=test".encode('utf-8'), {
        "uid": [u"dreßler".encode('utf-8')],
        "objectClass": ["person", "organizationalPerson", "inetOrgPerson", "posixAccount"],
        "userPassword": ["password"],
        "uidNumber": ["1002"],
        "gidNumber": ["50"],
        "givenName": ["Wolfgang"],
        "sn": [u"Dreßler".encode('utf-8')]
    })

    _mock_ldap = MockLDAP({
        alice[0]: alice[1],
        bob[0]: bob[1],
        dressler[0]: dressler[1],
    })

    def setUp(self):
        self.client = Client()
        self.configure_logger()
        self.ldap = _LDAPConfig.ldap = self._mock_ldap
        self.account = {'username': 'alice', 'password': 'ldaptest'}
        settings.AUTH_LDAP_PERMIT_EMPTY_PASSWORD = False
        settings.AUTH_LDAP_USER_DN_TEMPLATE='uid=%(user)s,ou=people,o=test'
        settings.AUTH_LDAP_USER_ATTR_MAP = {}
        settings.AUTH_LDAP_PROFILE_ATTR_MAP = {}

    def tearDown(self):
        self._mock_ldap.reset()

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
        settings.auth_ldap_user_dn_template='uid=%(user)s,ou=people,o=test'
        account = {'username': ' alice', 'password': 'ldaptest'}
        response = self.client.post('/login/', account)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['location'], 'http://testserver/')
        user = User.objects.get(pk=1)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, 'alice')
        self.assert_(not user.has_usable_password())

    def test_correct_user_trailing_space_in_username(self):
        settings.auth_ldap_user_dn_template='uid=%(user)s,ou=people,o=test'
        account = {'username': 'alice ', 'password': 'ldaptest'}
        response = self.client.post('/login/', account)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['location'], 'http://testserver/')
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
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/')
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
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['location'], 'http://testserver/')
        user = User.objects.get(pk=1)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, u'dreßler')
        self.assert_(not user.has_usable_password())
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
        self.assertEqual(user.email, '')

class LoginTestsOneAccountInDB(TestCase):
    fixtures = ['alice.json']

    logging_configured = False

    def configure_logger(cls):
        if not cls.logging_configured:
            logger = logging.getLogger('django_auth_ldap')
            formatter = logging.Formatter("LDAP auth - %(levelname)s - %(message)s")
            handler = logging.StreamHandler()

            handler.setLevel(logging.DEBUG)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            logger.setLevel(logging.DEBUG)

            cls.logging_configured = True

    configure_logger = classmethod(configure_logger)

    alice = ("uid=alice,ou=people,o=test", {
        "uid": ["alice"],
        "userPassword": ["ldaptest"],
        "objectClass": ["person", "organizationalPerson", "inetOrgPerson", "posixAccount"],
        "uidNumber": ["1000"],
        "gidNumber": ["1000"],
        "givenName": ["Alice"],
        "sn": ["Adams"],
    })
    bob = ("uid=bob,ou=people,o=test", {
        "uid": ["bob"],
        "objectClass": ["person", "organizationalPerson", "inetOrgPerson", "posixAccount"],
        "userPassword": ["ldapmoretest"],
        "uidNumber": ["1001"],
        "gidNumber": ["50"],
        "givenName": ["Robert"],
        "sn": ["Barker"]
    })

    _mock_ldap = MockLDAP({
        alice[0]: alice[1],
        bob[0]: bob[1],
    })

    def setUp(self):
        self.client = Client()
        self.configure_logger()
        self.ldap = _LDAPConfig.ldap = self._mock_ldap
        self.account1 = {'username': 'alice', 'password': 'ldaptest'}
        self.account2 = {'username': 'bob', 'password': 'ldapmoretest'}
        settings.AUTH_LDAP_PERMIT_EMPTY_PASSWORD = False
        settings.AUTH_LDAP_USER_DN_TEMPLATE='uid=%(user)s,ou=people,o=test'
        settings.AUTH_LDAP_USER_ATTR_MAP = {}
        settings.AUTH_LDAP_PROFILE_ATTR_MAP = {}

    def tearDown(self):
        self._mock_ldap.reset()

    def test_dont_authenticate_from_db_when_ldap_is_down(self):
        _LDAPConfig.ldap = None
        response = self.client.post('/login/', self.account1)
        self.assertEqual(response.context['notification']['error'], u'Login failed')
        self.assertEqual(User.objects.count(), 1)
        self.assert_(not User.objects.get(pk=1).has_usable_password())

    def test_authenticate_account_that_is_already_in_db(self):
        response = self.client.post('/login/', self.account1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/')
        user = User.objects.get(pk=1)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, 'alice')
        self.assert_(not user.has_usable_password())
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
        self.assertEqual(user.email, '')

    def test_authenticate_new_account(self):
        response = self.client.post('/login/', self.account2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/')
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
