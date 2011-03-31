from django.conf.urls.defaults import *
urlpatterns = patterns('hide.views',
    (r'^doc/(?P<id>\w+)/','detail'),
    (r'^$','index'), 
    (r'^list/$', 'objlist'),
    (r'^delete/(?P<id>\w+)/','delete'), 
#    (r'^managesets/$', 'managesets'),
    (r'^label/$', 'labeldocs'),
    (r'^settings/?$', 'editsettings'),
    (r'^anonymize/$', 'anonymizelist'),
    (r'^anonymize/(?P<tag>.+)$', 'anonymize'),
    (r'^random/$', 'randomReport'),
    (r'^autolabel/(?P<id>\w+)/?','autolabel'),
    (r'^autolabelset/(?P<tag>.+)/?','autolabelset'),
    (r'^trainsets/$', 'trainsets'),
    (r'^train/?$', 'trainblank'),
    (r'^train/(?P<tag>.+)$', 'train'),
    (r'^deidentify/?$', 'deidentifyblank'), 
    (r'^deidentify/(?P<id>\w+)$', 'deidentify'),
    (r'^deidentifyset/(?P<tag>.+)$', 'deidentifyset'),
    (r'^add/$', 'add'),
    (r'^export/$', 'exportlist'),
    (r'^export/(?P<tag>.+)/?$', 'export'),
    (r'^analysis/$', 'analysislist'),
    (r'^accuracy/$', 'accuracy'),
    (r'^evaluate/$', 'evaluate'),
    (r'^analysis/(?P<tag>.+)/?$', 'analysis'),
    (r'^anondoc/(?P<id>\w+)/?', 'anondoc'),
    (r'^delete_label/(?P<tag>.+)/?', 'delete_label'),
    (r'^dpdp/$', 'dpdp')
#    (r'^reset','reset'), 
)
