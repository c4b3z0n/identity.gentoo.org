# vim:fileencoding=utf8:et:ts=4:sts=4:sw=4:ft=python

from django.conf import settings
from django.core import mail
from django.core.urlresolvers import resolve
from django.template import RequestContext

from mockldap import MockLdap
from passlib.hash import ldap_md5_crypt

from okupy.accounts.forms import SignupForm
from okupy.accounts.models import Queue
from okupy.accounts.views import signup, activate
from okupy.common.test_helpers import (OkupyTestCase, set_request, ldap_users,
                                       no_database)
from okupy.tests import vars


class SignupUnitTests(OkupyTestCase):
    @classmethod
    def setUpClass(cls):
        cls.mockldap = MockLdap(vars.DIRECTORY)

    @classmethod
    def tearDownClass(cls):
        del cls.mockldap

    def setUp(self):
        self.mockldap.start()
        self.ldapobj = self.mockldap[settings.AUTH_LDAP_SERVER_URI]

    def tearDown(self):
        self.mockldap.stop()
        del self.ldapobj

    def test_username_already_exists_in_ldap(self):
        _form = vars.SIGNUP_TESTUSER.copy()
        _form['username'] = 'alice'
        request = set_request(uri='/signup', post=_form, messages=True)
        response = signup(request)
        response.context = RequestContext(request)
        self.assertMessage(response, 'Username already exists', 40)

    def test_email_already_exists_in_ldap(self):
        _form = vars.SIGNUP_TESTUSER.copy()
        _form['email'] = 'alice@test.com'
        request = set_request(uri='/signup', post=_form, messages=True)
        response = signup(request)
        response.context = RequestContext(request)
        self.assertMessage(response, 'Email already exists', 40)

    def test_username_already_pending_activation(self):
        _form = vars.SIGNUP_TESTUSER.copy()
        _form['username'] = 'queueduser'
        vars.QUEUEDUSER.save()
        request = set_request(uri='/signup', post=_form, messages=True)
        response = signup(request)
        response.context = RequestContext(request)
        self.assertMessage(response,
                           'Account is already pending activation', 40)

    def test_email_already_pending_activation(self):
        _form = vars.SIGNUP_TESTUSER.copy()
        _form['email'] = 'queued_user@test.com'
        vars.QUEUEDUSER.save()
        request = set_request(uri='/signup', post=_form, messages=True)
        response = signup(request)
        response.context = RequestContext(request)
        self.assertMessage(response,
                           'Account is already pending activation', 40)

    def test_add_queued_account_to_ldap_prints_success_message(self):
        vars.QUEUEDUSER.save()
        activate_url = '/activate/%s/' % vars.QUEUEDUSER.encrypted_id
        request = set_request(uri=activate_url, messages=True)
        response = activate(request, vars.QUEUEDUSER.encrypted_id)
        response.context = RequestContext(request)
        self.assertMessage(response,
                           'Your account has been activated successfully', 25)

    def test_queued_account_gets_added_to_ldap(self):
        vars.QUEUEDUSER.save()
        activate_url = '/activate/%s/' % vars.QUEUEDUSER.encrypted_id
        request = set_request(activate_url, messages=True)
        activate(request, vars.QUEUEDUSER.encrypted_id)
        self.assertTrue(ldap_users(vars.QUEUEDUSER.username,
                        directory=self.ldapobj.directory))
        ldap_account = ldap_users(vars.QUEUEDUSER.username,
                                  directory=self.ldapobj.directory)[1]
        self.assertEqual(ldap_account['objectClass'],
                         settings.AUTH_LDAP_USER_OBJECTCLASS)
        self.assertEqual(ldap_account['sn'][0], vars.QUEUEDUSER.last_name)
        self.assertEqual(ldap_account['cn'][0], '%s %s' % (
            vars.QUEUEDUSER.first_name, vars.QUEUEDUSER.last_name))
        self.assertTrue(ldap_md5_crypt.verify(vars.QUEUEDUSER.password,
                                              ldap_account['userPassword'][0]))
        self.assertEqual(ldap_account['givenName'][0],
                         vars.QUEUEDUSER.first_name)
        self.assertEqual(ldap_account['mail'][0], vars.QUEUEDUSER.email)
        self.assertEqual(ldap_account['uid'][0], vars.QUEUEDUSER.username)
        self.assertEqual(ldap_account['uidNumber'][0], '1002')
        self.assertEqual(ldap_account['gidNumber'][0], '100')
        self.assertEqual(ldap_account['gecos'][0], '%s %s' % (
            vars.QUEUEDUSER.first_name, vars.QUEUEDUSER.last_name))
        self.assertEqual(ldap_account['homeDirectory'][0],
                         '/home/%s' % vars.QUEUEDUSER.username)
        self.assertEqual(ldap_account['gentooACL'][0], 'user.group')

    def test_add_queued_account_remove_from_queue(self):
        vars.QUEUEDUSER.save()
        activate_url = '/activate/%s/' % vars.QUEUEDUSER.encrypted_id
        request = set_request(activate_url, messages=True)
        activate(request, vars.QUEUEDUSER.encrypted_id)
        self.assertEqual(Queue.objects.count(), 0)

    def test_valid_data_to_signup_form_prints_info_message(self):
        request = set_request(uri='/signup', post=vars.SIGNUP_TESTUSER,
                              messages=True)
        response = signup(request)
        response.context = RequestContext(request)
        self.assertMessage(response,
                           'You will shortly receive an activation mail', 20)

    def test_valid_data_to_signup_form_sends_activation_mail(self):
        request = set_request(uri='/signup', post=vars.SIGNUP_TESTUSER,
                              messages=True)
        response = signup(request)
        response.context = RequestContext(request)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '%sAccount Activation' %
                         settings.EMAIL_SUBJECT_PREFIX)

    def test_valid_data_to_signup_form_adds_user_to_queue(self):
        request = set_request(uri='/signup', post=vars.SIGNUP_TESTUSER,
                              messages=True)
        response = signup(request)
        response.context = RequestContext(request)
        self.assertEqual(Queue.objects.count(), 1)
        vars.QUEUEDUSER = Queue.objects.get(pk=1)
        self.assertEqual(vars.QUEUEDUSER.username,
                         vars.SIGNUP_TESTUSER['username'])
        self.assertEqual(vars.QUEUEDUSER.first_name,
                         vars.SIGNUP_TESTUSER['first_name'])
        self.assertEqual(vars.QUEUEDUSER.last_name,
                         vars.SIGNUP_TESTUSER['last_name'])
        self.assertEqual(vars.QUEUEDUSER.email, vars.SIGNUP_TESTUSER['email'])
        self.assertEqual(vars.QUEUEDUSER.password,
                         vars.SIGNUP_TESTUSER['password_origin'])
        # note: this needs to be kept in line with used cipher
        self.assertRegexpMatches(vars.QUEUEDUSER.encrypted_id,
                                 '^[a-zA-Z0-9_-]{22}$')

    @no_database()
    def test_no_database_connection_raises_error_in_signup(self):
        request = set_request(uri='/signup', post=vars.SIGNUP_TESTUSER,
                              messages=True)
        response = signup(request)
        response.context = RequestContext(request)
        self.assertMessage(response, "Can't contact the database", 40)

    @no_database()
    def test_no_database_connection_sends_notification_mail_in_signup(self):
        request = set_request(uri='/signup', post=vars.SIGNUP_TESTUSER,
                              messages=True)
        response = signup(request)
        response.context = RequestContext(request)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(mail.outbox[0].subject.startswith('%sERROR:' %
                        settings.EMAIL_SUBJECT_PREFIX))

    @no_database()
    def test_no_database_connection_raises_error_in_activation(self):
        request = set_request('/activate/test', messages=True)
        response = activate(request, vars.QUEUEDUSER.encrypted_id)
        response.context = RequestContext(request)
        self.assertMessage(response, "Can't contact the database", 40)

    @no_database()
    def test_no_database_connection_sends_notificationmail_in_activation(self):
        request = set_request('/activate/test', messages=True)
        activate(request, vars.QUEUEDUSER.encrypted_id)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(mail.outbox[0].subject.startswith('%sERROR:' %
                        settings.EMAIL_SUBJECT_PREFIX))

    def test_add_first_user_in_empty_ldap_directory(self):
        vars.QUEUEDUSER.save()
        activate_url = '/activate/%s/' % vars.QUEUEDUSER.encrypted_id
        self.ldapobj.directory = ldap_users(clean=True)
        request = set_request(activate_url, messages=True)
        activate(request, vars.QUEUEDUSER.encrypted_id)
        self.assertTrue(ldap_users(vars.QUEUEDUSER.username,
                        directory=self.ldapobj.directory))
        self.assertEqual(ldap_users(
            vars.QUEUEDUSER.username,
            directory=self.ldapobj.directory)[1]['uidNumber'][0], '1')


