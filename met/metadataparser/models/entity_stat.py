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

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

stats = getattr(settings, "STATS")


class EntityStat(models.Model):
    """
    Model describing a statistic information about an entity.
    """

    time = models.DateTimeField(blank=False, null=False,
                                verbose_name=_(u'Metadata time stamp'))

    feature = models.CharField(max_length=100, blank=False, null=False, db_index=True,
                               verbose_name=_(u'Feature name'))

    value = models.PositiveIntegerField(blank=False, null=False,
                                        verbose_name=_(u'Feature value'))

    federation = models.ForeignKey('Federation', blank=False,
                                   verbose_name=_(u'Federations'))

    def __unicode__(self):
        return self.feature
