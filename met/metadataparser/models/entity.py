#################################################################
#
# This Software is Open Source. See License: https://github.com/TERENA/met/blob/master/LICENSE.md
# Copyright (c) 2012, TERENA All rights reserved.
#
# This Software is based on MET v1 developed for TERENA by Yaco Sistemas, http://www.yaco.es/
# MET v2 was developed for TERENA by Tamim Ziai, DAASI International GmbH, http://www.daasi.de
# Current version of MET has been revised for performance improvements by Andrea Biancini,
# Consortium GARR, http://www.garr.it
##########################################################################

import simplejson as json

from urllib.parse import urlparse
from urllib.parse import quote_plus
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Count
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _

from met.metadataparser.templatetags import attributemap
from met.metadataparser.xmlparser import DESCRIPTOR_TYPES_DISPLAY

from met.metadataparser.models.base import JSONField, Base
from met.metadataparser.models.entity_type import EntityType
from met.metadataparser.models.entity_federations import Entity_Federations

TOP_LENGTH = getattr(settings, "TOP_LENGTH", 5)


def update_obj(mobj, obj, attrs=None):
    for_attrs = attrs or getattr(mobj, 'all_attrs', [])
    for attrb in attrs or for_attrs:
        if (getattr(mobj, attrb, None) and
            getattr(obj, attrb, None) and
                getattr(mobj, attrb) != getattr(obj, attrb)):
            setattr(obj, attrb, getattr(mobj, attrb))


class EntityQuerySet(QuerySet):
    """
    Entity queryset.
    """

    def iterator(self):
        cached_federations = {}
        for entity in super().iterator():
            if entity.file:
                continue

            federations = entity.federations.all()
            if federations:
                federation = federations[0]
            else:
                raise ValueError("Can't find entity metadata")

            for federation in federations:
                if not federation.id in cached_federations:
                    cached_federations[federation.id] = federation

                cached_federation = cached_federations[federation.id]
                try:
                    entity.load_metadata(federation=cached_federation)
                except ValueError:
                    # Allow entity in federation but not in federation file
                    continue
                else:
                    break

            yield entity


class EntityManager(models.Manager):
    """
    Manager for entities.
    """

    def get_queryset(self):
        return EntityQuerySet(self.model, using=self._db)


