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

import re, time
import pytz
import operator
import simplejson as json
from urllib import unquote
from datetime import datetime
from dateutil import tz

from django.conf import settings
from django.db.models import Count, Q
from django.contrib import messages
from django.contrib.auth import logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from chartit import DataPool, Chart

from datetime import datetime

from met.metadataparser.decorators import user_can_edit
from met.metadataparser.models import Federation, Entity, EntityStat, EntityCategory, Entity_Federations, TOP_LENGTH, FEDERATION_TYPES
from met.metadataparser.forms import (FederationForm, EntityForm, EntityCommentForm,
                                      EntityProposalForm, ServiceSearchForm, ChartForm, SearchEntitiesForm)

from met.metadataparser.summary_export import export_summary
from met.metadataparser.query_export import export_query_set
from met.metadataparser.entity_export import export_entity
from met.metadataparser.xmlparser import DESCRIPTOR_TYPES
from met.metadataparser.utils import send_mail

if settings.PROFILE:
    from silk.profiling.profiler import silk_profile as profile
else:
    from met.metadataparser.templatetags.decorators import noop_decorator as profile

RESCUE_SLASH = re.compile(r"^(http(?:|s):/)([^/])")

def increment_current_toplength(request):
    current_top_length = request.session.get('currentTopLength', TOP_LENGTH)
    current_top_length += TOP_LENGTH

    if current_top_length > Entity.objects.all().count():
        current_top_length -= TOP_LENGTH

    request.session['currentTopLength'] = current_top_length
    return HttpResponseRedirect(reverse('index'))
    
def decrement_current_toplength(request):
    current_top_length = request.session.get('currentTopLength', TOP_LENGTH)
    current_top_length -= TOP_LENGTH

    if current_top_length <= 0:
        current_top_length = TOP_LENGTH

    request.session['currentTopLength'] = current_top_length
    return HttpResponseRedirect(reverse('index'))

def _index_export(export, export_format, objects):
    counters = (
                ('all', {}),
                ('IDPSSO', {'types__xmlname': 'IDPSSODescriptor'}),
                ('SPSSO', {'types__xmlname': 'SPSSODescriptor'}),
               )

    if not export in ['interfederations', 'federations', 'most_federated_entities']:
        return HttpResponseBadRequest('Not valid export query')

    if export == 'most_federated_entities':
        return export_query_set(export_format, objects['most_federated_entities'],
                                'most_federated_entities', ('entityid', 'types', 'name', 'federations'))
    else:
        return export_summary(export_format, objects[export],
                              'entity_set', '%s_summary' % export,
                              counters)

@profile(name='Index page')
def index(request):
    ff = Federation.objects.all().order_by('name')
    federations = []
    interfederations = []
    for f in ff:
        if f.is_interfederation:
            interfederations.append(f)
        else:
            federations.append(f)

    cc = Entity.objects.values('federations__id', 'types__xmlname').annotate(Count('federations__id'), Count('types__xmlname'))
    counts = {}
    for curtype in DESCRIPTOR_TYPES:
        counts[curtype] = []
        for c in cc:
            if c['types__xmlname'] == curtype:
                counts[curtype].append(c)
    counts['All'] = Entity.objects.values('federations__id').annotate(Count('federations__id'))

    totals = Entity.objects.values('types__xmlname').annotate(Count('types__xmlname'))

    # Entities with count how many federations belongs to, and sorted by most first
    current_top_length = request.session.get('currentTopLength', TOP_LENGTH)
    most_federated_entities = Entity.get_most_federated_entities(maxlength=current_top_length, cache_expire=24*60*60)

    params = {
       'settings': settings,
       'interfederations': interfederations,
       'federations': federations,
       'entity_types': DESCRIPTOR_TYPES,
       'federation_path': request.path,
       'counts': counts,
       'totals': totals,
       'most_federated_entities': most_federated_entities,
    }

    export = request.GET.get('export', None)
    export_format = request.GET.get('format', None)
    if export and export_format:
        return _index_export(export, export_format, params)
    
    return render_to_response('metadataparser/index.html', params, context_instance=RequestContext(request))

