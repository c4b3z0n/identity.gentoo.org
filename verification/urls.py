from django.conf.urls.defaults import patterns

urlpatterns = patterns('okupy.verification.views',
    (r'^(?P<key>[a-zA-Z0-9]+)/$', 'verification', {}, 'verification'),
)
