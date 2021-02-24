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

from lxml import etree
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import simplejson as json

NAMESPACES = {
    'xml': 'http://www.w3.org/XML/1998/namespace',
    'xs': 'http://www.w3.org/2001/XMLSchema',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
    'mdui': 'urn:oasis:names:tc:SAML:metadata:ui',
    'ds': 'http://www.w3.org/2000/09/xmldsig#',
    'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
    'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
    'mdrpi': 'urn:oasis:names:tc:SAML:metadata:rpi',
    'shibmd': 'urn:mace:shibboleth:metadata:1.0',
    'mdattr': 'urn:oasis:names:tc:SAML:metadata:attribute',
}

SAML_METADATA_NAMESPACE = NAMESPACES['md']

XML_NAMESPACE = NAMESPACES['xml']
XMLDSIG_NAMESPACE = NAMESPACES['ds']
MDUI_NAMESPACE = NAMESPACES['mdui']

DESCRIPTOR_TYPES = ('IDPSSODescriptor', 'SPSSODescriptor', 'AASSODescriptor')
DESCRIPTOR_TYPES_DISPLAY = {}
for item in DESCRIPTOR_TYPES:
    DESCRIPTOR_TYPES_DISPLAY[item] = item.replace('SSODescriptor', '')

DESCRIPTOR_TYPES_UTIL = ["md:%s" % item for item in DESCRIPTOR_TYPES]


def addns(node_name, namespace=SAML_METADATA_NAMESPACE):
    '''Return a node name qualified with the XML namespace'''
    return '{' + namespace + '}' + node_name


def delns(node, namespace=SAML_METADATA_NAMESPACE):
    return node.replace('{' + namespace + '}', '')


def getlang(node):
    if 'lang' in node.attrib:
        return node.attrib['lang']
    elif addns('lang', NAMESPACES['xml']) in node.attrib:
        return node.attrib[addns('lang', NAMESPACES['xml'])]


FEDERATION_ROOT_TAG = addns('EntitiesDescriptor')
ENTITY_ROOT_TAG = addns('EntityDescriptor')


