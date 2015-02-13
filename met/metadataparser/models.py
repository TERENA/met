#################################################################
# MET v2 Metadate Explorer Tool
#
# This Software is Open Source. See License: https://github.com/TERENA/met/blob/master/LICENSE.md
# Copyright (c) 2012, TERENA All rights reserved.
#
# This Software is based on MET v1 developed for TERENA by Yaco Sistemas, http://www.yaco.es/
# MET v2 was developed for TERENA by Tamim Ziai, DAASI International GmbH, http://www.daasi.de
#########################################################################################

from os import path
import requests
from urlparse import urlsplit, urlparse
from urllib import quote_plus
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.cache import get_cache
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Count
from django.db.models.signals import pre_save
from django.db.models.query import QuerySet
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from met.metadataparser.utils import compare_filecontents
from met.metadataparser.xmlparser import MetadataParser, DESCRIPTOR_TYPES_DISPLAY
from met.metadataparser.templatetags import attributemap


TOP_LENGTH = getattr(settings, "TOP_LENGTH", 5)
stats = getattr(settings, "STATS")

def update_obj(mobj, obj, attrs=None):
    for_attrs = attrs or getattr(mobj, 'all_attrs', [])
    for attrb in attrs or for_attrs:
        if (getattr(mobj, attrb, None) and
            getattr(obj, attrb, None) and
            getattr(mobj, attrb) != getattr(obj, attrb)):
            setattr(obj, attrb,  getattr(mobj, attrb))


class Base(models.Model):
    file_url = models.URLField(verbose_name='Metadata url',
                               blank=True, null=True,
                               help_text=_(u'Url to fetch metadata file'))
    file = models.FileField(upload_to='metadata', blank=True, null=True,
                            verbose_name=_(u'metadata xml file'),
                            help_text=_("if url is set, metadata url will be "
                                        "fetched and replace file value"))
    file_id = models.CharField(blank=True, null=True, max_length=500,
                               verbose_name=_(u'File ID'))

    editor_users = models.ManyToManyField(User, null=True, blank=True,
                                          verbose_name=_('editor users'))

    class Meta:
        abstract = True

    class XmlError(Exception):
        pass

    def __unicode__(self):
        return self.url or u"Metadata %s" % self.id

    def load_file(self):
        """Only load file and parse it, don't create/update any objects"""
        if not self.file:
            return None
        metadata = MetadataParser(filename=self.file.path)
        return metadata

    def fetch_metadata_file(self):
        req = requests.get(self.file_url)
        if req.ok:
            req.raise_for_status()
        parsed_url = urlsplit(self.file_url)
        if self.file:
            self.file.seek(0)
            original_file_content = self.file.read()
            if compare_filecontents(original_file_content, req.content):
                return

        filename = path.basename(parsed_url.path)
        self.file.save(filename, ContentFile(req.content), save=False)

    def process_metadata(self):
        raise NotImplemented()


class XmlDescriptionError(Exception):
    pass


