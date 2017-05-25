##########################################################################
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

from django.db import models
from django.utils.translation import ugettext_lazy as _


class EntityCategory(models.Model):
    """
    Description of an entity category as defined in SAML here:
    http://macedir.org/draft-macedir-entity-category-00.html
    """
    category_id = models.CharField(verbose_name='Entity category ID',
                                   max_length=1000,
                                   blank=False, null=False,
                                   help_text=_(u'The ID of the entity category'))

    name = models.CharField(verbose_name='Entity category name',
                            max_length=1000,
                            blank=True, null=True,
                            help_text=_(u'The name of the entity category'))

    def __unicode__(self):
        return self.name or self.category_id