def _paginate_fed(ob_entities, page):
    paginator = Paginator(ob_entities, 20)

    try:
        ob_entities = paginator.page(page)
    except PageNotAnInteger:
        ob_entities = paginator.page(1)
    except EmptyPage:
        ob_entities = paginator.page(paginator.num_pages)

    adjacent_pages = 5
    page_range = [n for n in \
                  range(ob_entities.number - adjacent_pages, ob_entities.number + adjacent_pages + 1) \
                  if n > 0 and n <= ob_entities.paginator.num_pages]

    return {
        'page_range': page_range,
        'cur_page_number': ob_entities.number,
        'num_pages': ob_entities.paginator.num_pages,
        'num_objects': ob_entities.paginator.count,
        'objects': ob_entities.object_list,
    }

@profile(name='Federation view')
def federation_view(request, federation_slug=None):
    if federation_slug:
        request.session['%s_process_done' % federation_slug] = False
        request.session['%s_num_entities' % federation_slug] = 0
        request.session['%s_cur_entities' % federation_slug] = 0
        request.session.save()

    federation = get_object_or_404(Federation, slug=federation_slug)
    if federation.registration_authority:
        categories = EntityCategory.objects.all().filter(
            Q(category_id__icontains=federation.registration_authority) |
            Q(category_id__icontains='http://refeds.org') |
            Q(category_id__icontains='http://www.geant.net'))
    else:
        categories = EntityCategory.objects.all().filter(
            Q(category_id__icontains='http://refeds.org') |
            Q(category_id__icontains='http://www.geant.net'))

    ob_entities = Entity.objects.filter(federations__id=federation.id)
    entity_type = None
    if request.GET and 'entity_type' in request.GET:
        entity_type = request.GET['entity_type']
        ob_entities = ob_entities.filter(types__xmlname=entity_type)
    
    entity_category = None
    if request.GET and 'entity_category' in request.GET:
        entity_category = request.GET['entity_category']

    ob_entities = ob_entities.prefetch_related('types', 'federations')
    pagination = _paginate_fed(ob_entities, request.GET.get('page'))

    entities = []
    for entity in pagination['objects']:
        entity.curfed = federation
        if entity_category is None or entity_category in [c.category_id for c in entity.entity_categories.all()]:
            entities.append({
                'entityid': entity.entityid,
                'name': entity.name,
                'absolute_url': entity.get_absolute_url(),
                'types': [unicode(item) for item in entity.types.all()],
                'federations': [(unicode(item.name), item.get_absolute_url()) for item in entity.federations.all()],
            })

    if 'format' in request.GET:
        return export_query_set(request.GET.get('format'), entities,
                                'entities_search_result', ('entityid', 'types', 'federations'))

    context = RequestContext(request)
    user = context.get('user', None)
    add_entity = user and user.has_perm('metadataparser.add_federation')
    pie_chart = fed_pie_chart(request, federation.id)

    return render_to_response('metadataparser/federation_view.html',
            {'settings': settings,
             'federation': federation,
             'entity_types': DESCRIPTOR_TYPES,
             'entity_type': entity_type or 'All',
             'fed_types': dict(FEDERATION_TYPES),
             'entities': entities,
             'categories': categories,
             'show_filters': True,
             'add_entity': add_entity,
             'lang': request.GET.get('lang', 'en'),
             'update_entities': request.GET.get('update', 'false'),
             'statcharts': [pie_chart],
             'pagination': pagination,
            }, context_instance=context)


@user_can_edit(Federation)
def federation_edit_post(request, federation, form):
    modify = True if federation else False
    form.save()

    if not modify:
        form.instance.editor_users.add(request.user)
    if 'file' in form.changed_data or 'file_url' in form.changed_data:
        form.instance.process_metadata()

    messages.success(request, _('Federation %s successfully' % 'modified' if modify else 'created'))
    return HttpResponseRedirect(form.instance.get_absolute_url() + '?update=true')


@user_can_edit(Federation)
def federation_edit(request, federation_slug=None):
    federation = get_object_or_404(Federation, slug=federation_slug) if federation_slug else None

    if request.method == 'POST':
        form = FederationForm(request.POST, request.FILES, instance=federation)
        if not form.is_valid():
            messages.error(request, _('Please correct the errors indicated below'))
        else:
            return federation_edit_post(request, federation, form)
    else:
        form = FederationForm(instance=federation)

    context = RequestContext(request)
    user = context.get('user', None)
    delete_federation = user and user.has_perm('metadataparser.delete_federation')
    return render_to_response('metadataparser/federation_edit.html',
                              {'settings': settings, 'form': form, 'delete_federation': delete_federation},
                              context_instance=RequestContext(request))


