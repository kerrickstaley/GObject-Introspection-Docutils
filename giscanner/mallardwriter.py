# Copyright (C) 2012 Kerrick Staley
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met: 
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer. 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution. 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# As a special exception, you may re-license the code under the GPL version 2.0
# or higher, removing the above license and substituting the GPL header, as
# long as you retain the copyright notice.

import xml.sax
import codecs
import logging
import re
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
    
    # parse the .gir file in two passes.
    
    # the first pass generates some name maps, which are needed when putting hyperlinks into docStrings
    # for example, #GtkWindow needs to be converted to <link xref="Gtk.Window">Window</link>
    pass1Handler = _NameMapContentHandler()
    xml.sax.parse(girFilename, pass1Handler)
    
    nameConverter = _PythonNameConverter(pass1Handler.namespace, pass1Handler.glibToName, pass1Handler.glibToId)
    
    # the second pass actually creates the Mallard files, using the name maps generated in the first pass
    pass2Handler = _MallardContentHandler(lang, nameConverter, writerFactory)
    xml.sax.parse(girFilename, pass2Handler)

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

# types of identifiers:
# ctype: this is the type used by C code. Examples are gint, ClutterActor, ClutterActorBox*, gchar*
# giname: this is of the form Clutter.Actor
# glib:type-name: this is of the form ClutterActor. It is only mentioned in the definition of the class, interface, bitfield, or enumeration
class _NameConverter(object):
    """Performs programming-language-specific name conversions.
    
    In theory, all you should have to do in order to support a new language is define a new _NameConverter (and make trivial modifications to the command-line parsing).
    """
    
    def getId(self, tag, name, parentId):
        """Get a page ID for a class/enumeration/etc. that has just been encountered when parsing
        
        Parameters:
            tag      -- the type of tag (class, namespace, etc.)
            name     -- the tag's name attribute (e.g. Window)
            parentId -- the ID of the parent page (the namespace's ID if the tag is a class, the class's ID if the tag is a method, etc.)
        
        Returns:
            the page ID
        """
    
    def getNameId(self, glibName):
        """Get a name and a page ID for a class/enumeration/etc. given its GLib Typename.
        
        The name is a human-readable name; the page ID is used by Mallard when cross-linking pages.
        
        Parameters:
            glibName -- the GLib Typename (e.g. GtkWindow; this is the "glib:type-name" from a <class> tag in a .gir file, and is preceded by a hash in a <doc> tag)
        
        Returns:
            a (name, pageId) tuple
        """
        
        pass
    
    def formatDoc(self, rawDoc):
        """Convert a docString to a hyperlinked lxml element.
        
        Parameters:
            rawDoc -- a string containing the raw docString, e.g. "Creates a new #GtkAboutDialog."
        
        Return value
            a etree.Element with the converted docString, e.g. etree.XML("<p>Creates a new <link xref="Gtk.AboutDialog">AboutDialog</link>.</p>")
        """
    
    def typeToNode(self, typeString, isArray=False, arrayLength=0):
        """Convert a type name (in the GIName format) to a hyperlinked lxml element.
        
        GIName is roughly the same format as a Python identifier (e.g. Gtk.Window or just Window (if it's inside the Gtk <namespace> tag). You see GINames in <parameter> tags.
        
        Parameters:
            typeString  -- the type name (in the GIName format)
            isArray     -- (optional) True if it's actually an array of the type
            arrayLength -- (optional) if it's an array, the length of that array. The special value 0 means the array has variable length
        """

