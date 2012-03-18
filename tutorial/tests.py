import unittest

from pyramid import testing

class PageModelTests(unittest.TestCase):

    def _getTargetClass(self):
        from .resources import Page
        return Page

    def _makeOne(self, name=u'some name', data=u'some data'):
        return self._getTargetClass()(name=name, data=data)

    def test_constructor(self):
        instance = self._makeOne()
        self.assertEqual(instance.name, u'some name')
        self.assertEqual(instance.data, u'some data')

class WikiModelTests(unittest.TestCase):

    def _getTargetClass(self):
        from .resources import Wiki
        return Wiki

    def _makeOne(self, request):
        return self._getTargetClass()(request)

    def test_it(self):
        request = testing.DummyRequest(db=testing.DummyResource(
                wiki=type('DWiki', (object,), {'find_one': lambda x,y:
                        True})()))
        wiki = self._makeOne(request)
        self.assertEqual(wiki.__parent__, None)
        self.assertEqual(wiki.__name__, None)

class ViewWikiTests(unittest.TestCase):
    def test_it(self):
        from .views import view_wiki
        context = testing.DummyResource()
        request = testing.DummyRequest()
        response = view_wiki(context, request)
        self.assertEqual(response.location, 'http://example.com/FrontPage')

class ViewPageTests(unittest.TestCase):
    def _callFUT(self, context, request):
        from .views import view_page
        return view_page(context, request)

    def test_it(self):
        wiki = testing.DummyResource()
        wiki['IDoExist'] = testing.DummyResource()
        context = testing.DummyResource(data='Hello CruelWorld IDoExist')
        context.__parent__ = wiki
        context.__name__ = 'thepage'
        request = testing.DummyRequest()
        info = self._callFUT(context, request)
        self.assertEqual(info['page'], context)
        self.assertEqual(
            info['content'],
            '<div class="document">\n'
            '<p>Hello <a href="http://example.com/add_page/CruelWorld">'
            'CruelWorld</a> '
            '<a href="http://example.com/IDoExist/">'
            'IDoExist</a>'
            '</p>\n</div>\n')
        self.assertEqual(info['edit_url'],
                'http://example.com/thepage/edit_page')

class DummyResource_(dict):
    __parent__ = None
    __name__ = None
    __acl__ = []
    __resource_url__ = None

    def __getattribute__(self, attr):
        try:
            val = dict.__getattribute__(self, attr)
        except:
            val = self[attr]
        return val

    def __init__(self, **kwargs):
        self.update(kwargs)

    def save(self, obj):
        self.__parent__[obj.name] = obj
        return 1

    def commit(self):
        self.__parent__[self.__name__] = self
        return 1

class DummyWiki(testing.DummyResource):
    def __init__(self):
        testing.DummyResource.__init__(self, _wiki=DummyResource_())
        self._wiki.__parent__ = self._wiki

    def __setitem__(self, item, value):
        self._wiki[item] = value

    def __getitem__(self, item):
        return self._wiki[item]

class AddPageTests(unittest.TestCase):
    def _callFUT(self, context, request):
        from .views import add_page
        return add_page(context, request)

    def test_it_notsubmitted(self):
        context = testing.DummyResource()
        request = testing.DummyRequest()
        request.subpath = ['AnotherPage']
        info = self._callFUT(context, request)
        self.assertEqual(info['page'].data,'')
        self.assertEqual(
                info['save_url'],
                request.resource_url(context, 'add_page', 'AnotherPage'))

    def test_it_submitted(self):
        context = DummyWiki()
        request = testing.DummyRequest({'form.submitted':True,
                'body':'Hello yo!'})
        request.subpath = ['AnotherPage']
        self._callFUT(context, request)
        page = context['AnotherPage']
        self.assertEqual(page.data, 'Hello yo!')
        self.assertEqual(page.__name__, 'AnotherPage')
        self.assertEqual(page.__parent__, context)