@user_can_edit(Federation)
def federation_update_entities(request, federation_slug=None):
    federation = get_object_or_404(Federation, slug=federation_slug)
    federation.process_metadata_entities(request=request, federation_slug=federation_slug)

    messages.success(request, _('Federation entities updated succesfully'))
    return HttpResponse("Done. All entities updated.", content_type='text/plain')


def entityupdate_progress(request, federation_slug=None):
    data = { 'done': False }
    if federation_slug:
        data = { 'done': request.session.get('%s_process_done' % federation_slug, False),
                 'tot': request.session.get('%s_num_entities' % federation_slug, 0),
                 'num': request.session.get('%s_cur_entities' % federation_slug, 0) }

    return HttpResponse(json.dumps(data), content_type='application/javascript')


@user_can_edit(Federation, True)
def federation_delete(request, federation_slug):
    federation = get_object_or_404(Federation, slug=federation_slug)

    for entity in federation.entity_set.all():
        if len(entity.federations.all()) == 1:
            entity.delete()

    messages.success(request,
                     _(u"%(federation)s federation was deleted successfully"
                     % {'federation': unicode(federation)}))
    federation.delete()
    return HttpResponseRedirect(reverse('index'))


@profile(name='Index charts')
def federation_charts(request, federation_slug=None):
    if federation_slug is None:
        federation = None
    else:
        federation = get_object_or_404(Federation, slug=federation_slug)

    if request.method == 'POST':
        form = ChartForm(request.POST, request.FILES, instance=federation)

        if form.is_valid():
            stats_config_dict = getattr(settings, "STATS")
            service_terms = stats_config_dict['statistics']['entity_by_type']['terms']
            protocol_terms = stats_config_dict['statistics']['entity_by_protocol']['terms']
            
            protocols = stats_config_dict['protocols']

            from_time = datetime.fromordinal(form.cleaned_data['fromDate'].toordinal())
            if timezone.is_naive(from_time):
                from_time = pytz.utc.localize(from_time)
            to_time = datetime.fromordinal(form.cleaned_data['toDate'].toordinal() + 1)
            if timezone.is_naive(to_time):
                to_time = pytz.utc.localize(to_time)

            service_stats = EntityStat.objects.filter(  federation=federation \
                                              , feature__in = service_terms \
                                              , time__gte = from_time \
                                              , time__lte = to_time).order_by("time")

            protocol_stats = EntityStat.objects.filter(  federation=federation \
                                              , feature__in = protocol_terms \
                                              , time__gte = from_time \
                                              , time__lte = to_time).order_by("time")

            s_chart = []

            if len(service_stats) > 0:
                cur_data = service_stats[0].time.strftime('%d/%m/%y')
                cur_stat = { 'date': cur_data }
                for s in service_stats:
                    if s.time.strftime('%d/%m/%y') != cur_data:
                        s_chart.append(cur_stat)
                        cur_data = s.time.strftime('%d/%m/%y')
                        cur_stat = { 'date': cur_data }
                    
                    cur_stat[s.feature] = s.value
                s_chart.append(cur_stat)

            p_chart = []
            if len(protocol_stats) > 0:
                cur_data = protocol_stats[0].time.strftime('%d/%m/%y')
                cur_stat = { 'date': cur_data }
                for p in protocol_stats:
                    if p.time.strftime('%d/%m/%y') != cur_data:
                        p_chart.append(cur_stat)
                        cur_data = p.time.strftime('%d/%m/%y')
                        cur_stat = { 'date': cur_data }

                    cur_stat[p.feature] = p.value
                p_chart.append(cur_stat)

            return render_to_response('metadataparser/federation_chart.html',
                                      {'form': form,
                                       'statcharts': ['aa'], #[s_chart, p_chart],
                                       's_chart': s_chart,
                                       'p_chart': p_chart,
                                      },
                                      context_instance=RequestContext(request))

        else:
            messages.error(request, _('Please correct the errors indicated'
                                      ' below'))
    else:
        form = ChartForm(instance=federation)

    return render_to_response('metadataparser/federation_chart.html',
                              {'settings': settings, 'form': form},
                              context_instance=RequestContext(request))


