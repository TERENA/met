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

import pytz
import simplejson as json

from datetime import datetime, time, timedelta

from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Max
from django.db.models.signals import pre_save
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.dispatch import receiver
from django.template.defaultfilters import slugify

from met.metadataparser.xmlparser import MetadataParser

from met.metadataparser.models.base import Base, XmlDescriptionError
from met.metadataparser.models.entity import Entity
from met.metadataparser.models.entity_type import EntityType
from met.metadataparser.models.entity_stat import EntityStat, stats
from met.metadataparser.models.entity_category import EntityCategory
from met.metadataparser.models.entity_federations import Entity_Federations

FEDERATION_TYPES = (
    (None, ''),
    ('hub-and-spoke', 'Hub and Spoke'),
    ('mesh', 'Full Mesh'),
)


def update_obj(mobj, obj, attrs=None):
    for_attrs = attrs or getattr(mobj, 'all_attrs', [])
    for attrb in attrs or for_attrs:
        if (getattr(mobj, attrb, None) and
            getattr(obj, attrb, None) and
                getattr(mobj, attrb) != getattr(obj, attrb)):
            setattr(obj, attrb, getattr(mobj, attrb))


class Federation(Base):
    """
    Model describing an identity federation.
    """

    name = models.CharField(blank=False, null=False, max_length=200,
                            unique=True, verbose_name=_('Name'))

    type = models.CharField(blank=True, null=True, max_length=100,
                            unique=False, verbose_name=_('Type'), choices=FEDERATION_TYPES)

    url = models.URLField(verbose_name='Federation url',
                          blank=True, null=True)

    fee_schedule_url = models.URLField(verbose_name='Fee schedule url',
                                       max_length=150, blank=True, null=True)

    logo = models.ImageField(upload_to='federation_logo', blank=True,
                             null=True, verbose_name=_('Federation logo'))

    is_interfederation = models.BooleanField(default=False, db_index=True,
                                             verbose_name=_('Is interfederation'))

    slug = models.SlugField(max_length=200, unique=True)

    country = models.CharField(blank=True, null=True, max_length=100,
                               unique=False, verbose_name=_('Country'))

    metadata_update = models.DateTimeField(blank=True, null=True,
                                           unique=False, verbose_name=_('Metadata update date and time'))

    certstats = models.CharField(blank=True, null=True, max_length=200,
                                 unique=False, verbose_name=_('Certificate Stats'))

    @property
    def certificates(self):
        return json.loads(self.certstats)

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

        if self.file_id and metadata.file_id and metadata.file_id == self.file_id:
            return
        else:
            self.file_id = metadata.file_id

        if not metadata:
            return
        if not metadata.is_federation:
            raise XmlDescriptionError("XML Haven't federation form")

        update_obj(metadata.get_federation(), self)
        self.certstats = MetadataParser.get_certstats(metadata.rootelem)

    def _remove_deleted_entities(self, entities_from_xml):
        removed = 0
        for entity in self.entity_set.all():
            # Remove entity relation if does not exist in metadata
            if not entity.entityid in entities_from_xml:
                Entity_Federations.objects.filter(
                    federation=self, entity=entity).delete()
                removed += 1

        return removed

    def _get_or_create_ecategories(self, entity, cached_entity_categories):
        entity_categories = []
        efed = Entity_Federations.objects.get_or_create(federation=self, entity=entity)[0]
        cur_cached_categories = [
            t.category_id for t in efed.entity_categories.all()]
        for ecategory in entity.xml_categories:
            if ecategory in cur_cached_categories:
                break

            if cached_entity_categories is None:
                entity_category, _ = EntityCategory.objects.get_or_create(
                    category_id=ecategory)
            else:
                if ecategory in cached_entity_categories:
                    entity_category = cached_entity_categories[ecategory]
                else:
                    entity_category = EntityCategory.objects.create(
                        category_id=ecategory)
            entity_categories.append(entity_category)
        return entity_categories

    def _update_entities(self, entities_to_update, entities_to_add):
        for e in entities_to_update:
            e.save()

        for e in entities_to_add:
            membership = Entity_Federations.objects.get_or_create(federation=self, entity=e)[0]
            membership.registration_instant = e.registration_instant.date() if e.registration_instant else None

            if e.xml_categories:
                db_entity_categories = EntityCategory.objects.all()
                cached_entity_categories = {
                    entity_category.category_id: entity_category for entity_category in db_entity_categories}

                # Delete categories no more present in XML
                membership.entity_categories.clear()

                # Create all entities, if not alread in database
                entity_categories = self._get_or_create_ecategories(e, cached_entity_categories)

                # Add categories to entity
                if len(entity_categories) > 0:
                    membership.entity_categories.add(*entity_categories)
            else:
                # No categories in XML, delete eventual categorie sin DB
                membership.entity_categories.clear()

            membership.save()

    def _add_new_entities(self, entities, entities_from_xml, request, federation_slug):
        db_entity_types = EntityType.objects.all()
        cached_entity_types = {
            entity_type.xmlname: entity_type for entity_type in db_entity_types}

        entities_to_add = []
        entities_to_update = []

        for m_id in entities_from_xml:
            if request and federation_slug:
                request.session['%s_cur_entities' % federation_slug] += 1
                request.session.save()

            created = False
            if m_id in entities:
                entity = entities[m_id]
            else:
                entity, created = Entity.objects.get_or_create(entityid=m_id)

            entityid = entity.entityid
            name = entity.name
            registration_authority = entity.registration_authority
            certstats = entity.certstats
            display_protocols = entity._display_protocols

            entity_from_xml = self._metadata.get_entity(m_id, False)
            entity.process_metadata(False, entity_from_xml, cached_entity_types, self)

            if created or entity.has_changed(entityid, name, registration_authority, certstats, display_protocols):
                entities_to_update.append(entity)

            entities_to_add.append(entity)

        self._update_entities(entities_to_update, entities_to_add)
        return len(entities_to_update)

    @staticmethod
    def _daterange(start_date, end_date):
        for n in range(int((end_date - start_date).days + 1)):
            yield start_date + timedelta(n)

    def compute_new_stats(self):
        if not self._metadata: return ([], [])
        entities_from_xml = self._metadata.get_entities()

        entities = Entity.objects.filter(entityid__in=entities_from_xml)
        entities = entities.prefetch_related('types')
        Entity_Federations.objects.filter(federation=self)

        try:
            first_date = EntityStat.objects.filter(
                federation=self).aggregate(Max('time'))['time__max']
            if not first_date:
                raise Exception('Not able to find statistical data in the DB.')
        except Exception:
            first_date = datetime(2010, 1, 1)
            first_date = pytz.utc.localize(first_date)

        for curtimestamp in self._daterange(first_date, timezone.now() - timedelta(1)):
            computed = {}
            not_computed = []
            entity_stats = []
            for feature in stats['features'].keys():
                fun = getattr(self, 'get_%s' % feature, None)

                if callable(fun):
                    stat = EntityStat()
                    stat.feature = feature
                    stat.time = curtimestamp
                    stat.federation = self
                    stat.value = fun(
                        entities, stats['features'][feature], curtimestamp)
                    entity_stats.append(stat)
                    computed[feature] = stat.value
                else:
                    not_computed.append(feature)

            from_time = datetime.combine(curtimestamp, time.min)
            if timezone.is_naive(from_time):
                from_time = pytz.utc.localize(from_time)
            to_time = datetime.combine(curtimestamp, time.max)
            if timezone.is_naive(to_time):
                to_time = pytz.utc.localize(to_time)

            EntityStat.objects.filter(
                federation=self, time__gte=from_time, time__lte=to_time).delete()
            EntityStat.objects.bulk_create(entity_stats)

        return (computed, not_computed)

    def process_metadata_entities(self, request=None, federation_slug=None):
        if not self._metadata: return
        entities_from_xml = self._metadata.get_entities()
        removed = self._remove_deleted_entities(entities_from_xml)

        entities = {}
        db_entities = Entity.objects.filter(entityid__in=entities_from_xml)
        db_entities = db_entities.prefetch_related('types')
        #TODO add prefetch related, federations, entity_categories

        for entity in db_entities.all():
            entities[entity.entityid] = entity

        if request and federation_slug:
            request.session['%s_num_entities' %
                            federation_slug] = len(entities_from_xml)
            request.session['%s_cur_entities' % federation_slug] = 0
            request.session['%s_process_done' % federation_slug] = False
            request.session.save()

        updated = self._add_new_entities(
            entities, entities_from_xml, request, federation_slug)

        if request and federation_slug:
            request.session['%s_process_done' % federation_slug] = True
            request.session.save()

        return removed, updated

    def get_absolute_url(self):
        return reverse('federation_view', args=[self.slug])

    @classmethod
    def get_sp(cls, entities, xml_name, ref_date=None):
        if ref_date and ref_date < pytz.utc.localize(datetime.now() - timedelta(days=1)):
            selected = entities.filter(
                types__xmlname=xml_name, entity_federations__registration_instant__lt=ref_date)
        else:
            selected = entities.filter(types__xmlname=xml_name)
        return len(selected)

    @classmethod
    def get_idp(cls, entities, xml_name, ref_date=None):
        if ref_date and ref_date < pytz.utc.localize(datetime.now() - timedelta(days=1)):
            selected = entities.filter(
                types__xmlname=xml_name, entity_federations__registration_instant__lt=ref_date)
        else:
            selected = entities.filter(types__xmlname=xml_name)
        return len(selected)

    @classmethod
    def get_aa(cls, entities, xml_name, ref_date=None):
        if ref_date and ref_date < pytz.utc.localize(datetime.now() - timedelta(days=1)):
            selected = entities.filter(
                types__xmlname=xml_name, entity_federations__registration_instant__lt=ref_date)
        else:
            selected = entities.filter(types__xmlname=xml_name)
        return len(selected)

    def get_sp_saml1(self, entities, xml_name, ref_date=None):
        return self.get_stat_protocol(entities, xml_name, 'SPSSODescriptor', ref_date)

    def get_sp_saml2(self, entities, xml_name, ref_date=None):
        return self.get_stat_protocol(entities, xml_name, 'SPSSODescriptor', ref_date)

    def get_sp_shib1(self, entities, xml_name, ref_date=None):
        return self.get_stat_protocol(entities, xml_name, 'SPSSODescriptor', ref_date)

    def get_idp_saml1(self, entities, xml_name, ref_date=None):
        return self.get_stat_protocol(entities, xml_name, 'IDPSSODescriptor', ref_date)

    def get_idp_saml2(self, entities, xml_name, ref_date=None):
        return self.get_stat_protocol(entities, xml_name, 'IDPSSODescriptor', ref_date)

    def get_idp_shib1(self, entities, xml_name, ref_date=None):
        return self.get_stat_protocol(entities, xml_name, 'IDPSSODescriptor', ref_date)

    def get_stat_protocol(self, entities, xml_name, service_type, ref_date):
        if ref_date and ref_date < pytz.utc.localize(datetime.now() - timedelta(days=1)):
            selected = entities.filter(types__xmlname=service_type,
                                       _display_protocols__contains=xml_name,
                                       entity_federations__registration_instant__lt=ref_date)
        else:
            selected = entities.filter(types__xmlname=service_type,
                                       _display_protocols__contains=xml_name)

        return len(selected)

    def can_edit(self, user, delete):
        if user.is_superuser:
            return True

        permission = 'delete_federation' if delete else 'change_federation'
        if user.has_perm('metadataparser.%s' % permission) and user in self.editor_users.all():
            return True
        return False


@receiver(pre_save, sender=Federation, dispatch_uid='federation_pre_save')
def federation_pre_save(sender, instance, **kwargs):
    # Skip pre_save if only file name is saved
    if kwargs.has_key('update_fields') and kwargs['update_fields'] == {'file'}:
        return

    #slug = slugify(unicode(instance.name))[:200]
    # if instance.file_url and instance.file_url != '':
    #    try:
    #        instance.fetch_metadata_file(slug)
    #    except Exception as e:
    #        pass

    if instance.name:
        instance.slug = slugify(unicode(instance))[:200]


@receiver(pre_save, sender=Entity, dispatch_uid='entity_pre_save')
def entity_pre_save(sender, instance, **kwargs):
    # if refetch and instance.file_url:
    #    slug = slugify(unicode(instance.name))[:200]
    #    instance.fetch_metadata_file(slug)
    #    instance.process_metadata()
    pass