class _PythonNameConverter(_NameConverter):
    """A _NameConverter for Python.
    """
    def __init__(self, namespace, glibToName, glibToId):
        self._namespace = namespace
        self._glibToName = glibToName
        self._glibToId = glibToId
    
    def getId(self, tag, name, parentId=None):
        if tag in ('namespace', ):
            return name
        elif tag in _PAGE_ELEMENTS_WITH_PARENT:
            return '{}.{}'.format(parentId, name)
        else:
            return '#'
    
    def getNameId(self, glibName):        
        if self._glibToName.has_key(glibName):
            return self._glibToName[glibName], self._glibToId[glibName]
        else:
            return glibName, '#'
    
    def formatDoc(self, rawDoc):
        # Handle these:
        #     @Name is a parameter
        #     #Name:name2 is a property (and name2 can have dashes)
        #     #Name is a class, interface, record, union, enumeration, or bitfield
        #     <structname>Name</structname> is the same as #Name
        #     %Name is a constant, enumeration/bitfield member, or one of the special values %TRUE, %FALSE, %NONE. Maybe it could be other things, IDK
        #     Name() is a function or method
        
        patterns = ['@\w+',
                    '#\w+:[-\w]+',
                    '#\w+',
                    '<structname>\w+</structname>',
                    '%\w+',
                    '\w+\(\)']
        
        splitPattern = '(' + '|'.join(patterns) + ')'
        
        textList = re.split(splitPattern,
                            rawDoc)
        
        logging.debug('formatDoc(): textList is ' + repr(textList))
        
        docNode = etree.Element('p')
        docNode.text = textList[0]
        
        # re.split() is interesting; see its documentation if you're unsure how this works
        for i in range(1, len(textList), 2):
            symbol = textList[i]
            
            # special case for %TRUE, %FALSE, %NULL
            if re.match('%(TRUE|FALSE|NULL)', symbol):
                node = etree.SubElement(docNode, 'em', style='strong')
                node.text = {'%TRUE':'True', '%FALSE':'False', '%NULL':'None'}[symbol]
            
            # @symbol is a parameter
            elif re.match('@\w+', symbol):
                node = etree.SubElement(docNode, 'em')
                node.text = symbol[1:]
            
            # #Name:name2 is a property
            elif re.match('#\w+:[-\w]+', symbol):
                classSymbol, propertyName = symbol.split(':')
                className, xref = self.getNameId(glibName=classSymbol[1:])
                
                name = className + ':' + propertyName
                
                node = etree.SubElement(docNode, 'link', xref=xref)
                node.text = name
            
            # everything else requires a hyperlink
            else:
                linkPatterns = [r'^#(\w+)$',
                                r'^<structname>(\w+)</structname>$',
                                r'^%(\w+)$',
                                r'^(\w+)\(\)$']
                
                for pattern in linkPatterns:
                    m = re.match(pattern, symbol)
                    if m:
                        name, xref = self.getNameId(glibName=m.group(1))
                        
                        node = etree.SubElement(docNode, 'link', xref=xref)
                        node.text = name
            
            # add the unformatted documentation that lies between this node and the next one
            node.tail = textList[i + 1]
        
        return docNode
    
    def typeToNode(self, typeString, isArray=False, arrayLength=0):
        rv = etree.Element('p')
        
        arrayStr = str(arrayLength) if arrayLength > 0 else ''
        arrayStr = '[' + arrayStr + ']' if isArray else ''
        
        if typeString == 'none':
            etree.SubElement(rv, 'em', style='strong').text = 'None'
        
        elif typeString == 'gboolean':
            rv.text = 'bool' + arrayStr
        
        elif typeString == 'gfloat' or typeString == 'gdouble':
            rv.text = 'float' + arrayStr
        
        elif typeString == 'utf8':
            rv.text = 'str' + arrayStr
        
        elif re.match(r'gu?(char|short|int|long|size|ssize)(8|16|32|64)?', typeString):
            rv.text = 'int' + arrayStr
        
        else:
            pageId = self._namespace + '.' + typeString                 # FIXME this sucks, mostly because GObject Introspection uses *way* too many different naming conventions
            etree.SubElement(rv, 'link', xref=pageId).text = typeString + arrayStr
        
        return rv
    
    def _spanNode(self, text):
        rv = etree.Element('span')
        rv.text = text
        
        return rv
    
    def _pNode(self, text):
        rv = etree.Element('p')
        rv.text = text
        
        return rv
    
    def _emNode(self, text):
        rv = etree.Element('em')
        rv.text = text
        
        return rv
    
    def _linkNode(self, glibName):
        name, xref = self.getNameId(glibName)
        
        rv = etree.Element('link', xref=xref)
        rv.text = name
        
        return rv

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

