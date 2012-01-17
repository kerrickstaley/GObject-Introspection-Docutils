# -*- Mode: Python -*-

import xml.sax
import codecs
import logging
from contextlib import contextmanager
from lxml import etree

# uncomment to enable debug logging
# logging.basicConfig(level=logging.DEBUG)

def write_mallard(girFilename, lang, writerFactory=None):
    """Parse a .gir file, creating a set of Mallard documentation files.
    
    Parameters:
    girFilename   -- the path to the .gir file
    lang          -- programming language to create docs for
    writerFactory -- a contextmanager that takes a Mallard page ID and yields an open file or some other writable object; see tmpWriterFactory below for an example. The default writerFactory writes files to /tmp/ID.page.
    """
    
    if writerFactory is None:
        # a writerFactory for testing purposes that writes the files to /tmp/
        @contextmanager
        def tmpWriterFactory(pageId):
            f = codecs.open('/tmp/{}.page'.format(pageId), 'w', 'utf-8')
            try:
                yield f
            finally:
                f.close()
        
        writerFactory = tmpWriterFactory
    
    contentHandler = _MallardContentHandler(lang, writerFactory)
    xml.sax.parse(girFilename, contentHandler)

# definitions for working with namespaces using the lxml library
# see http://lxml.de/tutorial.html#namespaces for more details
_MALLARD_NAMESPACE = 'http://projectmallard.org/1.0/'
_MALLARD = '{' + _MALLARD_NAMESPACE + '}'
_UI_NAMESPACE = 'http://projectmallard.org/experimental/ui/'
_UI = '{' + _UI_NAMESPACE + '}'
_NSMAP = {None : _MALLARD_NAMESPACE, 'ui' : _UI_NAMESPACE}

# list of elements that get their own page
_PAGE_ELEMENTS = ('namespace', 'class', 'interface', 'record', 'union', 'function', 'glib:signal', 'bitfield', 'enumeration', 'constructor', 'method', 'virtual-method', 'callback')
# list of elements that get their own page and have a parent page
_PAGE_ELEMENTS_WITH_PARENT = _PAGE_ELEMENTS[1:]

class _Page(object):
    """Simple class representing a Mallard page.
    
    The only reason we don't use a namedtuple for this is because we add arbitrary properties to it in _MallardContentHandler.
    
    Properties:
    root  -- The etree.Element that is the root of the page.
    etree -- The etree.ElementTree that represents the whole document.
    """
    
    def __init__(self, root):
        """Initialize the page, given the root element.
        """
        self.root = root
        self.etree = etree.ElementTree(root)


