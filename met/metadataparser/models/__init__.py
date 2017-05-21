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
#########################################################################################

from django.conf import settings

from base import Dummy
from federation import Federation, FEDERATION_TYPES
from entity import Entity
from entity_type import EntityType
from entity_category import EntityCategory
from entity_federations import Entity_Federations
from entity_stat import EntityStat

TOP_LENGTH = getattr(settings, "TOP_LENGTH", 5)

__all__ = [ 'TOP_LENGTH',
            'FEDERATION_TYPES',
            'Federation',
            'EntityType',
            'EntityCategory',
            'Entity',
            'Entity_Federations',
            'EntityStat',
            'Dummy']
