import transaction
from Acquisition import aq_parent, aq_base
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import _createObjectByType
from Products.PortalTransforms.Transform import make_config_persistent


def install_addons(context):
    qi = getToolByName(context, 'portal_quickinstaller')
    if not qi.isProductInstalled('Products.PressRoom'):
        qi.installProduct('Products.PressRoom')
    if not qi.isProductInstalled('ftw.calendar'):
        qi.installProduct('ftw.calendar')
    if not qi.isProductInstalled('Products.PloneKeywordManager'):
        qi.installProduct('Products.PloneKeywordManager')
    if not qi.isProductInstalled('Products.RedirectionTool'):
        qi.installProduct('Products.RedirectionTool')

def copy_generic_fields(event):
    event_object = event.getObject()
    temp_id = "temp_copy_of_%s" % event_object.id
    container = aq_parent(event_object)
    _createObjectByType('Event', container, id=temp_id, title=event_object.title)
    new_event = container[temp_id]
    new_event.subtitle = event_object.subtitle()
    image_field = new_event.getField('leadImage')
    if image_field is not None:
        image_field.getMutator(new_event)(event_object.getEvent_Image())
    image_caption_field = new_event.getField('leadImage_caption')
    if image_caption_field is not None:
        image_caption_field.getMutator(new_event)(event_object.getEvent_Image_caption())
    new_event.speaker = event_object.speaker()
    new_event.startDate = event_object.start()
    new_event.endDate = event_object.end()
    new_event.rsvpRequired = event_object.getEvent_Rsvp()
    new_event.contactName = event_object.contact_name()
    new_event.contactEmail = event_object.contact_email()
    new_event.contactPhone = event_object.contact_phone()
    new_event.location = event_object.getLocation()
    text = event_object.abstract()
    text += event_object.event_Speaker_detail()
    if event_object.event_Reception:
        text += "<p>There will be a reception folowing the event.</p>"
    if event_object.getEvent_Public():
        text += "<p>This is a public event.</p>"
    if event_object.event_custom_Rsvp:
        text += "<p>To RSVP, please email %s.</p>" % event_object.event_custom_Rsvp.encode('utf-8')
    else:
        text += "<p>To RSVP, please email isaw@nyu.edu.</p>"
    if event_object.event_Invite:
        text += "<p>This is an invitation only event.</p>"
    new_event.setText(text)
    return new_event

def remove_and_rename(event):
    event_id = event.getId
    temp_id = "temp_copy_of_%s" % event_id
    event_object = event.getObject()
    container = aq_parent(event_object)
    container.manage_delObjects([event_id])
    transaction.commit()
    container.manage_renameObject(temp_id, event_id)


def migrate_events(context):
    properties = getToolByName(context, 'portal_properties')
    old_check = properties.site_properties.getProperty('enable_link_integrity_checks', False)
    properties.site_properties.enable_link_integrity_checks = False
    catalog = getToolByName(context, 'portal_catalog')
    lectures = catalog(object_provides=['isaw.events.interfaces.lecture.ILecture'])
    for lecture in lectures:
        new_lecture = copy_generic_fields(lecture)
        new_lecture.eventType = 'Lecture'
        remove_and_rename(lecture)

    performances = catalog(object_provides=['isaw.events.interfaces.performance.IPerformance'])
    for performance in performances:
        new_performance = copy_generic_fields(performance)
        new_performance.eventType = 'Performance'
        remove_and_rename(performance)

    exhibitions = catalog(object_provides=['isaw.events.interfaces.exhibition.IExhibition'])
    for exhibition in exhibitions:
        new_exhibition = copy_generic_fields(exhibition)
        new_exhibition.eventType = 'Exhibition'
        remove_and_rename(exhibition)

    sponsored_events = catalog(object_provides=['isaw.events.interfaces.sponsored.ISponsored'])
    for sponsored in sponsored_events:
        new_sponsored = copy_generic_fields(sponsored)
        new_sponsored.eventType = 'Sponsored'
        if new_sponsored.event_Sponsor_Name:
            if new_sponsored.event_Sponsor_Url:
                new_sponsored.text += '<p>Sponsored by: <a href="%s">%s</a></p>' % (new_sponsored.event_Sponsor_Url, new_sponsored.event_Sponsor_Name)
            else:
                new_sponsored.text += "<p>Sponsored by: %s</p>" % new_sponsored.event_Sponsor_Name
        remove_and_rename(sponsored)

    conferences = catalog(object_provides=['isaw.events.interfaces.conference.IConference'])
    for conference in conferences:
        new_conference = copy_generic_fields(conference)
        new_conference.eventType = 'Conference'
        remove_and_rename(conference)

    seminars = catalog(object_provides=['isaw.events.interfaces.seminar.ISeminar'])
    for seminar in seminars:
        new_seminar = copy_generic_fields(seminar)
        new_seminar.eventType = 'Seminar'
        remove_and_rename(seminar)

    general_events = catalog(object_provides=['isaw.events.interfaces.general.IGeneral'])
    for general in general_events:
        new_general = copy_generic_fields(general)
        new_general.eventType = 'General'
        remove_and_rename(general)

    properties.site_properties.enable_link_integrity_checks = old_check


