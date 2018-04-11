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

from django.conf.urls import patterns, url

comments_and_proposals = False

urlpatterns = patterns('met.metadataparser.views',
                       url(r'^federation/add/$', 'federation_edit',
                           name='federation_add'),
                       url(r'^federation/(?P<federation_slug>[-\w]+)/entityupdate_progress/$',
                           'entityupdate_progress', name='entityupdate_progress'),
                       url(r'^federation/(?P<federation_slug>[-\w]+)/federation_update_entities/$',
                           'federation_update_entities', name='federation_update_entities'),
                       url(r'^federation/(?P<federation_slug>[-\w]+)/edit/$', 'federation_edit',
                           name='federation_edit'),
                       url(r'^federation/(?P<federation_slug>[-\w]+)/delete/$', 'federation_delete',
                           name='federation_delete'),
                       url(r'^federation/(?P<federation_slug>[-\w]+)/$', 'federation_view',
                           name='federation_view'),
                       url(r'^federation/(?P<federation_slug>[-\w]+)/entityadd/$', 'entity_edit',
                           name='entity_add'),

                       url(r'^federation/(?P<federation_slug>[-\w]+)/charts/$', 'federation_charts',
                           name='federation_charts'),
                       url(r'^logout/$', 'met_logout', name='logout'),

                       url(r'^entity/(?P<entity_id>.+)/edit/$',
                           'entity_edit', name='entity_edit'),
                       url(r'^entity/(?P<entity_id>.+)/delete/$',
                           'entity_delete', name='entity_delete'),

                       url(r'^entity/(?P<entityid>.+)/$',
                           'entity_view', name='entity_view'),

                       url(r'^search_service/$', 'search_service',
                           name='search_service'),
                       url(r'^search_entities/$', 'search_entities',
                           name='search_entities'),

                       url(r'^most_federated_entities/$', 'most_federated_entities',
                           name='most_federated_entities'),
                       url(r'^show_less_entries/$', 'decrement_current_toplength',
                           name='show_less_entries'),
                       url(r'^show_more_entries/$', 'increment_current_toplength',
                           name='show_more_entries'),

                       )

if comments_and_proposals:
    urlpatterns += patterns('met.metadataparser.views',
                            url(r'^entity/(?P<entity_id>.+)/comment/$',
                                'entity_comment', name='entity_comment'),
                            url(r'^entity/(?P<entity_id>.+)/proposal/$',
                                'entity_proposal', name='entity_proposal'),
                            )
