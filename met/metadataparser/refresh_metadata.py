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

import logging
from datetime import datetime

from django.conf import settings
from django.db.models import Count

from met.metadataparser.utils import send_mail, send_slack
from met.metadataparser.models import Federation, Entity, EntityCategory

if settings.PROFILE:
    from silk.profiling.profiler import silk_profile as profile
else:
    from met.metadataparser.templatetags.decorators import noop_decorator as profile


def _send_message_via_email_and_slack(error_msg, federation, logger=None):
    mail_config_dict = getattr(settings, "MAIL_CONFIG")
    try:
        subject = mail_config_dict['refresh_subject'] % federation
        from_address = mail_config_dict['from_email_address']
        send_mail(from_address, subject, '%s' % error_msg)
        send_slack(f'{subject}, - {error_msg}')
    except Exception as errorMessage:
        log('Message could not be posted successfully: %s' %
            errorMessage, logger, logging.ERROR)


def _fetch_new_metadata_file(federation, logger):
    try:
        changed = federation.fetch_metadata_file(federation.slug)
        return None, changed
    except Exception as errorMessage:
        log('%s' % errorMessage, logger, logging.ERROR)
        return "%s" % errorMessage, False


def refresh(fed_name=None, force_refresh=False, logger=None):
    log('Starting refreshing metadata ...', logger, logging.INFO)

    federations = Federation.objects.all()
    federations.prefetch_related('etypes', 'federations')
    #TODO prefetch related, add federations->entity_categories

    for federation in federations:
        if fed_name and federation.slug != fed_name:
            continue

        error_msg = None
        try:
            log('[%s] Refreshing metadata ...' %
                federation, logger, logging.INFO)
            error_msg, data_changed = _fetch_new_metadata_file(
                federation, logger)

            if not error_msg and (force_refresh or data_changed):
                log('[%s] Updating database ...' %
                    federation, logger, logging.INFO)

                log('[%s] Updating federation ...' %
                    federation, logger, logging.DEBUG)
                federation.process_metadata()
                federation.save()

                log('[%s] Updating federation entities ...' %
                    federation, logger, logging.DEBUG)
                removed, updated = federation.process_metadata_entities()
                log('[%s] Removed %s old entities and updated %s entities.' %
                    (federation, removed, updated), logger, logging.INFO)

                log('[%s] Updating federation file and metadata_data...' %
                    federation, logger, logging.DEBUG)
                federation.metadata_update = datetime.now()
                federation.save(update_fields=['file', 'metadata_update'])
                log('[{}] Federation update time modified with {}'.format(
                    federation, federation.metadata_update), logger, logging.INFO)

            log('[%s] Updating federation statistics ...' %
                federation, logger, logging.DEBUG)
            (computed, not_computed) = federation.compute_new_stats()
            log('[%s] Computed statistics: %s' %
                (federation, computed), logger, logging.DEBUG)
            log('[%s] NOT Computed statistics: %s' %
                (federation, not_computed), logger, logging.DEBUG)

        except Exception as e:
            if error_msg is None:
                error_msg = '%s' % e
            error_msg = f'{error_msg}\n{e}'

        finally:
            if error_msg:
                log('Sending following error via email: %s' %
                    error_msg, logger, logging.INFO)
                _send_message_via_email_and_slack(
                    error_msg, federation, logger)

    try:
        log('Removing entity categories with no entity associated...', logger, logging.INFO)
        EntityCategory.objects.all().annotate(entitylength=Count("entity_federations")
                                              ).filter(entitylength__lte=0).delete()
    except Exception as errorMessage:
        log('Error: %s' % errorMessage, logger, logging.ERROR)

    try:
        log('Removing entities with no federation associated...', logger, logging.INFO)
        Entity.objects.all().annotate(federationslength=Count("federations")
                                      ).filter(federationslength__lte=0).delete()
    except Exception as errorMessage:
        log('Error: %s' % errorMessage, logger, logging.ERROR)

    log('Refreshing metadata terminated.', logger, logging.INFO)


def log(message, logger=None, severity=logging.INFO):
    if logger:
        logger.log(severity, message)
    else:
        print(message)
