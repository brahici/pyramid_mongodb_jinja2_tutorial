from pyramid.security import Allow
from pyramid.security import Everyone


class Wiki(object):
    __name__ = None
    __parent__ = None
    __acl__ = [
        (Allow, Everyone, 'view'),
        (Allow, 'group:editors', 'edit'),
    ]

    def __getitem__(self, item):
        page_ = self._wiki.find_one({'name': item})
        if not page_:
            raise KeyError
        page = Page(**page_)
        page.__parent__ = self
        page.__name__ = page.name
        return page

    def __init__(self, request):
        self.request = request
        self._wiki = request.db.wiki
        if not self._wiki.find_one({'name': 'FrontPage'}):
            page = Page(name='FrontPage', data='This is the front page')
            page.__parent__ = self
            page_ = self._wiki.insert(page)

    def __iter__(self):
        pages = [Page(**page_) for page_ in self._wiki.find()]
        for page in pages:
            page.__parent__ = self
        return pages


class Page(dict):
    __name__ = None
    __parent__ = None
    __acl__ = []
    __resource_url__ = None

    def __init__(self, **data):
        self.__name__ = data['name']
        self.update(data)

    def __getattribute__(self, attr):
        try:
            val = dict.__getattribute__(self, attr)
        except:
            # no need to catch KeyError, this exception will be raised
            # if 'attr' is not found
            val = self[attr]
        return val

    def commit(self):
        return self.__parent__._wiki.save(self)

