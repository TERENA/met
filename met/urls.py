#################################################################
# MET v2 Metadate Explorer Tool
#
# This Software is Open Source. See License: https://github.com/TERENA/met/blob/master/LICENSE.md
# Copyright (c) 2012, TERENA All rights reserved.
#
# This Software is based on MET v1 developed for TERENA by Yaco Sistemas, http://www.yaco.es/
# MET v2 was developed for TERENA by Tamim Ziai, DAASI International GmbH, http://www.daasi.de
# Current version of MET has been revised for performance improvements by Andrea Biancini,
# Consortium GARR, http://www.garr.it
##########################################################################

from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib import admin
from django.views.generic import TemplateView

admin.autodiscover()

urlpatterns = patterns('',
                       # Examples:
                       url(r'^$', 'met.metadataparser.views.index', name='index'),
                       url(r'^met/', include('met.metadataparser.urls')),

                       # Uncomment the admin/doc line below to enable admin documentation:
                       # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

                       url(r'^about/$', TemplateView.as_view(template_name='about.html'), name='about'),
                       url(r'^saml2/', include('djangosaml2.urls')),
                       url(r'^test/', 'djangosaml2.views.echo_attributes'),
                       url(r'^admin/', include(admin.site.urls)),

                       url(r'^error403.html$', 'met.portal.views.error403'),
                       url(r'^error404.html$', 'met.portal.views.error404'),
                       url(r'^error500.html$', 'met.portal.views.error500'),
                       )

if settings.PROFILE:
    urlpatterns += patterns('', url(r'^silk/',
                                    include('silk.urls', namespace='silk')))

handler403 = 'met.portal.views.error403'
handler404 = 'met.portal.views.error404'
handler500 = 'met.portal.views.error500'

if settings.DEBUG:
    from django.views.static import serve
    _media_url = settings.MEDIA_URL
    if _media_url.startswith('/'):
        _media_url = _media_url[1:]
        urlpatterns += patterns('',
                                (r'^%s(?P<path>.*)$' % _media_url,
                                 serve,
                                 {'document_root': settings.MEDIA_ROOT}))
    del(_media_url, serve)