RENAME = {
    'visiting-scholar-program': {'id': 'visiting-scholars',
                                 'title': 'Visiting Scholars'},
    'graduate-program': {'id': 'graduate-studies',
                         'title': 'Graduate Studies'},
}
RETAIN = set((
    'events',
    'exhibitions',
    'visiting-scholars',
    'graduate-studies',
))


def setup_portal_tabs(context):
    if hasattr(context, 'getSite'):
        if context.readDataFile('isaw_policy.txt') is None:
            return
        portal = context.getSite()
    else:
        portal = getToolByName(context, 'portal_url').getPortalObject()

    ids = set(portal.objectIds())
    for cid in RENAME:
        if cid in ids:
            new_info = RENAME[cid]
            new_id = new_info['id']
            portal.manage_renameObject(cid, new_id)
            transaction.savepoint(optimistic=True)
            new_obj = portal[new_id]
            new_obj.setTitle(new_info['title'])
            new_obj.reindexObject()

    ids = portal.contentIds()
    for cid in ids:
        if cid in ids:
            if cid not in RETAIN:
                obj = portal[cid]
                if not hasattr(aq_base(obj), 'setExcludeFromNav'):
                    continue
                obj.setExcludeFromNav(True)
                obj.reindexObject()


def update_workflow_settings(context):
    wft = getToolByName(context, 'portal_workflow')
    wft.updateRoleMappings()


def setup_portal_transforms(context):
    tid = 'safe_html'

    pt = getToolByName(context, 'portal_transforms')
    if not tid in pt.objectIds(): return

    trans = pt[tid]

    tconfig = trans._config
    tconfig['class_blacklist'] = []
    tconfig['nasty_tags'] = {'meta': '1'}
    tconfig['remove_javascript'] = 0
    tconfig['stripped_attributes'] = ['lang', 'valign', 'halign', 'border',
                                     'frame', 'rules', 'cellspacing',
                                     'cellpadding', 'bgcolor']
    tconfig['stripped_combinations'] = {}
    tconfig['style_whitelist'] = ['text-align', 'list-style-type', 'float',
                                  'width', 'height', 'padding-left',
                                  'padding-right'] # allow specific styles for
                                                   # TinyMCE editing
    tconfig['valid_tags'] = {
        'code': '1', 'meter': '1', 'tbody': '1', 'style': '1', 'img': '0',
        'title': '1', 'tt': '1', 'tr': '1', 'param': '1', 'li': '1',
        'source': '1', 'tfoot': '1', 'th': '1', 'td': '1', 'dl': '1',
        'blockquote': '1', 'big': '1', 'dd': '1', 'kbd': '1', 'dt': '1',
        'p': '1', 'small': '1', 'output': '1', 'div': '1', 'em': '1',
        'datalist': '1', 'hgroup': '1', 'video': '1', 'rt': '1', 'canvas': '1',
        'rp': '1', 'sub': '1', 'bdo': '1', 'sup': '1', 'progress': '1',
        'body': '1', 'acronym': '1', 'base': '0', 'br': '0', 'address': '1',
        'article': '1', 'strong': '1', 'ol': '1', 'script': '1', 'caption': '1',
        'dialog': '1', 'col': '1', 'h2': '1', 'h3': '1', 'h1': '1', 'h6': '1',
        'h4': '1', 'h5': '1', 'header': '1', 'table': '1', 'span': '1',
        'area': '0', 'mark': '1', 'dfn': '1', 'var': '1', 'cite': '1',
        'thead': '1', 'head': '1', 'hr': '0', 'link': '1', 'ruby': '1',
        'b': '1', 'colgroup': '1', 'keygen': '1', 'ul': '1', 'del': '1',
        'iframe': '1', 'embed': '1', 'pre': '1', 'figure': '1', 'ins': '1',
        'aside': '1', 'html': '1', 'nav': '1', 'details': '1', 'u': '1',
        'samp': '1', 'map': '1', 'object': '1', 'a': '1', 'footer': '1',
        'i': '1', 'q': '1', 'command': '1', 'time': '1', 'audio': '1',
        'section': '1', 'abbr': '1'}
    make_config_persistent(tconfig)
    trans._p_changed = True
    trans.reload()