class Federation(Base):

    name = models.CharField(blank=False, null=False, max_length=200,
                            unique=True, verbose_name=_(u'Name'))

    type = models.CharField(blank=True, null=True, max_length=100,
                            unique=False, verbose_name=_(u'Type'))

    url = models.URLField(verbose_name='Federation url',
                          blank=True, null=True)

    free_schedule_url = models.URLField(verbose_name='Free schedule url',
                          blank=True, null=True)

    logo = models.ImageField(upload_to='federation_logo', blank=True,
                             null=True, verbose_name=_(u'Federation logo'))
    is_interfederation = models.BooleanField(default=False, db_index=True,
                                         verbose_name=_(u'Is interfederation'))
    slug = models.SlugField(max_length=200, unique=True)

    @property
    def _metadata(self):
        if not hasattr(self, '_metadata_cache'):
            self._metadata_cache = self.load_file()
        return self._metadata_cache

    def __unicode__(self):
        return self.name

    def get_entity_metadata(self, entityid):
        return self._metadata.get_entity(entityid)

    def get_entity(self, entityid):
        return self.entity_set.get(entityid=entityid)

    def process_metadata(self):
        metadata = self.load_file()
        if (self.file_id and metadata.file_id and
                metadata.file_id == self.file_id):
            return
        else:
            self.file_id = metadata.file_id

        if not metadata:
            return
        if not metadata.is_federation:
            raise XmlDescriptionError("XML Haven't federation form")

        update_obj(metadata.get_federation(), self)

    def process_metadata_entities(self, request=None, federation_slug=None, timestamp=timezone.now()):
        entities_from_xml = self._metadata.get_entities()

        for entity in self.entity_set.all():
            """Remove entity relation if does not exist in metadata"""
            if not self._metadata.entity_exist(entity.entityid):
                self.entity_set.remove(entity)
                if request and not entity.federations.exists():
                    messages.warning(request,
                        mark_safe(_("Orphan entity: <a href='%s'>%s</a>" %
                                (entity.get_absolute_url(), entity.entityid))))

        if request and federation_slug:
            request.session['%s_num_entities' % federation_slug] = len(entities_from_xml)
            request.session['%s_cur_entities' % federation_slug] = 0
            request.session['%s_process_done' % federation_slug] = False
            request.session.save()

        for m_id in entities_from_xml:
            if request and federation_slug:
                request.session['%s_cur_entities' % federation_slug] += 1
                request.session.save()

            try:
                entity = self.get_entity(entityid=m_id)
            except Entity.DoesNotExist:
                try:
                    entity = Entity.objects.get(entityid=m_id)
                    self.entity_set.add(entity)
                except Entity.DoesNotExist:
                    entity = self.entity_set.create(entityid=m_id)
            entity.process_metadata(self._metadata.get_entity(m_id))

        if request and federation_slug:
            request.session['%s_process_done' % federation_slug] = True
            request.session.save()

        for feature in stats['features'].keys():
            fun = getattr(self, 'get_%s' %feature, None)

            if callable(fun):
                stat = EntityStat()
                stat.feature = feature
                stat.time = timestamp
                stat.federation = self
                stat.value = fun(stats['features'][feature])
            
                stat.save()
            
    def get_absolute_url(self):
        return reverse('federation_view', args=[self.slug])
    
    def get_sp(self, xml_name):
        return self.entity_set.all().filter(types=EntityType.objects.get(xmlname=xml_name)).count()

    def get_idp(self, xml_name):
        return self.entity_set.all().filter(types=EntityType.objects.get(xmlname=xml_name)).count()

    def get_sp_saml1(self, xml_name):
        return self.get_stat_protocol(xml_name, 'SPSSODescriptor')

    def get_sp_saml2(self, xml_name):
        return self.get_stat_protocol(xml_name, 'SPSSODescriptor')

    def get_sp_shib1(self, xml_name):
        return self.get_stat_protocol(xml_name, 'SPSSODescriptor')

    def get_idp_saml1(self, xml_name):
        return self.get_stat_protocol(xml_name, 'IDPSSODescriptor')

    def get_idp_saml2(self, xml_name):
        return self.get_stat_protocol(xml_name, 'IDPSSODescriptor')

    def get_idp_shib1(self, xml_name):
        return self.get_stat_protocol(xml_name, 'IDPSSODescriptor')

    def get_stat_protocol(self, xml_name, service_type):
        count = 0
        for entity in self.entity_set.all().filter(types=EntityType.objects.get(xmlname=service_type)):
#             if Entity.READABLE_PROTOCOLS.has_key(xml_name) and entity.protocols and Entity.READABLE_PROTOCOLS[xml_name] in entity.display_protocols():
            if Entity.READABLE_PROTOCOLS.has_key(xml_name) and Entity.READABLE_PROTOCOLS[xml_name] in entity.display_protocols(self):
                count += 1
            
        return count

    def can_edit(self, user, delete):
        permission = 'delete_federation' if delete else 'change_federation'
        if user.has_perm('metadataparser.%s' % permission):
            if user in self.editor_users.all():
                return True
        return False


class EntityQuerySet(QuerySet):
    def iterator(self):
        cached_federations = {}
        for entity in super(EntityQuerySet, self).iterator():
            if not entity.file:
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
    def get_queryset(self):
        return EntityQuerySet(self.model, using=self._db)


class EntityType(models.Model):
    name = models.CharField(blank=False, max_length=20, unique=True,
                            verbose_name=_(u'Name'), db_index=True)
    xmlname = models.CharField(blank=False, max_length=20, unique=True,
                            verbose_name=_(u'Name in XML'), db_index=True)

    def __unicode__(self):
        return self.name