class _MallardContentHandler(xml.sax.handler.ContentHandler):
    def __init__(self, lang, writerFactory):
        self._writerFactory = writerFactory
        
        # _tagStack is a stack that holds tag names
        # it is pushed (and later popped) for every tag
        self._tagStack = []
        
        # _textStack is a stack that is the concatenation of all the text nodes found in each tag that is currently being processed
        # it is pushed (and later popped) for every tag
        self._textStack = []
        
        # _pageStack is a stack of Pages
        # it is pushed (and later popped) for every tag that has its own page
        self._pageStack = []
    
    #######################################################
    #### Methods for SAX ContentHandler implementation ####
    #######################################################
    
    def startDocument(self):
        logging.debug('startDocument()')
    
    def endDocument(self):
        logging.debug('endDocument()')
    
    def startElement(self, tag, attrs):
        logging.debug('startElement(): tag = {}; attrs[\'name\'] = {}'.format(tag, attrs['name'] if attrs.has_key('name') else '(none)'))
    
        self._tagStack.append(tag)
        self._textStack.append('')
        
        # create page and set page.id
        if tag in _PAGE_ELEMENTS:
            self._pageStack.append(_Page(etree.Element(_MALLARD + 'page', nsmap=_NSMAP)))
            
            if tag in ('namespace', ):
                self._page.id = attrs['name']
            else:
                parentId = self._pageStack[-2].id
                self._page.id = '{}.{}'.format(attrs['name'], parentId)
            
            self._root.set('id', self._page.id)
            self._root.set('type',  'guide')
            self._root.set('style', tag)
        
        # set page.title
        if tag in _PAGE_ELEMENTS:
            self._page.title = etree.Element('title')
            self._page.title.text = attrs['name']
        
        # set page.doc
        if tag in _PAGE_ELEMENTS:
            self._page.doc = None
        
        # set page.info, which contains a link to the parent page
        if tag in _PAGE_ELEMENTS_WITH_PARENT:
            self._page.info = etree.Element('info')
            
            etree.SubElement(self._page.info,
                             'link',
                             type='guide',
                             xref=self._parentPage.id, 
                             group=tag)
        
        # set page.classes, which is a list of classes
        if tag in ('namespace', ):
            self._page.classes = self._linkSection('Classes', 'class')
        
        # set page.functions, which is a list of functions
        if tag in ('namespace', ):
            self._page.functions = self._linkSection('Functions', 'function')
        
        # set page.constants, which is a list of constants
        if tag in ('namespace', ):
            self._page.constants = self._varSection('Constants')
        
        # set page.constructors, which is a list of constructors
        if tag in ('class', ):
            self._page.constructors = self._linkSection('Constructors', 'constructor')
        
        # set page.methods, which is a list of methods
        if tag in ('class', 'interface'):
            self._page.methods = self._linkSection('Methods', 'method')
        
        # set page.properties, which is a list of properties
        if tag in ('class', 'interface'):
            self._page.properties = self._varSection('Properties')
        
        # set page.parameters, which is a list of method parameters
        if tag in ('function', 'glib:signal', 'constructor', 'method', 'virtual-method', 'callback'):
            self._page.parameters = self._varSection('Parameters')
        
        # set page.members, which is a list of bitfield/enumeration members
        if tag in ('bitfield', 'enumeration'):
            self._page.members = self._membSection('Members')
        
        # save the name of a variable so that an entry can be created later in endElement
        if tag in ('constant', 'parameter', 'property', 'member'):
            # some elements (like a varargs parameter) don't have a name
            self._tmpName = attrs['name'] if attrs.has_key('name') else ''
            self._tmpDocNode = etree.Element('p')
        
        # save the name/value of an bitfield/enumeration member so that it can be created later in endElement
        if tag in ('member', ):
            self._tmpName = attrs['name']
            self._tmpValue = attrs['value']
            self._tmpDocNode = etree.Element('p')
        
        # begin the entry for a property
        #if tag in ('property', ):
        #    item = etree.SubElement(self._page.properties, 'item')
        #    etree.SubElement(item, 'title').text = attrs['name']
        
        # save the type of a variable so that an entry can be created later in endElement
        if tag in ('type', ):
            self._tmpType = attrs['name'] if attrs.has_key('name') else '(none)'
        
    def endElement(self, tag):
        logging.debug('endElement(): tag = {}'.format(tag))
        
        # add page.info to the output page
        if tag in _PAGE_ELEMENTS_WITH_PARENT:
            self._root.append(self._page.info)
        
        # add page.title to the output page
        if tag in _PAGE_ELEMENTS:
            self._root.append(self._page.title)
        
        # add page.doc to the output page
        if tag in _PAGE_ELEMENTS:
            if self._page.doc is not None:
                self._root.append(self._page.doc)
        
        # custom elements for namespace pages
        if tag in ('namespace', ):
            self._root.append(self._page.classes)
            self._root.append(self._page.constants)
        
        # custom elements for class pages
        if tag in ('class', ):
            self._root.append(self._page.constructors)
            self._root.append(self._page.methods)
            self._root.append(self._page.properties)
            #self._root.append(self._page.signals)
            #self._root.append(self._page.others)
        
        # add page.parameters to the element
        if tag in ('function', 'glib:signal', 'constructor', 'method', 'virtual-method', 'callback'):
            self._root.append(self._page.parameters)
        
        # add page.members to the element
        if tag in ('bitfield', 'enumeration'):
            self._root.append(self._page.members)
        
        if tag in ('doc', ):
            doc = etree.Element('p')
            doc.text = self._text
            
            # create page.doc
            if self._parentTag in _PAGE_ELEMENTS:
                self._page.doc = doc
            
            # save the documentation for a variable so that an entry can be created later in endElement
            if self._parentTag in ('constant', 'parameter', 'property', 'member'):
                self._tmpDocNode = doc
        
        # create an entry for a constant
        if tag in ('constant', ):
            # taking the element at index 2 gives us the <tbody>
            self._page.constants[2].append(self._varEntry(self._tmpName, self._tmpType, self._tmpDocNode))
        
        # create an entry for a parameter
        if tag in ('parameter', ):
            # taking the element at index 2 gives us the <tbody>
            self._page.parameters[2].append(self._varEntry(self._tmpName, self._tmpType, self._tmpDocNode))
        
        # create an entry for a property
        if tag in ('property', ):
            # taking the element at index 2 gives us the <tbody>
            self._page.properties[2].append(self._varEntry(self._tmpName, self._tmpType, self._tmpDocNode))
        
        # create an entry for a member
        if tag in ('member', ):
            # taking the element at index 2 gives us the <tbody>
            self._page.members[2].append(self._membEntry(self._tmpName, self._tmpValue, self._tmpDocNode))
        
        # add the title to a varargs parameter
        if tag in ('varargs', ):
            self._tmpName = '(varargs)'
        
        # output the page
        if tag in _PAGE_ELEMENTS:
            with self._writerFactory(self._page.id) as writer:
                self._page.etree.write(writer, pretty_print=True)
            
            self._pageStack.pop()
        
        self._tagStack.pop()
        self._textStack.pop()
    
    def characters(self, content):
        # content may be in Unicode format, but the .format() method of
        # an ASCII string can only accept other ASCII strings, so use
        # repr to escape it
        logging.debug('characters({})'.format(repr(content)))
        
        #self._text += content                # this doesn't work. I have no idea why. FIXME
        #self._text = self._text + content    # this likewise doesn't work
        self._textStack[-1] += content
    
    #########################
    #### Private Methods ####
    #########################
    
    @property
    def _page(self):
        return self._pageStack[-1]
    
    @property
    def _parentPage(self):
        return self._pageStack[-2]
    
    @property
    def _root(self):
        return self._page.root
    
    @property
    def _text(self):
        return self._textStack[-1]
    
    @_text.setter
    def _text(self, value):
        self._textStack[-1] = value
    
    @property
    def _parentTag(self):
        return self._tagStack[-2]
    
    # create a section where other topics (children of this topic) can link back to this one
    @staticmethod
    def _linkSection(title, groups, expanded=True):
        rv = etree.Element('links')
        rv.set('type', 'topic')
        rv.set(_UI + 'expanded', 'yes' if expanded else 'no')
        rv.set('groups', groups)
        etree.SubElement(rv, 'title').text = title
        return rv
    
    # create a table that lists variables
    # returns the table (which hasn't been inserted into any document yet)
    @staticmethod
    def _varSection(title, expanded=True):
        table = etree.Element('table', shade='cols')
        table.set(_UI + 'expanded', 'yes' if expanded else 'no')
        etree.SubElement(table, 'title').text = title
        
        thead = etree.SubElement(table, 'thead')
        tr = etree.SubElement(thead, 'tr')
        
        for text in ('Type', 'Name', 'Description'):
            td = etree.SubElement(tr, 'td')
            etree.SubElement(td, 'p').text = text
        
        etree.SubElement(table, 'tbody')
        
        return table
    
    # create a row in a table that lists variables
    @staticmethod
    def _varEntry(name, type, docNode):
        tr = etree.Element('tr')
        
        td = etree.SubElement(tr, 'td')
        etree.SubElement(td, 'p').text = type
        
        td = etree.SubElement(tr, 'td')
        etree.SubElement(td, 'p').text = name
        
        td = etree.SubElement(tr, 'td')
        td.append(docNode)
        
        return tr
    
    # create a table that lists bitfield/enumeration members
    # returns the table (which hasn't been inserted into any document yet)
    @staticmethod
    def _membSection(title):
        table = etree.Element('table', shade='cols')
        etree.SubElement(table, 'title').text = title
        
        thead = etree.SubElement(table, 'thead')
        tr = etree.SubElement(thead, 'tr')
        
        for text in ('Value', 'Name', 'Description'):
            td = etree.SubElement(tr, 'td')
            etree.SubElement(td, 'p').text = text
        
        etree.SubElement(table, 'tbody')
        
        return table
    
    # create a row in a table that lists bitfield/enumeration members
    @staticmethod
    def _membEntry(name, value, docNode):
        tr = etree.Element('tr')
        
        td = etree.SubElement(tr, 'td')
        etree.SubElement(td, 'p').text = value
        
        td = etree.SubElement(tr, 'td')
        etree.SubElement(td, 'p').text = name
        
        td = etree.SubElement(tr, 'td')
        td.append(docNode)
        
        return tr
