from django.conf.urls import patterns

urlpatterns = patterns('identity.verification.views',
    (r'^(?P<key>[a-zA-Z0-9]+)/$', 'verification', {}, 'verification'),
)
