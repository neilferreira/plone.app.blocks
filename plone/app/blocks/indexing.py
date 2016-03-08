from Products.CMFPlone.utils import safe_unicode
from lxml.html import fromstring
from lxml.html import tostring
from plone.app.blocks.layoutbehavior import ILayoutAware
from plone.indexer.decorator import indexer
from plone.tiles.data import ANNOTATIONS_KEY_PREFIX
from zope.annotation.interfaces import IAnnotations
from z3c.relationfield.relation import RelationValue
from plone.namedfile.file import NamedBlobFile
from datetime import date
from plone.namedfile.file import NamedFile
from DateTime import DateTime
from plone.app.textfield import RichTextValue
from Products.CMFCore.utils import getToolByName
import logging


try:
    from plone.app.contenttypes import indexers
    concat = indexers._unicode_save_string_concat
except ImportError:
    def concat(*args):
        result = ''
        for value in args:
            if isinstance(value, unicode):
                value = value.encode('utf-8', 'replace')
            if value:
                result = ' '.join((result, value))
        return result


@indexer(ILayoutAware)
def LayoutSearchableText(obj):
    # todo: what relevance does the object id have here?
    indexed_text = [obj.id]
    try:
        indexed_text.append(obj.text.output)
    except AttributeError:
        pass
    try:
        indexed_text.append(safe_unicode(obj.title))
    except AttributeError:
        pass
    try:
        indexed_text.append(safe_unicode(obj.description))
    except AttributeError:
        pass

    behavior_data = ILayoutAware(obj)
    # get data from tile data
    annotations = IAnnotations(obj)
    for key in annotations.keys():
        if key.startswith(ANNOTATIONS_KEY_PREFIX):
            data = annotations[key]
            for field_name in data:
                build_layout_indexed_text(obj, indexed_text, data[field_name])

    if not behavior_data.contentLayout and behavior_data.content:
        dom = fromstring(behavior_data.content)
        for el in dom.cssselect('.mosaic-text-tile .mosaic-tile-content'):
            indexed_text.append(tostring(el))
    return concat(*indexed_text)


def build_layout_indexed_text(obj, indexed_text, value):
    if not value:
        return
    if isinstance(value, (bool, int, date, NamedFile, NamedBlobFile, DateTime)):
        # We can't do anything with these
        return
    elif isinstance(value, basestring):
        indexed_text.append(value)
    elif isinstance(value, (RichTextValue, basestring)):
        if isinstance(value, RichTextValue):
            transforms = getToolByName(obj, 'portal_transforms')
            indexed_text.append(
                transforms.convertTo(
                    'text/plain',
                    value.raw,
                    mimetype='text/html')
                .getData()
                .strip()
            )
    elif isinstance(value, dict):
        for key in value:
            build_layout_indexed_text(obj, indexed_text, value[key])
    elif isinstance(value, (list, set, tuple)):
        for row in value:
            build_layout_indexed_text(obj, indexed_text, row)
    elif isinstance(value, RelationValue):
        indexed_text.append(value.to_object.Title())
    else:
        logger = logging.getLogger(__name__)
        logger.error('Could not do anything with %s (type %s)' % (value, type(value)))