def stats_chart(stats_config_dict, request, stats, entity, protocols=None):
    terms = stats_config_dict['statistics'][entity]['terms']
    title = stats_config_dict['statistics'][entity]['title']
    x_title = stats_config_dict['statistics'][entity]['x_title']
    y_title = stats_config_dict['statistics'][entity]['y_title']
    chart_type = 'column'
    stacking = True
    term_names = stats_config_dict['feature_names']
    time_format = stats_config_dict['time_format']
    statdata = _create_statdata('bar', stats, terms, term_names)

    series_options = []
    for stack in range(len(protocols) if protocols else 1):
        for term in terms:
            if not protocols or term.endswith(protocols[stack]):
                series_options += \
                  [{'options':{
                      'type': chart_type,
                      'stacking': stacking,
                      'stack': stack,
                    },
                    'terms':{
                      'time_%s' %term: [{term_names[term]: {'stack': stack, }}],
                    }}]

    chart_options = _get_chart_options('bar', title, x_title, y_title)

    return Chart(
        datasource = statdata,
        series_options = series_options,
        chart_options = chart_options, 
        x_sortf_mapf_mts=(None, lambda i: datetime.fromtimestamp(time.mktime(i.replace(tzinfo=tz.gettz('UTC')).astimezone(tz.tzlocal()).timetuple())).strftime(time_format), False)
    )



def _create_statdata(chart_type, stats, terms=None, term_names=None):
    if chart_type == 'bar':
        statdata = DataPool(
           series=[{'options': {
                       'source': stats.filter(feature=term)},
                       'legend_by': 'feature',
                       'terms': [{'time_%s' %term :'time'}, 
                                 {term_names[term] : 'value', 'name': 'feature'}]
                    } for term in terms]
        )
    elif chart_type == 'pie':
        statdata = DataPool(
           series=[{'options': { 'source': stats },
                    'legend_by': 'feature',
                    'terms': ['feature', 'value'],
                  }]
        )
    else:
        statdata = None

    return statdata

def _get_chart_options(chart_type, title=None, x_title=None, y_title=None):
    if chart_type == 'bar':
        chart_options = {'title': { 'text': title },
           'xAxis': {
                'title': { 'text': x_title },
                'labels': {
                   'rotation': -45,
                   'align': 'right'
                },
                'max': 10,
            },
           'yAxis': {
                'title': { 'text': y_title },
                'minorTickInterval': 'auto'
            },
           'credits': { 'enabled': False },
           'scrollbar': { 'enabled': True },
           'zoomType': 'xy',
        }
    elif chart_type == 'pie':
        chart_options = {
            'title': { 'text': ' ' },
            'credits': { 'enabled': False }
        }
    else:
        chart_options = None

    return chart_options

def fed_pie_chart(request, federation_id):
    stats_config_dict = getattr(settings, "STATS")
    terms = stats_config_dict['statistics']['entity_by_type']['terms']
    stats = EntityStat.objects.filter(federation=federation_id, \
                                      feature__in=terms).order_by('-time')[0:len(terms)]
    statdata = _create_statdata('pie', stats)
    series_options = \
        [{'options': { 'type': 'pie', 'stacking': False, 'size': '70%' },
          'terms':{ 'feature': [ 'value' ] }}]
    chart_options = _get_chart_options('pie')

    return Chart(
        datasource = statdata,
        series_options = series_options,
        chart_options = chart_options,
    )



@profile(name='Entity view')
def entity_view(request, entityid):
    entityid = unquote(entityid)
    entityid = RESCUE_SLASH.sub("\\1/\\2", entityid)

    entity = get_object_or_404(Entity, entityid=entityid)

    if 'federation' in request.GET:
        federation = get_object_or_404(Federation, slug=request.GET.get('federation'))
        entity.curfed = federation
    else:
        federation = entity.federations.all()[0]
        entity.curfed = federation

    if 'format' in request.GET:
        return export_entity(request.GET.get('format'), entity)

    if 'viewxml' in request.GET:
        serialized = entity.xml
        response = HttpResponse(serialized, content_type='application/xml')
        return response

    return render_to_response('metadataparser/entity_view.html',
            {'settings': settings,
             'entity': entity,
             'lang': request.GET.get('lang', 'en') 
            }, context_instance=RequestContext(request))


