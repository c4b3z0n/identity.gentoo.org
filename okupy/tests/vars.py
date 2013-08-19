# vim:fileencoding=utf8:et:ts=4:sts=4:sw=4:ft=python

""" Various variables used by the tests """

from django.conf import settings
from django.contrib.auth.models import User

from ..accounts.models import Queue


# LDAP directory
DIRECTORY = {
    "o=test": {},
    "cn=anon,o=test": {
        "userPassword": ["{CRYPT}$1$n4jlXi20$.5a8UTvwIqVfVAMlXJ1EZ0"],
    },
    "cn=Manager,o=test": {
        "userPassword": ["{CRYPT}$1$sY4mlRve$0eg5TLYMyZfBCIUgU/RPf0"],
    },
    "ou=people,o=test": {},
    "uid=alice,ou=people,o=test": {
        "uid": ["alice"],
        "userPassword": ['{CRYPT}$1$lO/RU6zz$2fJCOwurxBtCqdImkoLQo1'],
        "objectClass": settings.AUTH_LDAP_USER_OBJECTCLASS +
        settings.AUTH_LDAP_DEV_OBJECTCLASS,
        "uidNumber": ["1000"],
        "gidNumber": ["1000"],
        "givenName": ["Alice"],
        "sn": ["Adams"],
        "mail": ["alice@test.com"],
    },
    "uid=bob,ou=people,o=test": {
        "uid": ["bob"],
        "userPassword": ['{CRYPT}$1$eFSQMJY6$8y.WUL/ONeEarVXqeCIbH.'],
        "objectClass": settings.AUTH_LDAP_USER_OBJECTCLASS,
        "uidNumber": ["1001"],
        "gidNumber": ["50"],
        "givenName": ["Robert"],
        "sn": ["Barker"],
        "mail": ["bob@test.com"],
    }
}

# User objects
USER_ALICE = User(username='alice', password='ldaptest')

# Queue objects
QUEUEDUSER = Queue(
    username='queueduser',
    password='queuedpass',
    email='queued_user@test.com',
    first_name='queued_first_name',
    last_name='queued_last_name',
)

# login form data
LOGIN_ALICE = {'username': 'alice', 'password': 'ldaptest'}
LOGIN_BOB = {'username': 'bob', 'password': 'ldapmoretest'}
LOGIN_WRONG = {'username': 'wrong', 'password': 'wrong'}

# signup form data
SIGNUP_TESTUSER = {
    'username': 'testuser',
    'first_name': 'testfirstname',
    'last_name': 'testlastname',
    'email': 'test@test.com',
    'password_origin': 'testpassword',
    'password_verify': 'testpassword',
}