class SignupunitTestsNoLDAP(OkupyTestCase):
    def test_signup_url_resolves_to_signup_view(self):
        found = resolve('/signup/')
        self.assertEqual(found.func, signup)

    def test_signup_page_returns_200_for_anonymous(self):
        request = set_request(uri='/signup')
        response = signup(request)
        self.assertEqual(response.status_code, 200)

    def test_rendered_signup_form(self):
        request = set_request(uri='/signup')
        response = signup(request)
        signup_form_part = '<label for="id_first_name">First Name:</label><input id="id_first_name" maxlength="100" name="first_name" type="text" />'  # noqa
        self.assertIn(signup_form_part, response.content)

    def test_empty_signup_form_raises_form_error_messages(self):
        request = set_request(uri='/signup')
        response = signup(request)
        response.context = RequestContext(request, {'signup_form':
                                          SignupForm(request.POST)})
        self.assertFormError(response, 'signup_form', 'username',
                             'This field is required.')
        self.assertFormError(response, 'signup_form', 'first_name',
                             'This field is required.')
        self.assertFormError(response, 'signup_form', 'last_name',
                             'This field is required.')
        self.assertFormError(response, 'signup_form', 'email',
                             'This field is required.')
        self.assertFormError(response, 'signup_form', 'password_origin',
                             'This field is required.')
        self.assertFormError(response, 'signup_form', 'password_verify',
                             'This field is required.')

    def test_passwords_dont_match(self):
        _form = vars.SIGNUP_TESTUSER.copy()
        _form['password_verify'] = 'wrong'
        request = set_request(uri='/signup', post=_form)
        response = signup(request)
        response.context = RequestContext(request, {'signup_form':
                                          SignupForm(request.POST)})
        self.assertFormError(response, 'signup_form', 'password_verify',
                             "Passwords don't match")

    def test_wrong_activaltion_link_raises_invalid_url(self):
        request = set_request(uri='/activate/invalidurl', messages=True)
        response = activate(request, 'invalidurl')
        response.context = RequestContext(request)
        self.assertMessage(response, 'Invalid URL', 40)

    def test_no_ldap_connection_raises_error_in_signup(self):
        request = set_request(uri='/signup', post=vars.SIGNUP_TESTUSER,
                              messages=True)
        response = signup(request)
        response.context = RequestContext(request)
        self.assertMessage(response, "Can't contact LDAP server", 40)

    def test_no_ldap_connection_sends_notification_mail_in_signup(self):
        request = set_request(uri='/signup', post=vars.SIGNUP_TESTUSER,
                              messages=True)
        response = signup(request)
        response.context = RequestContext(request)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            '%sERROR: {\'desc\': "Can\'t contact LDAP server"}' %
            settings.EMAIL_SUBJECT_PREFIX)

    def test_no_ldap_connection_raises_error_in_activation(self):
        vars.QUEUEDUSER.save()
        activate_url = '/activate/%s/' % vars.QUEUEDUSER.encrypted_id
        request = set_request(activate_url, messages=True)
        response = activate(request, vars.QUEUEDUSER.encrypted_id)
        response.context = RequestContext(request)
        self.assertMessage(response, "Can't contact LDAP server", 40)

    def test_no_ldap_connection_sends_notification_mail_in_activation(self):
        vars.QUEUEDUSER.save()
        activate_url = '/activate/%s/' % vars.QUEUEDUSER.encrypted_id
        request = set_request(activate_url, messages=True)
        response = activate(request, vars.QUEUEDUSER.encrypted_id)
        response.context = RequestContext(request)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            '%sERROR: {\'desc\': "Can\'t contact LDAP server"}' %
            settings.EMAIL_SUBJECT_PREFIX)