class _NameMapContentHandler(xml.sax.handler.ContentHandler):
    """Used during the first pass over the .gir file to build two dicts.
    
    There are 3 types of class/interface names (that we care about):
    GLib Typename -- Used in the .gir file's docStrings (which come from the C annotations). Uniquely identifies the class/interface. Is the "official" name used by the GObject system.
    Name          -- Human-readable name (not necessarily unique outside its namespace). Used in higher-level (Python, Javascript, etc.) programs.
    Namespace     -- Together with the name, uniquely identifies the class/interface.
    
    When a GLib Typename is mentioned in a docString during the main parsing pass, it may not have been encountered yet.
    So, we need to make a preliminary pass and generate these maps.
    
    This class builds a (GLib Typename)->(Name) map and a (GLib Typename)->(Page ID) map.
    
    Note: C programs don't care about the name/namespace (and hence this class doesn't need to be used when generating C documentation).
    
    Properties:
    glibToName    -- the (GLib Typename)->(Name) map
    glibToId      -- the (GLib Typename)->(Page ID) map
    """
    
    def __init__(self):
        self.namespace = ''
        self.glibToName = {}
        self.glibToId = {}
    
    #######################################################
    #### Methods for SAX ContentHandler implementation ####
    #######################################################
    
    def startElement(self, tag, attrs):
        logging.debug('_NameMapContentHandler.startElement(): tag = {}; attrs[\'name\'] = {}'.format(tag, attrs['name'] if attrs.has_key('name') else '(none)'))
        
        # set self._namespace for future reference
        if tag in ('namespace', ):
            self.namespace = attrs['name']
        
        # set self._parentName for future reference. self._parentName is the name of the class, bitfield, etc. where a method, member, etc. is defined in
        if tag in ('class', 'interface', 'record', 'union', 'bitfield', 'enumeration'):
            self._parentName = attrs['name']
        
        # put entries into maps
        if tag in ('class', 'interface', 'record', 'union', 'bitfield', 'enumeration'):
            # the record ActionClass doesn't have a glib:type-name, which I don't understand. FIXME
            if attrs.has_key('glib:type-name'):
                glibName = attrs['glib:type-name']
                self.glibToName[glibName] = attrs['name']
                self.glibToId[glibName] = '{}.{}'.format(self.namespace, attrs['name'])
        
        # put entries into maps
        # c:identifier is not really the GLib Typename AFAIK, but it's what's used in docStrings.
        if tag in ('member', ):
            glibName = attrs['c:identifier']
            self.glibToName[glibName] = '{}.{}'.format(self._parentName, attrs['name'])
            self.glibToId[glibName] = '{}.{}'.format(self.namespace, self._parentName)
        
        # put entries into maps
        # c:identifier is not really the GLib Typename AFAIK, but it's what's used in docStrings.
        if tag in ('function', ):
            glibName = attrs['c:identifier']
            # a "function" can be either a static method (defined within a class) or an actual function (defined within a namespace)
            if hasattr(self, '_parentName'):
                self.glibToName[glibName] = '{}.{}'.format(self._parentName, attrs['name'])
                self.glibToId[glibName] = '{}.{}.{}'.format(self.namespace, self._parentName, attrs['name'])
            else:
                self.glibToName[glibName] = attrs['name']
                self.glibToId[glibName] = '{}.{}'.format(self.namespace, attrs['name'])
        
        # put entries into maps
        # c:identifier is not really the GLib Typename AFAIK, but it's what's used in docStrings.
        if tag in ('method', ):
            glibName = attrs['c:identifier']
            self.glibToName[glibName] = '{}.{}'.format(self._parentName, attrs['name'])
            self.glibToId[glibName] = '{}.{}.{}'.format(self.namespace, self._parentName, attrs['name'])
    
    def endElement(self, tag):
        # need to do this because of the hasattr() above 
        if tag in ('class', 'interface', 'record', 'union'):
            del self._parentName