class Entity(Base):

    READABLE_PROTOCOLS = {
        'urn:oasis:names:tc:SAML:1.1:protocol': 'SAML 1.1',
        'urn:oasis:names:tc:SAML:2.0:protocol': 'SAML 2.0',
        'urn:mace:shibboleth:1.0': 'Shiboleth 1.0',
    }

    entityid = models.CharField(blank=False, max_length=200, unique=True,
                                verbose_name=_(u'EntityID'), db_index=True)
    federations = models.ManyToManyField(Federation,
                                         verbose_name=_(u'Federations'))

    types = models.ManyToManyField(EntityType, verbose_name=_(u'Type'))

    objects = models.Manager()
    longlist = EntityManager()

    @property
    def registration_authority(self):
        return self._get_property('registration_authority')

    @property
    def registration_instant(self):
        return datetime.strptime(self._get_property('registration_instant'), '%Y-%m-%dT%H:%M:%SZ')

    @property
    def protocols(self):
        return ' '.join(self._get_property('protocols'))

    @property
    def languages(self):
        return ' '.join(self._get_property('languages'))

    @property
    def scopes(self):
        return ' '.join(self._get_property('scopes'))

    @property
    def attributes(self):
        attributes = self._get_property('attr_requested')
        if not attributes:
            return ''
        return ' '.join(attributes['required'])

    @property
    def attributes_options(self):
        attributes = self._get_property('attr_requested')
        if not attributes:
            return ''
        return ' '.join(attributes['optional'])

    @property
    def organization(self):
        organization = self._get_property('organization')

        names = []
        urls = []
        displayNames = []

        vals = []
        for lang, data in organization.items():
            data['lang'] = lang
            vals.append(data)

        return vals

    @property
    def name(self):
        return self._get_property('displayName')

    @property
    def federationsCount(self):
        return str(self.federations.all().count())
        
    @property
    def description(self):
        return self._get_property('description')

    @property
    def infoUrl(self):
        return self._get_property('infoUrl')

    @property
    def privacyUrl(self):
        return self._get_property('privacyUrl')

    @property
    def xml(self):
         return self._get_property('xml')

    @property
    def xml_types(self):
         return self._get_property('entity_types')

    def display_protocols(self, federation = None):
        protocols = []
        if self._get_property('protocols', federation):
            for proto in self._get_property('protocols', federation):
                protocols.append(self.READABLE_PROTOCOLS.get(proto, proto))

        return protocols

    def display_attributes(self):
        attributes = {}
        for attr in self.attributes.split(' '):
            oid = attr.replace('urn:oid:', '')
            if attr in attributemap.MAP['fro']:
                attributes[oid] = attributemap.MAP['fro'][attr]
            else:
                attributes[oid] = attr
        return attributes

    def display_attributes_optional(self):
        attributes = {}
        for attr in self.attributes_optional.split(' '):
            oid = attr.replace('urn:oid:', '')
            if attr in attributemap.MAP['fro']:
                attributes[oid] = attributemap.MAP['fro'][attr]
            else:
                attributes[oid] = attr
        return attributes

    @property
    def contacts(self):
        contacts = []
        for cur_contact in self._get_property('contacts'):
            if cur_contact['name'] and cur_contact['surname']:
                contact_name = '%s %s' % (cur_contact['name'], cur_contact['surname'])
            elif cur_contact['name']:
                contact_name = cur_contact['name']
            elif cur_contact['surname']:
                contact_name = cur_contact['surname']
            else:
                contact_name = urlparse(cur_contact['email']).path.partition('?')[0]
            c_type = 'undefined'
            if cur_contact['type']:
                c_type = cur_contact['type']
            contacts.append({ 'name': contact_name, 'email': cur_contact['email'], 'type': c_type })
        return contacts

    @property
    def logos(self):
        logos = []
        for cur_logo in self._get_property('logos'):
            cur_logo['external'] = True
            logos.append(cur_logo)

        return logos

    class Meta:
        verbose_name = _(u'Entity')
        verbose_name_plural = _(u'Entities')

    def __unicode__(self):
        return self.entityid

    def load_metadata(self, federation=None, entity_data=None):
        if not hasattr(self, '_entity_cached'):
            if self.file:
                self._entity_cached = self.load_file().get_entity(self.entityid)
            elif federation:
                self._entity_cached = federation.get_entity_metadata(self.entityid)
            elif entity_data:
                self._entity_cached = entity_data
            else:
                for federation in self.federations.all():
                    try:
                        entity_cached = federation.get_entity_metadata(self.entityid)
                        if entity_cached and hasattr(self, '_entity_cached'):
                            self._entity_cached.update(entity_cached)
                        else:
                            self._entity_cached = entity_cached
                    except ValueError:
                        continue
            if not hasattr(self, '_entity_cached'):
                raise ValueError("Can't find entity metadata")

    def _get_property(self, prop, federation = None):
        try:
            self.load_metadata(federation)
        except ValueError:
            return None
        if hasattr(self, '_entity_cached'):
            return self._entity_cached.get(prop, None)
        else:
            raise ValueError("Not metadata loaded")

    def process_metadata(self, entity_data=None):
        if not entity_data:
            self.load_metadata()

        if self.entityid != entity_data.get('entityid'):
            raise ValueError("EntityID is not the same")

        self._entity_cached = entity_data
        if self.xml_types:
            for etype in self.xml_types:
                try:
                    entity_type = EntityType.objects.get(xmlname=etype)
                except EntityType.DoesNotExist:
                    entity_type = EntityType.objects.create(xmlname=etype,
                                              name=DESCRIPTOR_TYPES_DISPLAY[etype])
                if entity_type not in self.types.all():
                    self.types.add(entity_type)

    def to_dict(self):
        self.load_metadata()

        entity = self._entity_cached.copy()
        entity["types"] = [(unicode(f)) for f in self.types.all()]
        entity["federations"] = [{u"name": unicode(f), u"url": f.get_absolute_url()}
                                    for f in self.federations.all()]

        if self.registration_authority:
            entity["registration_authority"] = self.registration_authority
        if self.registration_instant:
            entity["registration_instant"] = datetime.strptime(self.registration_instant, '%Y-%m-%dT%H:%M%SZ')

        if "file_id" in entity.keys():
            del entity["file_id"]
        if "entity_types" in entity.keys():
            del entity["entity_types"]

        return entity

    @classmethod
    def get_most_federated_entities(self, maxlength=TOP_LENGTH, cache_expire=None):
        entities = None
        if cache_expire:
            cache = get_cache("default")
            entities = cache.get("most_federated_entities")

        if not entities or entities.count() != maxlength:
            # Entities with count how many federations belongs to, and sorted by most first
            entities = Entity.objects.all().annotate(
                                 federationslength=Count("federations")).order_by("-federationslength")[:maxlength]

        if cache_expire:
            cache = get_cache("default")
            cache.set("most_federated_entities", entities, cache_expire)

        return entities

    def get_absolute_url(self):
        return reverse('entity_view', args=[quote_plus(self.entityid)])

    def can_edit(self, user, delete):
        permission = 'delete_entity' if delete else 'change_entity'
        if user.has_perm('metadataparser.%s' % permission):
            if user in self.editor_users.all():
                return True

        for federation in self.federations.all():
            if federation.can_edit(user, False):
                return True

        return False

