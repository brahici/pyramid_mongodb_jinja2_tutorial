from persistent import Persistent
from persistent.mapping import PersistentMapping

from pyramid.security import Allow
from pyramid.security import Everyone


class Wiki(PersistentMapping):
    __name__ = None
    __parent__ = None
    __acl__ = [
        (Allow, Everyone, 'view'),
        (Allow, 'group:editors', 'edit'),
    ]


class Page(Persistent):
    def __init__(self, data):
        self.data = data

def appmaker(zodb_root):
    if not 'app_root' in zodb_root:
        app_root = Wiki()
        front_page = Page('Front page')
        app_root['FrontPage'] = front_page
        front_page.__name__ = 'FrontPage'
        front_page.__parent__ = app_root
        zodb_root['app_root'] = app_root
        import transaction
        transaction.commit()
    return zodb_root['app_root']

