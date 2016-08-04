import json
import argparse
import transaction

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManager import setSecurityPolicy
from Products.CMFCore.tests.base.security import PermissiveSecurityPolicy
from Testing.makerequest import makerequest
from zope.component.hooks import setSite

from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobImage


FIELDS = ['title',
          'description',
          'context',
          'date',
          'not_before',
          'not_after',
          'dimensions',
          'inventory_num',
          'lender',
          'lender_link',
          'medium',
          'notes',
          'image',
          'text',
          'label',
          ]


def spoofRequest(app):
    _policy = PermissiveSecurityPolicy()
    setSecurityPolicy(_policy)
    user = app.acl_users.getUser('admin')
    newSecurityManager(None, user.__of__(app.acl_users))
    return makerequest(app)


def getSite(app):
    site = app.unrestrictedTraverse("Plone")
    site.setupCurrentSkin(app.REQUEST)
    setSite(site)
    return site


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create Exhibition Objects.')
    parser.add_argument('--dry-run', action='store_true', default=False,
                        dest='dry_run', help='No changes will be made.')
    parser.add_argument('file', type=file, help='Path to JSON import file')
    parser.add_argument('-c', help='Optional Zope configuration file.')

    try:
        args = parser.parse_args()
    except IOError, msg:
        parser.error(str(msg))

    json_file = args.file
    json_dir = '.'
    if '/' in json_file.name:
        json_dir = json_file.name.rsplit('/', 1)[0]
    items = json.loads(json_file.read()).get('items', [])

    app = spoofRequest(app)
    site = getSite(app)

    print
    print "Starting batch content creation..."
    print

    for item in items:
        path, values = item.items()[0]
        if path.startswith('/'):
            path = path[1:]
        print "Creating Exhibition Object at path: {}".format(path)
        if 'title' not in values:
            print "Title is a required field. Skipping."
            print
            continue
        if 'inventory_num' not in values:
            print "Inventory Number (inventory_num) is a required field. Skipping."
            print
            continue
        try:
            container = site.restrictedTraverse(path.encode('utf-8'))
        except (KeyError, AttributeError):
            print "Creation path not found. Skipping."
            print
            continue
        fields = {}
        for field in FIELDS:
            if field in values:
                value = values[field]
                if field == 'image':
                    try:
                        filename = "{}/{}".format(json_dir, value)
                        value = NamedBlobImage(open(filename).read())
                    except IOError, msg:
                        print "Invalid path for image: {}".format(str(msg))
                        continue
                fields[field] = value
        item = createContentInContainer(container,
                                        'isaw.exhibitions.object',
                                        **fields)
        print 'Created Exhibition Object with id "{}"'.format(item.id)
        print

    if args.dry_run:
        print "Dry run. No changes made in Plone."
    else:
        print "Updated content in Plone."
        transaction.commit()