class EntityInfo(models.Model):
    info_type = models.CharField(blank=True, max_length=30,
                                verbose_name=_(u'Info Type'), db_index=True)
    language = models.CharField(blank=True, null=True, max_length=10,
                                verbose_name=_(u'Language'))
    value = models.CharField(blank=False, max_length=100000,
                                verbose_name=_(u'Info Value'))
    width = models.PositiveSmallIntegerField(null=True, default=0,
                                verbose_name=_(u'Width'))
    height = models.PositiveSmallIntegerField(null=True, default=0,
                                verbose_name=_(u'Height'))

    entity = models.ForeignKey(Entity, blank=False,
                                verbose_name=_('Entity'))

    def __unicode__(self):
        return "[%s:%s] %s" % (self.info_type, self.language, self.value)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            for field in ['info_type', 'language', 'value', 'width', 'height']:
                if self.__dict__[field] != other.__dict__[field]:
                    return False
            return True
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

class EntityContact(models.Model):
    contact_type = models.CharField(blank=True, max_length=30,
                                verbose_name=_(u'Contact Type'), db_index=True)
    name = models.CharField(blank=True, null=True, max_length=200,
                                verbose_name=_(u'Name'))
    surname = models.CharField(blank=True, null=True, max_length=200,
                                verbose_name=_(u'Surname'))
    email = models.CharField(blank=False, max_length=500,
                                verbose_name=_(u'Email'))

    entity = models.ForeignKey(Entity, blank=False,
                                verbose_name=_('Entity'))

    def __unicode__(self):
        return "[%s] %s %s <%s>" % (self.contact_type, self.name, self.surname, self.email)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            for field in ['contact_type', 'name', 'surname', 'email']:
                if self.__dict__[field] != other.__dict__[field]:
                    return False
            return True
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

class EntityStat(models.Model):
    time = models.DateTimeField(blank=False, null=False, 
                           verbose_name=_(u'Metadata time stamp'))
    feature = models.CharField(max_length=100, blank=False, null=False, db_index=True,
                           verbose_name=(u'Feature name'))

    value = models.PositiveIntegerField(max_length=100, blank=False, null=False,
                           verbose_name=(u'Feature value'))

    federation = models.ForeignKey(Federation, blank = False,
                                         verbose_name=_(u'Federations'))

    def __unicode__(self):
        return self.feature


class Dummy(models.Model):
    pass


@receiver(pre_save, sender=Federation, dispatch_uid='federation_pre_save')
def federation_pre_save(sender, instance, **kwargs):
    # Skip pre_save if only file name is saved 
    if kwargs.has_key('update_fields') and kwargs['update_fields'] == set(['file']):
        return

    if instance.file_url:
        instance.fetch_metadata_file()
    if instance.name:
        instance.slug = slugify(unicode(instance))[:200]


@receiver(pre_save, sender=Entity, dispatch_uid='entity_pre_save')
def entity_pre_save(sender, instance, **kwargs):
    if instance.file_url:
        instance.fetch_metadata_file()
        instance.process_metadata()
