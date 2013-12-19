from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('polls.views',
    url(r'^$', 'index'),
    url(r'^upload$', 'uploadFile'),
    url(r'^songs$', 'songs'),
    url(r'^stream$', 'stream'),
    url(r'^finishedUpload$', 'finishedUpload'),
    url(r'^about$', 'about'),
    url(r'^polls/$', 'result'),
    #url(r'^.*.css$', 'css'),
    #url(r'^polls/(?P<poll_id>\d+)/$', 'detail'),
    #url(r'^polls/(?P<poll_id>\d+)/results/$', 'results'),
    #url(r'^polls/(?P<poll_id>\d+)/vote/$', 'vote'),
)

urlpatterns += patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

#todo: check if this is needed
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()