@user_can_edit(Entity)
def entity_edit_post(request, form, federation, entity):
    form.save()
    if federation and not federation in form.instance.federations.all():
        form.instance.federations.add(federation)
        form.instance.save()

    if entity:
        messages.success(request, _('Entity modified successfully'))
    else:
        messages.success(request, _('Entity created successfully'))

    return HttpResponseRedirect(form.instance.get_absolute_url())



@user_can_edit(Entity)
def entity_edit(request, federation_slug=None, entity_id=None):
    entity = None
    federation = None
    if federation_slug:
        federation = get_object_or_404(Federation, slug=federation_slug)
        if entity_id:
            entity = get_object_or_404(Entity, id=entity_id,
                                       federations__id=federation.id)
    if entity_id and not federation_slug:
        entity = get_object_or_404(Entity, id=entity_id)

    if request.method == 'POST':
        form = EntityForm(request.POST, request.FILES, instance=entity)
        if form.is_valid():
            return entity_edit_post(request, form, federation, entity)
        else:
            messages.error(request, _('Please correct the errors indicated below'))
    else:
        form = EntityForm(instance=entity)

    return render_to_response('metadataparser/entity_edit.html',
                              {'settings': settings,
                               'form': form,
                               'federation': federation},
                              context_instance=RequestContext(request))


@user_can_edit(Entity, True)
def entity_delete(request, entity_id):
    entity = get_object_or_404(Entity, id=entity_id)
    messages.success(request,
                     _(u"%(entity)s entity was deleted successfully"
                     % {'entity': unicode(entity)}))
    entity.delete()
    return HttpResponseRedirect(reverse('index'))


def entity_comment(request, federation_slug=None, entity_id=None):
    entity = None
    federation = None
    if federation_slug:
        federation = get_object_or_404(Federation, slug=federation_slug)
        if entity_id:
            entity = get_object_or_404(Entity, id=entity_id,
                                       federations__id=federation.id)
    if entity_id and not federation_slug:
        entity = get_object_or_404(Entity, id=entity_id)

    if request.method == 'POST':
        form = EntityCommentForm(request.POST, request.FILES, instance=entity)
        if form.is_valid():
            mail_config = getattr(settings, "MAIL_CONFIG")
            try:
                subject = mail_config['comment_subject'] %entity
                send_mail(form.data['email'], subject, form.data['comment'])
                messages.success(request, _('Comment posted successfully'))
            except Exception, errorMessage:
                messages.error(request, _('Comment could not be posted successfully: %s' %errorMessage))

            return HttpResponseRedirect(form.instance.get_absolute_url())

        else:
            messages.error(request, _('Please correct the errors indicated'
                                      ' below'))
    else:
        form = EntityCommentForm(instance=entity)

    return render_to_response('metadataparser/entity_comment.html',
                              {'settings': settings,
                               'form': form,
                              },
                              context_instance=RequestContext(request))


def entity_proposal(request, federation_slug=None, entity_id=None):
    entity = None
    federation = None
    if federation_slug:
        federation = get_object_or_404(Federation, slug=federation_slug)
        if entity_id:
            entity = get_object_or_404(Entity, id=entity_id,
                                       federations__id=federation.id)
    if entity_id and not federation_slug:
        entity = get_object_or_404(Entity, id=entity_id)

    if request.method == 'POST':
        form = EntityProposalForm(request.POST, request.FILES, instance=entity)
     
        if form.is_valid():
            mail_config = getattr(settings, "MAIL_CONFIG")
            try:
                subject = mail_config['proposal_subject'] %entity
                my_dict = dict(form.data.iterlists())
                body = mail_config['proposal_body'] % (entity, ', '.join(my_dict['federations']), form.data['comment'])
                send_mail(form.data['email'], subject, body)
                messages.success(request, _('Proposal posted successfully'))
            except Exception, errorMessage:
                messages.error(request, _('Proposal could not be posted successfully: %s' %errorMessage))

            return HttpResponseRedirect(form.instance.get_absolute_url())

        else:
            messages.error(request, _('Please correct the errors indicated'
                                      ' below'))
    else:
        form = EntityProposalForm(instance=entity)

    return render_to_response('metadataparser/entity_proposal.html',
                              {'settings': settings,
                               'form': form,
                              },
                              context_instance=RequestContext(request))