class _MallardContentHandler(xml.sax.handler.ContentHandler):
    """Used during the second pass over the .gir file. Parses the file and writes the Mallard output.
    """
    def __init__(self, lang, nameConverter, writerFactory):
        self._nameConverter = nameConverter
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
        logging.debug('_MallardContentHandler.startElement(): tag = {}; attrs[\'name\'] = {}'.format(tag, attrs['name'] if attrs.has_key('name') else '(none)'))
        
        self._tagStack.append(tag)
        self._textStack.append('')
        
        # initialize page
        if tag in _PAGE_ELEMENTS:
            # create page
            self._pageStack.append(_Page(etree.Element(_MALLARD + 'page', nsmap=_NSMAP)))
        
            # set page.id
            parentId = self._parentPage.id if tag != 'namespace' else None
            self._page.id = self._nameConverter.getId(tag, attrs['name'], parentId)
            
            # set attributes on the output page
            self._root.set('id', self._page.id)
            self._root.set('type',  'guide')
            self._root.set('style', tag)
        
            # set page.title
            self._page.title = etree.Element('title')
            self._page.title.text = attrs['name']
        
            # clear page.docNode
            self._page.docNode = None
        
        # set page.info, which contains a link to the parent page
        if tag in _PAGE_ELEMENTS_WITH_PARENT:
            self._page.info = etree.Element('info')
            
            etree.SubElement(self._page.info,
                             'link',
                             type='guide',
                             xref=self._parentPage.id, 
                             group=tag)
        
        # set page.constants, which is a list of constants
        if tag in ('namespace', ):
            self._page.constants = self._varSection('Constants')
        
        # set page.properties, which is a list of properties
        if tag in ('class', 'interface'):
            self._page.properties = self._varSection('Properties')
        
        # set page.parameters, which is a list of method parameters
        if tag in ('function', 'glib:signal', 'constructor', 'method', 'virtual-method', 'callback'):
            self._page.parameters = self._varSection('Parameters')
        
        # set page.members, which is a list of bitfield/enumeration members
        if tag in ('bitfield', 'enumeration'):
            self._page.members = self._membSection('Members')
        
        # save the name 
        if tag in ('constant', 'parameter', 'property', 'member'):
            # varargs parameter and return values don't have names
            self._tmpName = attrs['name'] if attrs.has_key('name') else ''
        
        # save the name/value of an bitfield/enumeration member so that an entry can be created later in endElement
        if tag in ('member', ):
            self._tmpName = attrs['name']
            self._tmpValue = attrs['value']
        
        # save the length of an array so that it can be used when creating the type later
        if tag in ('array', ):
            if attrs.has_key('length'):
                self._tmpArrayLength = int(attrs['length'])
            elif attrs.has_key('fixed-size'):
                self._tmpArrayLength = int(attrs['fixed-size'])
            else:
                self._tmpArrayLength = 0    # 0 is a special value meaning "variable length"
            
        # save the type of a variable so that an entry can be created later in endElement
        if tag in ('type', ):
            typeString = attrs['name'] if attrs.has_key('name') else '(none)'
            if self._parentTag != 'array':
                self._tmpTypeNode = self._nameConverter.typeToNode(typeString)
            else:
                self._tmpTypeNode = self._nameConverter.typeToNode(typeString, isArray=True, arrayLength=self._tmpArrayLength)
        
    def endElement(self, tag):
        logging.debug('endElement(): tag = {}'.format(tag))
        
        # add page.info to the output page
        if tag in _PAGE_ELEMENTS_WITH_PARENT:
            self._root.append(self._page.info)
        
        # add page.title to the output page
        if tag in _PAGE_ELEMENTS:
            self._root.append(self._page.title)
        
        # add page.docNode to the output page
        if tag in _PAGE_ELEMENTS:
            if self._page.docNode is not None:
                self._root.append(self._page.docNode)
        
        # custom elements for namespace pages
        if tag in ('namespace', ):
            self._root.append(self._linkSection('Classes', 'class'))
            self._root.append(self._linkSection('Functions', 'function'))
            self._root.append(self._linkSection('Other', '#first #default #last'))
            self._root.append(self._page.constants)
        
        # add a section for constructors to the output page
        if tag in ('class', ):
            self._root.append(self._linkSection('Constructors', 'constructor'))
        
        # add a section for methods to the output page
        if tag in ('class', 'interface'):
            self._root.append(self._linkSection('Methods', 'method'))
        
        # add a section for class methods to the output page
        if tag in ('class', 'interface'):
            self._root.append(self._linkSection('Class Methods', 'function'))
        
        # add a section for signals to the output page
        if tag in ('class', 'interface'):
            self._root.append(self._linkSection('Signals', 'glib:signal'))
        
        # add page.properties to the output page
        if tag in ('class', 'interface'):
            self._root.append(self._page.properties)
        
        # add page.parameters to the element
        if tag in ('function', 'glib:signal', 'constructor', 'method', 'virtual-method', 'callback'):
            self._root.append(self._page.parameters)
        
        # add page.returnValue to the element
        if tag in ('function', 'method', 'virtual-method'):
            self._root.append(self._page.returnValue)
        
        # add page.members to the element
        if tag in ('bitfield', 'enumeration'):
            self._root.append(self._page.members)
        
        # add a section for other things to the element (ideally should be empty):
        if tag in ('class', 'interface'):
            self._root.append(self._linkSection('Other', '#first #default #last'))
        
        # process a doc tag
        if tag in ('doc', ):
            docNode = self._nameConverter.formatDoc(self._text)
            
            # create page.docNode
            if self._parentTag in _PAGE_ELEMENTS:
                self._page.docNode = docNode
            
            # save the documentation for a variable so that an entry can be created later in endElement
            if self._parentTag in ('constant', 'parameter', 'property', 'member', 'return-value'):
                self._tmpDocNode = docNode
        
        # get the docNode
        if tag in ('constant', 'parameter', 'property', 'member', 'return-value'):
            if hasattr(self, '_tmpDocNode'):
                docNode = self._tmpDocNode
                del self._tmpDocNode
            else:
                docNode = etree.Element('p')
        
        # create an entry for a constant
        if tag in ('constant', ):
            # taking the element at index 2 gives us the <tbody>
            self._page.constants[2].append(self._varEntry(self._tmpName, self._tmpTypeNode, docNode))
        
        # create an entry for a parameter
        if tag in ('parameter', ):
            # taking the element at index 2 gives us the <tbody>
            self._page.parameters[2].append(self._varEntry(self._tmpName, self._tmpTypeNode, docNode))
        
        # create an entry for a property
        if tag in ('property', ):
            # taking the element at index 2 gives us the <tbody>
            self._page.properties[2].append(self._varEntry(self._tmpName, self._tmpTypeNode, docNode))
        
        # create an entry for a member
        if tag in ('member', ):
            # taking the element at index 2 gives us the <tbody>
            self._page.members[2].append(self._membEntry(self._tmpName, self._tmpValue, docNode))
        
        # set page.returnValue, which gives the return value
        if tag in ('return-value', ):
            self._page.returnValue = self._table('Return Value', ('Type', 'Description'))
            
            tr = etree.SubElement(self._page.returnValue[2], 'tr')
            
            td = etree.SubElement(tr, 'td')
            td.append(self._tmpTypeNode)
            
            td = etree.SubElement(tr, 'td')
            td.append(docNode)
        
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
    
    # create a table    
    @staticmethod
    def _table(title, headerList, expanded=True):
        table = etree.Element('table', shade='cols')
        table.set(_UI + 'expanded', 'yes' if expanded else 'no')
        etree.SubElement(table, 'title').text = title
        
        thead = etree.SubElement(table, 'thead')
        tr = etree.SubElement(thead, 'tr')
        
        for text in headerList:
            td = etree.SubElement(tr, 'td')
            etree.SubElement(td, 'p').text = text
        
        etree.SubElement(table, 'tbody')
        
        return table
    
    # create a table that lists variables
    # returns the table (which hasn't been inserted into any document yet)
    @staticmethod
    def _varSection(title, expanded=True):
        return _MallardContentHandler._table(title, ('Type', 'Name', 'Description'), expanded=expanded)
    
    # create a row in a table that lists variables
    @staticmethod
    def _varEntry(name, typeNode, docNode):
        tr = etree.Element('tr')
        
        td = etree.SubElement(tr, 'td')
        td.append(typeNode)
        
        td = etree.SubElement(tr, 'td')
        etree.SubElement(td, 'p').text = name
        
        td = etree.SubElement(tr, 'td')
        td.append(docNode)
        
        return tr
    
    # create a table that lists bitfield/enumeration members
    # returns the table (which hasn't been inserted into any document yet)
    @staticmethod
    def _membSection(title):
        return _MallardContentHandler._table(title, ('Value', 'Name', 'Description'))
    
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