class Entity(Base):
    """
    Model describin a federation entity (IdP, SP or AA).
    """

    READABLE_PROTOCOLS = {
        'urn:oasis:names:tc:SAML:1.1:protocol': 'SAML 1.1',
        'urn:oasis:names:tc:SAML:2.0:protocol': 'SAML 2.0',
        'urn:mace:shibboleth:1.0': 'Shiboleth 1.0',
    }

    entityid = models.CharField(blank=False, max_length=200, unique=True,
                                verbose_name=_('EntityID'), db_index=True)

    federations = models.ManyToManyField('Federation', through='Entity_Federations',
                                         verbose_name=_('Federations'))

    types = models.ManyToManyField('EntityType', verbose_name=_('Type'))

    name = JSONField(blank=True, null=True, max_length=2000,
                     verbose_name=_('Display Name'))

    certstats = models.CharField(blank=True, null=True, max_length=200,
                                 unique=False, verbose_name=_('Certificate Stats'))

    _display_protocols = models.CharField(blank=True, null=True, max_length=300,
                                          unique=False, verbose_name=_('Display Protocols'))

    objects = models.Manager()

    longlist = EntityManager()

    curfed = None

    @property
    def certificates(self):
        return json.loads(self.certstats)

    @property
    def registration_authority_xml(self):
        return self._get_property('registration_authority')

    @property
    def registration_policy(self):
        return self._get_property('registration_policy')

    @property
    def registration_instant(self):
        reginstant = self._get_property('registration_instant')
        if reginstant is None:
            return None
        reginstant = "%sZ" % reginstant[0:19]
        return datetime.strptime(reginstant, '%Y-%m-%dT%H:%M:%SZ')

    @property
    def protocols(self):
        try:
            return ' '.join(self._get_property('protocols'))
        except Exception:
            return ''

    @property
    def languages(self):
        try:
            return ' '.join(self._get_property('languages'))
        except Exception:
            return ''

    @property
    def scopes(self):
        try:
            return ' '.join(self._get_property('scopes'))
        except Exception:
            return ''

    @property
    def attributes(self):
        try:
            attributes = self._get_property('attr_requested')
            if not attributes:
                return []
            return attributes['required']
        except Exception:
            return []

    @property
    def attributes_optional(self):
        try:
            attributes = self._get_property('attr_requested')
            if not attributes:
                return []
            return attributes['optional']
        except Exception:
            return []

    @property
    def organization(self):
        organization = self._get_property('organization')
        if not organization:
            return []

        vals = []
        for lang, data in organization.items():
            data['lang'] = lang
            vals.append(data)

        return vals

    @property
    def display_name(self):
        try:
            return self._get_property('displayName')
        except Exception:
            return ''

    @property
    def federations_count(self):
        try:
            return str(self.federations.all().count())
        except Exception:
            return ''

    @property
    def description(self):
        try:
            return self._get_property('description')
        except Exception:
            return ''

    @property
    def info_url(self):
        try:
            return self._get_property('infoUrl')
        except Exception:
            return ''

    @property
    def privacy_url(self):
        try:
            return self._get_property('privacyUrl')
        except Exception:
            return ''

    @property
    def xml(self):
        try:
            return self._get_property('xml')
        except Exception:
            return ''

    @property
    def xml_types(self):
        try:
            return self._get_property('entity_types')
        except Exception:
            return []

    @property
    def entity_categories(self):
        if self.curfed:
            efed = Entity_Federations.objects.get_or_create(federation=self.curfed, entity=self)[0]
            return efed.entity_categories
        return None

    @property
    def xml_categories(self):
        try:
            return self._get_property('entity_categories')
        except Exception:
            return []

    @property
    def display_protocols(self):
        protocols = []

        xml_protocols = self.protocols
        if xml_protocols:
            for proto in xml_protocols.split(' '):
                protocols.append(self.READABLE_PROTOCOLS.get(proto, proto))

        return protocols

    def display_attributes(self):
        attributes = {}
        for [attr, friendly] in self.attributes:
            if friendly:
                attributes[attr] = friendly
            elif attr in attributemap.MAP['fro']:
                attributes[attr] = attributemap.MAP['fro'][attr]
            else:
                attributes[attr] = '?'
        return attributes

    def display_attributes_optional(self):
        attributes = {}
        for [attr, friendly] in self.attributes_optional:
            if friendly:
                attributes[attr] = friendly
            elif attr in attributemap.MAP['fro']:
                attributes[attr] = attributemap.MAP['fro'][attr]
            else:
                attributes[attr] = '?'
        return attributes

    @property
    def contacts(self):
        contacts = []
        for cur_contact in self._get_property('contacts'):
            if cur_contact['name'] and cur_contact['surname']:
                contact_name = '{} {}'.format(
                    cur_contact['name'], cur_contact['surname'])
            elif cur_contact['name']:
                contact_name = cur_contact['name']
            elif cur_contact['surname']:
                contact_name = cur_contact['surname']
            else:
                contact_name = urlparse(
                    cur_contact['email']).path.partition('?')[0]
            c_type = 'undefined'
            if cur_contact['type']:
                c_type = cur_contact['type']
            contacts.append(
                {'name': contact_name, 'email': cur_contact['email'], 'type': c_type})
        return contacts

    @property
    def logos(self):
        logos = []
        for cur_logo in self._get_property('logos'):
            cur_logo['external'] = True
            logos.append(cur_logo)

        return logos

    class Meta:
        verbose_name = _('Entity')
        verbose_name_plural = _('Entities')

    def __unicode__(self):
        return self.entityid

    def load_metadata(self, federation=None, entity_data=None):
        if hasattr(self, '_entity_cached'):
            return

        if self.file:
            self._entity_cached = self.load_file().get_entity(self.entityid)
        elif federation:
            self._entity_cached = federation.get_entity_metadata(self.entityid)
        elif entity_data:
            self._entity_cached = entity_data
        else:
            right_fed = None
            first_fed = None
            for fed in self.federations.all():
                if fed.registration_authority == self.registration_authority:
                    right_fed = fed
                if first_fed is None:
                    first_fed = fed

            if right_fed is not None:
                entity_cached = right_fed.get_entity_metadata(self.entityid)
                self._entity_cached = entity_cached
            else:
                entity_cached = first_fed.get_entity_metadata(self.entityid)
                self._entity_cached = entity_cached

        if not hasattr(self, '_entity_cached'):
            raise ValueError("Can't find entity metadata")

    def _get_property(self, prop, federation=None):
        try:
            self.load_metadata(federation or self.curfed)
        except ValueError:
            return None

        if hasattr(self, '_entity_cached'):
            return self._entity_cached.get(prop, None)
        else:
            raise ValueError("Not metadata loaded")

    def _get_or_create_etypes(self, cached_entity_types):
        entity_types = []
        cur_cached_types = [t.xmlname for t in self.types.all()]
        for etype in self.xml_types:
            if etype in cur_cached_types:
                break

            if cached_entity_types is None:
                entity_type, _ = EntityType.objects.get_or_create(xmlname=etype,
                                                                  name=DESCRIPTOR_TYPES_DISPLAY[etype])
            else:
                if etype in cached_entity_types:
                    entity_type = cached_entity_types[etype]
                else:
                    entity_type = EntityType.objects.create(xmlname=etype,
                                                            name=DESCRIPTOR_TYPES_DISPLAY[etype])
            entity_types.append(entity_type)
        return entity_types

    def process_metadata(self, auto_save=True, entity_data=None, cached_entity_types=None, federation=None):
        if not entity_data:
            self.load_metadata()

        if self.entityid.lower() != entity_data.get('entityid').lower():
            raise ValueError("EntityID is not the same: {} != {}".format(
                self.entityid.lower(), entity_data.get('entityid').lower()))

        self._entity_cached = entity_data

        if self.xml_types:
            entity_types = self._get_or_create_etypes(cached_entity_types)
            if len(entity_types) > 0:
                self.types.add(*entity_types)

        newname = self._get_property('displayName')
        if newname and newname != '':
            self.name = newname

        self.certstats = self._get_property('certstats')

        newprotocols = self.protocols
        if newprotocols and newprotocols != "":
            self._display_protocols = newprotocols

        if str(self._get_property('registration_authority')) != '':
            self.registration_authority = self._get_property(
                'registration_authority')

        if auto_save:
            self.save()

    def to_dict(self):
        self.load_metadata()

        entity = self._entity_cached.copy()
        entity["types"] = [unicode(f) for f in self.types.all()]
        entity["federations"] = [{"name": unicode(f), "url": f.get_absolute_url()}
                                 for f in self.federations.all()]

        if self.registration_authority:
            entity["registration_authority"] = self.registration_authority
        if self.registration_instant:
            entity["registration_instant"] = '%s' % self.registration_instant

        if "file_id" in entity.keys():
            del entity["file_id"]
        if "entity_types" in entity.keys():
            del entity["entity_types"]

        return entity

    def display_etype(value, separator=', '):
        return separator.join([unicode(item) for item in value.all()])

    @classmethod
    def get_most_federated_entities(self, maxlength=TOP_LENGTH, cache_expire=None):
        entities = None
        if cache_expire:
            entities = cache.get("most_federated_entities")

        if not entities or len(entities) < maxlength:
            # Entities with count how many federations belongs to, and sorted
            # by most first
            ob_entities = Entity.objects.all().annotate(
                federationslength=Count("federations")).order_by("-federationslength")
            ob_entities = ob_entities.prefetch_related('types', 'federations')
            ob_entities = ob_entities[:maxlength]

            entities = []
            for entity in ob_entities:
                entities.append({
                    'entityid': entity.entityid,
                    'name': entity.name,
                    'absolute_url': entity.get_absolute_url(),
                    'types': [unicode(item) for item in entity.types.all()],
                    'federations': [(unicode(item.name), item.get_absolute_url()) for item in entity.federations.all()],
                })

        if cache_expire:
            cache.set("most_federated_entities", entities, cache_expire)

        return entities[:maxlength]

    def get_absolute_url(self):
        return reverse('entity_view', args=[quote_plus(self.entityid.encode('utf-8'))])

    def can_edit(self, user, delete):
        permission = 'delete_entity' if delete else 'change_entity'
        if user.is_superuser or (user.has_perm('metadataparser.%s' % permission) and user in self.editor_users.all()):
            return True

        for federation in self.federations.all():
            if federation.can_edit(user, False):
                return True

        return False

    def has_changed(self, entityid, name, registration_authority, certstats, display_protocols):
        if self.entityid != entityid:
            return True
        if self.name != name:
            return True
        if self.registration_authority != registration_authority:
            return True
        if self.certstats != certstats:
            return True
        if self._display_protocols != display_protocols:
            return True

        return False