class EditPageTests(unittest.TestCase):
    def _callFUT(self, context, request):
        from .views import edit_page
        return edit_page(context, request)

    def test_it_notsubmitted(self):
        context = testing.DummyResource()
        request = testing.DummyRequest()
        info = self._callFUT(context, request)
        self.assertEqual(info['page'], context)
        self.assertEqual(info['save_url'],
                request.resource_url(context, 'edit_page'))

    def test_it_submitted(self):
        context = DummyResource_()
        context.__parent__ = DummyWiki()
        request = testing.DummyRequest({'form.submitted':True,
                'body':'Hello yo!'})
        response = self._callFUT(context, request)
        self.assertEqual(response.location, 'http://example.com/')
        self.assertEqual(context.data, 'Hello yo!')

class FunctionalTests(unittest.TestCase):

    viewer_login = '/login?login=viewer&password=viewer' \
                   '&came_from=FrontPage&form.submitted=Login'
    viewer_wrong_login = '/login?login=viewer&password=incorrect' \
                   '&came_from=FrontPage&form.submitted=Login'
    editor_login = '/login?login=editor&password=editor' \
                   '&came_from=FrontPage&form.submitted=Login'

    def setUp(self):
        from . import main

        settings = {
                'db_uri': 'mongodb://localhost',
                'db_name': 'tutorial_tests',
                'pyramid.includes': ['pyramid_tm', ],
            }

        app = main({}, **settings)
        self.cnx = app.registry.settings['db_conn']
        db = self.cnx[settings['db_name']]
        from webtest import TestApp
        self.testapp = TestApp(app)

    def tearDown(self):
        self.cnx.drop_database('tutorial_tests')

    def test_root(self):
        res = self.testapp.get('/', status=302)
        self.assertEqual(res.location, 'http://localhost/FrontPage')

    def test_FrontPage(self):
        res = self.testapp.get('/FrontPage', status=200)
        self.assertTrue('FrontPage' in res.body)

    def test_unexisting_page(self):
        res = self.testapp.get('/SomePage', status=404)
        self.assertTrue('Not Found' in res.body)

    def test_successful_log_in(self):
        res = self.testapp.get( self.viewer_login, status=302)
        self.assertEqual(res.location, 'http://localhost/FrontPage')

    def test_failed_log_in(self):
        res = self.testapp.get( self.viewer_wrong_login, status=200)
        self.assertTrue('login' in res.body)

    def test_logout_link_present_when_logged_in(self):
        res = self.testapp.get( self.viewer_login, status=302)
        res = self.testapp.get('/FrontPage', status=200)
        self.assertTrue('Logout' in res.body)

    def test_logout_link_not_present_after_logged_out(self):
        res = self.testapp.get( self.viewer_login, status=302)
        res = self.testapp.get('/FrontPage', status=200)
        res = self.testapp.get('/logout', status=302)
        self.assertTrue('Logout' not in res.body)

    def test_anonymous_user_cannot_edit(self):
        res = self.testapp.get('/FrontPage/edit_page', status=200)
        self.assertTrue('Login' in res.body)

    def test_anonymous_user_cannot_add(self):
        res = self.testapp.get('/add_page/NewPage', status=200)
        self.assertTrue('Login' in res.body)

    def test_viewer_user_cannot_edit(self):
        res = self.testapp.get( self.viewer_login, status=302)
        res = self.testapp.get('/FrontPage/edit_page', status=200)
        self.assertTrue('Login' in res.body)

    def test_viewer_user_cannot_add(self):
        res = self.testapp.get( self.viewer_login, status=302)
        res = self.testapp.get('/add_page/NewPage', status=200)
        self.assertTrue('Login' in res.body)

    def test_editors_member_user_can_edit(self):
        res = self.testapp.get( self.editor_login, status=302)
        res = self.testapp.get('/FrontPage/edit_page', status=200)
        self.assertTrue('Editing' in res.body)

    def test_editors_member_user_can_add(self):
        res = self.testapp.get( self.editor_login, status=302)
        res = self.testapp.get('/add_page/NewPage', status=200)
        self.assertTrue('Editing' in res.body)

    def test_editors_member_user_can_view(self):
        res = self.testapp.get( self.editor_login, status=302)
        res = self.testapp.get('/FrontPage', status=200)
        self.assertTrue('FrontPage' in res.body)

