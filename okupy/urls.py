# vim:fileencoding=utf8:et:ts=4:sts=4:sw=4:ft=python
from django.conf.urls import patterns, include, url

from .accounts.views import login, index, signup, activate, formerdevlist, foundationlist

urlpatterns = patterns('',
    (r'^$', index),
    (r'^login/$', login),
    (r'^former-devlist/$', formerdevlist),
    (r'^foundation-members/$', foundationlist),
    (r'^signup/$', signup),
    (r'^activate/(?P<token>[a-zA-Z0-9]+)/$', activate),
)