class MetadataParser(object):
    def __init__(self, filename=None):
        if filename is None:
            raise ValueError('filename is required')

        self.filename = filename
        with open(filename, 'r') as myfile:
            data = myfile.read().replace('\n', '')
        self.rootelem = etree.fromstring(data)
        self.file_id = self.rootelem.get('ID', None)
        self.is_federation = self.rootelem.tag == FEDERATION_ROOT_TAG
        self.is_entity = not self.is_federation

    @staticmethod
    def _get_entity_details(element):
        entity = {}

        entity['xml'] = etree.tostring(element, pretty_print=True)

        entity['description'] = MetadataParser.entity_description(element)
        entity['infoUrl'] = MetadataParser.entity_information_url(element)
        entity['privacyUrl'] = MetadataParser.entity_privacy_url(element)
        entity['organization'] = MetadataParser.entity_organization(element)
        entity['logos'] = MetadataParser.entity_logos(element)
        entity['scopes'] = MetadataParser.entity_attribute_scope(element)
        entity['attr_requested'] = MetadataParser.entity_requested_attributes(
            element)
        entity['contacts'] = MetadataParser.entity_contacts(element)
        entity['registration_policy'] = MetadataParser.registration_policy(
            element)

        return entity

    @staticmethod
    def _entity_lang_seen(entity):
        languages = set()
        for key in ['description', 'infoUrl', 'privacyUrl', 'organization', 'displayName']:
            if key in entity.keys() and entity[key]:
                languages |= set(entity[key].keys())

        return languages

    @staticmethod
    def _get_entity_by_id(context, entityid, details):
        for _, element in context:
            if element.attrib['entityID'] == entityid:
                entity = {}

                entity['entityid'] = entityid
                entity['file_id'] = element.get('ID', None)
                entity['displayName'] = MetadataParser.entity_displayname(
                    element)
                reg_info = MetadataParser.registration_information(element)
                if reg_info and 'authority' in reg_info:
                    entity['registration_authority'] = reg_info['authority']
                if reg_info and 'instant' in reg_info:
                    entity['registration_instant'] = reg_info['instant']
                entity['entity_categories'] = MetadataParser.entity_categories(
                    element)
                entity['entity_types'] = MetadataParser.entity_types(element)
                entity['protocols'] = MetadataParser.entity_protocols(
                    element, entity['entity_types'])
                entity['certstats'] = MetadataParser.get_certstats(element)

                if details:
                    entity_details = MetadataParser._get_entity_details(
                        element)
                    entity.update(entity_details)
                    entity = dict((k, v) for k, v in entity.iteritems() if v)

                entity['languages'] = MetadataParser._entity_lang_seen(entity)
                yield entity

            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]
        del context

    def get_federation(self):
        assert self.is_federation

        federation = {}
        federation['ID'] = self.rootelem.get('ID', None)
        federation['Name'] = self.rootelem.get('Name', None)

        return federation

    @staticmethod
    def _chunkstring(string, length):
        return (string[0 + i:length + i] for i in range(0, len(string), length))

    def get_entity(self, entityid, details=True):
        context = etree.iterparse(self.filename, tag=addns(
            'EntityDescriptor'), events=('end',), huge_tree=True, remove_blank_text=True)
        element = None
        for element in MetadataParser._get_entity_by_id(context, entityid, details):
            return element

        raise ValueError("Entity not found: %s" % entityid)

    def entity_exist(self, entityid):
        entity_xpath = self.rootelem.xpath("//md:EntityDescriptor[@entityID='%s']"
                                           % entityid, namespaces=NAMESPACES)
        return len(entity_xpath) > 0

    @staticmethod
    def _get_entities_id(context):
        for _, element in context:
            yield element.attrib['entityID']
            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]
        del context

    def get_entities(self):
        # Return entityid list
        context = etree.iterparse(self.filename, tag=addns(
            'EntityDescriptor'), events=('end',), huge_tree=True, remove_blank_text=True)
        return list(self._get_entities_id(context))

    @staticmethod
    def entity_types(entity):
        expression = "|".join([desc for desc in DESCRIPTOR_TYPES_UTIL])
        elements = entity.xpath(expression, namespaces=NAMESPACES)
        types = [element.tag.split("}")[1] for element in elements]
        if len(types) == 0:
            types = ['AASSODescriptor']
        return types

    @staticmethod
    def entity_categories(entity):
        elements = entity.xpath(".//mdattr:EntityAttributes"
                                "//saml:Attribute[@Name='http://macedir.org/entity-category-support' or @Name='http://macedir.org/entity-category' or @Name='urn:oasis:names:tc:SAML:attribute:assurance-certification']"
                                "//saml:AttributeValue",
                                namespaces=NAMESPACES)
        categories = [dnnode.text.strip() for dnnode in elements]
        return categories

    @staticmethod
    def entity_protocols(entity, entity_types):
        if isinstance(entity_types, list) and len(entity_types) > 0:
            e_type = entity_types[0]
        else:
            e_type = 'IDPSSODescriptor'

        raw_protocols = entity.xpath(".//md:%s"
                                     "/@protocolSupportEnumeration" % e_type,
                                     namespaces=NAMESPACES)
        if raw_protocols:
            protocols = raw_protocols[0]
            return protocols.split(' ')

        return []

    @staticmethod
    def get_certstats(element):
        hashes = {}

        for x in element.xpath(".//ds:X509Certificate", namespaces=NAMESPACES):
            certName = 'invalid'

            try:
                text = x.text.replace("\n", "").replace(
                    " ", "").replace("\t", "")
                text = "\n".join(MetadataParser._chunkstring(text, 64))
                certText = "\n".join(
                    ["-----BEGIN CERTIFICATE-----", text, '-----END CERTIFICATE-----'])
                cert = x509.load_pem_x509_certificate(
                    certText, default_backend())
                certName = cert.signature_hash_algorithm.name
            except Exception as e:
                pass

            if certName not in hashes:
                hashes[certName] = 0
            hashes[certName] += 1

        return json.dumps(hashes)

    @staticmethod
    def entity_displayname(entity):
        languages = {}

        names = entity.xpath(".//mdui:UIInfo"
                             "//mdui:DisplayName",
                             namespaces=NAMESPACES)

        for dn_node in names:
            lang = getlang(dn_node)
            languages[lang] = dn_node.text

        if None in languages.keys():
            del languages[None]
        return languages

    @staticmethod
    def entity_description(entity):
        languages = {}

        names = entity.xpath(".//mdui:UIInfo"
                             "//mdui:Description",
                             namespaces=NAMESPACES)

        for dn_node in names:
            lang = getlang(dn_node)
            languages[lang] = dn_node.text

        if None in languages.keys():
            del languages[None]
        return languages

    @staticmethod
    def entity_information_url(entity):
        languages = {}

        names = entity.xpath(".//mdui:UIInfo"
                             "//mdui:InformationURL",
                             namespaces=NAMESPACES)

        for dn_node in names:
            lang = getlang(dn_node)
            languages[lang] = dn_node.text

        if None in languages.keys():
            del languages[None]
        return languages

    @staticmethod
    def entity_privacy_url(entity):
        languages = {}

        names = entity.xpath(".//mdui:UIInfo"
                             "//mdui:PrivacyStatementURL",
                             namespaces=NAMESPACES)

        for dn_node in names:
            lang = getlang(dn_node)
            languages[lang] = dn_node.text

        if None in languages.keys():
            del languages[None]
        return languages

    @staticmethod
    def entity_organization(entity):
        orgs = entity.xpath(".//md:Organization",
                            namespaces=NAMESPACES)
        languages = {}
        for org_node in orgs:
            for attr in 'name', 'displayName', 'URL':
                node_name = 'Organization' + attr[0].upper() + attr[1:]
                for node in org_node.findall(addns(node_name)):
                    lang = getlang(node)
                    lang_dict = languages.setdefault(lang, {})
                    lang_dict[attr] = node.text

        if None in languages.keys():
            del languages[None]
        return languages

    @staticmethod
    def entity_logos(entity):
        xmllogos = entity.xpath(".//mdui:UIInfo"
                                "//mdui:Logo",
                                namespaces=NAMESPACES)
        logos = []
        for logo_node in xmllogos:
            if logo_node.text is None:
                continue  # the file attribute is required
            logo = {}
            logo['width'] = int(logo_node.attrib.get('width', '0'))
            logo['height'] = int(logo_node.attrib.get('height', '0'))
            logo['file'] = logo_node.text
            logo['lang'] = getlang(logo_node)
            logos.append(logo)
        return logos

    @staticmethod
    def registration_information(entity):
        reg_info = entity.xpath(".//md:Extensions"
                                "//mdrpi:RegistrationInfo",
                                namespaces=NAMESPACES)
        info = {}
        if reg_info:
            info['authority'] = reg_info[0].attrib.get('registrationAuthority')
            info['instant'] = reg_info[0].attrib.get('registrationInstant')
        return info

    @staticmethod
    def registration_policy(entity):
        reg_policy = entity.xpath(".//md:Extensions"
                                  "//mdrpi:RegistrationInfo"
                                  "//mdrpi:RegistrationPolicy",
                                  namespaces=NAMESPACES)
        languages = {}
        for dn_node in reg_policy:
            lang = getlang(dn_node)
            if lang is None:
                continue  # the lang attribute is required

            languages[lang] = dn_node.text

        return languages

    @staticmethod
    def entity_attribute_scope(entity):
        scope_node = entity.xpath(".//md:Extensions"
                                  "//shibmd:Scope",
                                  namespaces=NAMESPACES)

        scope = []
        for cur_scope in scope_node:
            if not cur_scope.text in scope:
                scope.append(cur_scope.text)
        return scope

    @staticmethod
    def entity_requested_attributes(entity):
        xmllogos = entity.xpath(".//md:AttributeConsumingService"
                                "//md:RequestedAttribute",
                                namespaces=NAMESPACES)
        attrs = {}
        attrs['required'] = []
        attrs['optional'] = []
        for attr_node in xmllogos:
            required = attr_node.attrib.get('isRequired', 'false')
            index = 'required' if required == 'true' else 'optional'
            attrs[index].append([attr_node.attrib.get(
                'Name', None), attr_node.attrib.get('FriendlyName', None)])
        return attrs

    @staticmethod
    def entity_contacts(entity):
        contacts = entity.xpath(".//md:ContactPerson",
                                namespaces=NAMESPACES)
        cont = []
        for cont_node in contacts:
            c_type = cont_node.attrib.get('contactType', '')
            name = cont_node.xpath(".//md:GivenName", namespaces=NAMESPACES)
            if name:
                name = name[0].text
            else:
                name = None
            surname = cont_node.xpath(".//md:SurName", namespaces=NAMESPACES)
            if surname:
                surname = surname[0].text
            else:
                surname = None
            email = cont_node.xpath(
                ".//md:EmailAddress", namespaces=NAMESPACES)
            if email:
                email = email[0].text
            else:
                email = None
            cont.append({'type': c_type, 'name': name,
                         'surname': surname, 'email': email})
        return cont
