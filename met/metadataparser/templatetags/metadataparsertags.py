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

from django import template
from django.template.base import Node, TemplateSyntaxError
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe, SafeData
from met.metadataparser.models import Federation
from met.metadataparser.xmlparser import DESCRIPTOR_TYPES, DESCRIPTOR_TYPES_DISPLAY
from met.metadataparser.query_export import export_modes
from met.metadataparser.summary_export import export_summary_modes
from urllib import urlencode

register = template.Library()


class AddGetParameter(Node):
    def __init__(self, values):
        self.values = values

    def render(self, context):
        req = template.resolve_variable('request', context)
        params = req.GET.copy()
        for key, value in self.values.items():
            params[key] = value.resolve(context)
        return '?%s' % params.urlencode()


@register.tag()
def add_get(parser, token):
    pairs = token.split_contents()[1:]
    values = {}
    for pair in pairs:
        s = pair.split('=', 1)
        values[s[0]] = parser.compile_filter(s[1])
    return AddGetParameter(values)


@register.inclusion_tag('metadataparser/bootstrap_form.html')
def bootstrap_form(form, cancel_link='..', delete_link=True):
    return {'form': form,
            'cancel_link': cancel_link,
            'delete_link': delete_link}


@register.inclusion_tag('metadataparser/bootstrap_searchform.html')
def bootstrap_searchform(form):
    return {'form': form}


@register.inclusion_tag('metadataparser/federations_summary_tag.html', takes_context=True)
def federations_summary(context, queryname, counts, federations=None):
    if not federations:
        federations = Federation.objects.all()

    user = context.get('user', None)
    add_federation = user and user.has_perm('metadataparser.add_federation')

    return {'federations': federations,
            'add_federation': add_federation,
            'queryname': queryname,
            'counts': counts,
            'entity_types': DESCRIPTOR_TYPES}


@register.inclusion_tag('metadataparser/interfederations_summary_tag.html', takes_context=True)
def interfederations_summary(context, queryname, counts, federations=None):
    if not federations:
        federations = Federation.objects.all()

    user = context.get('user', None)
    add_federation = user and user.has_perm('metadataparser.add_federation')

    return {'federations': federations,
            'add_federation': add_federation,
            'queryname': queryname,
            'counts': counts,
            'entity_types': DESCRIPTOR_TYPES}

@register.inclusion_tag('metadataparser/tag_entity_list.html', takes_context=True)
def entity_list(context, entities, categories=None, pagination=None, curfed=None, show_total=True, append_query=None, onclick_page=None, onclick_export=None):
    request = context.get('request', None)
    lang = 'en'
    if request:
        lang = request.GET.get('lang', 'en')

    return {'request': request,
            'entities': entities,
            'categories': categories,
            'curfed': curfed,
            'show_filters': context.get('show_filters'),
            'append_query': append_query,
            'show_total': show_total,
            'lang': lang,
            'pagination': pagination,
            'onclick_page': onclick_page,
            'onclick_export': onclick_export,
            'entity_types': DESCRIPTOR_TYPES}


@register.inclusion_tag('metadataparser/most_fed_entities_summary.html', takes_context=True)
def most_fed_entity_list(context, entities, categories=None, pagination=None, curfed=None, show_total=True, append_query=None, onclick_page=None, onclick_export=None):
    request = context.get('request', None)
    lang = 'en'
    if request:
        lang = request.GET.get('lang', 'en')

    return {'request': request,
            'entities': entities,
            'categories': categories,
            'curfed': curfed,
            'show_filters': context.get('show_filters'),
            'append_query': append_query,
            'show_total': show_total,
            'lang': lang,
            'pagination': pagination,
            'onclick_page': onclick_page,
            'onclick_export': onclick_export,
            'entity_types': DESCRIPTOR_TYPES}


@register.inclusion_tag('metadataparser/service_search_summary.html', takes_context=True)
def service_search_result(context, entities, categories=None, pagination=None, curfed=None, show_total=True, append_query=None, onclick_page=None, onclick_export=None):
    request = context.get('request', None)
    lang = 'en'
    if request:
        lang = request.GET.get('lang', 'en')

    return {'request': request,
            'entities': entities,
            'categories': categories,
            'curfed': curfed,
            'show_filters': context.get('show_filters'),
            'append_query': append_query,
            'show_total': show_total,
            'lang': lang,
            'pagination': pagination,
            'onclick_page': onclick_page,
            'onclick_export': onclick_export,
            'entity_types': DESCRIPTOR_TYPES}



@register.inclusion_tag('metadataparser/tag_entity_filters.html', takes_context=True)
def entity_filters(context, entities, categories):
    entity_types = ('All', ) + DESCRIPTOR_TYPES
    request = context.get('request')
    entity_type = request.GET.get('entity_type', '')
    entity_category = request.GET.get('entity_category', '')
    rquery = request.GET.copy()
    for filt in 'entity_type', 'entity_category', 'page':
        if filt in rquery:
            rquery.pop(filt)
    if not entity_type:
        entity_type = 'All'
    if not entity_category:
        entity_category = 'All'
    query = urlencode(rquery)
    filter_base_path = request.path
    return {'filter_base_path': filter_base_path,
            'otherparams': query,
            'entity_types': entity_types,
            'entity_type': entity_type,
            'entity_category': entity_category,
            'entities': entities,
            'categories': categories}


@register.simple_tag()
def entity_filter_url(base_path, filt, otherparams=None):
    url = base_path
    if filt != 'All':
        url += '?entity_type=%s' % filt
        if otherparams:
            url += '&%s' % otherparams
    elif otherparams:
        url += '?%s' % otherparams

    return url