def search_service(request):
    filters = {}
    objects = []

    if 'entityid' in request.GET:
        form = ServiceSearchForm(request.GET)
        if form.is_valid():
            entityid = form.cleaned_data['entityid']
            entityid = entityid.strip()
            filters['entityid__icontains'] = entityid
    else:
        form = ServiceSearchForm()
    entity_type = request.GET.get('entity_type', None)

    if entity_type:
        filters['entity_type'] = entity_type

    if filters:
        objects = Entity.objects.filter(**filters)

    if objects and 'format' in request.GET.keys():
        entities = []
        for entity in objects:
            entities.append({
                'entityid': entity.entityid,
                'name': entity.name,
                'absolute_url': entity.get_absolute_url(),
                'types': [unicode(item) for item in entity.types.all()],
                'federations': [(unicode(item.name), item.get_absolute_url()) for item in entity.federations.all()],
            })

        return export_query_set(request.GET.get('format'), entities,
                                'entities_search_result', ('entityid', 'types', 'federations'))

    entities = []
    for entity in objects:
        entities.append({
            'entityid': entity.entityid,
            'name': entity.name,
            'absolute_url': entity.get_absolute_url(),
            'types': [unicode(item) for item in entity.types.all()],
            'federations': [(unicode(item.name), item.get_absolute_url()) for item in entity.federations.all()],
        })

    return render_to_response('metadataparser/service_search.html',
        {'settings': settings,
         'searchform': form,
         'object_list': entities,
         'show_filters': False,
        }, context_instance=RequestContext(request))

def met_logout(request):
    logout(request)
    return HttpResponseRedirect(request.GET.get("next", "/"))


@profile(name='Search entities')
def search_entities(request):
    if request.method == 'POST':
        form = SearchEntitiesForm(request.POST)

        if form.is_valid():
            filters = {}
            args = ()

            entity_type = form.cleaned_data['entity_type']
            if entity_type and entity_type != 'All':
                filters['types__name'] = entity_type

            federations = form.cleaned_data['federations']
            if federations and not 'All' in federations:
                q_list = [Q(federations__id=f) for f in federations]
                args = (reduce(operator.or_, q_list),)

            entity_id = form.cleaned_data['entityid']
            if entity_id and entity_id != '':
                filters['entityid__icontains'] = entity_id

            ob_entities = Entity.objects.all()
            if args:
                ob_entities = ob_entities.filter(*args)
            if filters:
                ob_entities = ob_entities.filter(**filters)

            entity_category = form.cleaned_data['entity_category']
            if entity_category and entity_category != 'All':
                eid_list = []

                for entity in ob_entities.all():
                    feds = Entity_Federations.objects.filter(entity=entity)

                    if federations and not 'All' in federations:
                        ec_list = [Q(federation__id=f) for f in federations]
                        ec_args = (reduce(operator.or_, ec_list),)
                        feds = feds.filter(*ec_args)

                    feds.prefetch_related('entity_categories')
                    feds = feds.filter(entity_categories__category_id=entity_category)
                    eid_list.extend([ Q(entityid=f.entity.entityid) for f in feds])

                eid_args = (reduce(operator.or_, eid_list),)
                ob_entities = ob_entities.filter(*eid_args)

            ob_entities = ob_entities.prefetch_related('types', 'federations')
            pagination = _paginate_fed(ob_entities, form.cleaned_data['page'])

            entities = []
            for entity in pagination['objects']:
                entities.append({
                    'entityid': entity.entityid,
                    'name': entity.name,
                    'absolute_url': entity.get_absolute_url(),
                    'types': [unicode(item) for item in entity.types.all()],
                    'federations': [(unicode(item.name), item.get_absolute_url()) for item in entity.federations.all()],
                })

            export_format = form.cleaned_data['export_format']
            if export_format:
                return export_query_set(export_format, entities,
                                        'entities_search_result', ('entityid', 'types', 'federations'))

            return render_to_response('metadataparser/search_entities.html',
                                      {'settings': settings,
                                       'form': form,
                                       'object_list': entities,
                                       'show_filters': False,
                                       'pagination': pagination,
                                      }, context_instance=RequestContext(request))

        else:
            messages.error(request, _('Please correct the errors indicated'
                                      ' below'))
    else:
        form = SearchEntitiesForm()

    return render_to_response('metadataparser/search_entities.html',
                              {'form': form},
                              context_instance=RequestContext(request))