@register.simple_tag()
def entitycategory_filter_url(base_path, filt, otherparams=None):
    url = base_path
    if filt != 'All':
        url += '?entity_category=%s' % filt
        if otherparams:
            url += '&%s' % otherparams
    elif otherparams:
        url += '?%s' % otherparams

    return url


@register.inclusion_tag('metadataparser/export-menu.html', takes_context=True)
def export_menu(context, entities, append_query=None, onclick=None):
    request = context.get('request')
    copy_query = request.GET.copy()
    if 'page' in copy_query:
        copy_query.pop('page')
    query = copy_query.urlencode()
    base_path = request.path
    formats = []
    for mode in export_modes.keys():
        url = base_path
        if query:
            url += '?%s&format=%s' % (query, mode)
        else:
            url += '?format=%s' % (mode)
        if append_query:
            url += "&%s" % (append_query)
        formats.append({'url': url, 'label': mode, 'onclick': onclick})

    return {'formats': formats}


@register.inclusion_tag('metadataparser/export-menu.html')
def export_summary_menu(query, onclick=None):
    formats = []
    for mode in export_summary_modes.keys():
        urlquery = {'format': mode,
                    'export': query}
        url = "./?%(query)s" % {'query': urlencode(urlquery)}
        formats.append({'url': url, 'label': mode, 'onclick': onclick})

    return {'formats': formats}


@register.simple_tag()
def entities_count(entity_qs, entity_type=None):
    if entity_type and entity_type != 'All':
        return entity_qs.filter(types__xmlname=entity_type).count()
    else:
        return entity_qs.count()


@register.simple_tag()
def get_fed_total(totals, entity_type='All'):
    tot_count = 0
    for curtotal in totals:
        if entity_type == 'All' or curtotal['types__xmlname'] == entity_type:
            tot_count += curtotal['types__xmlname__count']
    return tot_count


@register.simple_tag()
def get_fed_count(counts, federation='All', entity_type='All'):
    count = counts[entity_type]

    fed_count = 0
    for curcount in count:
        if federation == 'All' or curcount['federations__id'] == federation:
            fed_count += curcount['federations__id__count']
    return fed_count


@register.simple_tag()
def get_fed_count_by_country(count, country='All'):
    fed_count = 0
    for curcount in count:
        if country == 'All' or curcount['federations__country'] == country:
            fed_count += curcount['federations__country__count']
    return fed_count


@register.simple_tag(takes_context=True)
def l10n_property(context, prop, lang):
    if isinstance(prop, dict) and len(prop) > 0:
        if not lang:
            lang = context.get('LANGUAGE_CODE', None)
        if lang and lang in prop:
            return prop.get(lang)
        else:
            return prop[prop.keys()[0]]
    return prop


@register.simple_tag(takes_context=True)
def organization_property(context, organizations, prop, lang):
    if not isinstance(organizations, list):
        return prop

    lang = lang or context.get('LANGUAGE_CODE', None)
    val = None
    for organization in organizations:
        if prop in organization:
            if val is None: val = organization[prop]
            if organization['lang'] == lang:
                val = organization[prop]

    return val


@register.simple_tag()
def get_property(obj, prop=None):
    uprop = unicode(prop)
    if not uprop:
        return '<a href="%(link)s">%(name)s</a>' % {"link": obj.get_absolute_url(),
                                                    "name": unicode(obj)}
    if isinstance(obj, dict):
        return obj.get(prop, None)
    if getattr(getattr(obj, uprop, None), 'all', None):
        return '. '.join(['<a href="%(link)s">%(name)s</a>' % {"link": item.get_absolute_url(),
                                                               "name": unicode(item)}
                          for item in getattr(obj, uprop).all()])
    if isinstance(getattr(obj, uprop, ''), list):
        return ', '.join(getattr(obj, uprop, []))
    return getattr(obj, uprop, '')


@register.simple_tag(takes_context=True)
def active_url(context, pattern):
    request = context.get('request')
    if request.path == pattern:
        return 'active'
    return ''


@register.filter(name='display_etype')
def display_etype(value, separator=', '):
    if isinstance(value, list):
        return separator.join(value)
    elif hasattr(value, 'all'):
        return separator.join([unicode(item) for item in value.all()])
    else:
        if value in DESCRIPTOR_TYPES_DISPLAY:
            return DESCRIPTOR_TYPES_DISPLAY.get(value)
        else:
            return value


@register.filter(name='mailto')
def mailto(value):
    if value.startswith('mailto:'):
        return value
    else:
        return 'mailto:%s' % value


@register.filter(name='wrap')
def wrap(value, length):
    value = unicode(value)
    if len(value) > length:
        return "%s..." % value[:length]
    return value


class CanEdit(Node):
    child_nodelists = 'nodelist'

    def __init__(self, obj, nodelist):
        self.obj = obj
        self.nodelist = nodelist

    @classmethod
    def __repr__(cls):
        return "<CanEdit>"

    def render(self, context):
        obj = self.obj.resolve(context, True)
        user = context.get('user')
        if obj.can_edit(user, False):
            return self.nodelist.render(context)
        else:
            return ''


def do_canedit(parser, token):
    bits = list(token.split_contents())
    if len(bits) != 2:
        raise TemplateSyntaxError("%r takes 1 argument" % bits[0])
    end_tag = 'end' + bits[0]
    nodelist = parser.parse((end_tag,))
    obj = parser.compile_filter(bits[1])
    token = parser.next_token()
    return CanEdit(obj, nodelist)


@register.tag
def canedit(parser, token):
    """
    Outputs the contents of the block if user has edit pemission

    Examples::

        {% canedit obj %}
            ...
        {% endcanedit %}
    """
    return do_canedit(parser, token)


@register.filter
@stringfilter
def split(value, splitter='|'):
    if not isinstance(value, SafeData):
        value = mark_safe(value)
    return value.split(splitter)
