# -*- Mode: Python -*-

import xml.sax
import logging

# uncomment to enable debug logging
# logging.basicConfig(level=logging.DEBUG)

def write_mallard(girFilename, lang='Python', transformer=None):
    contentHandler = _MallardContentHandler()
    xml.sax.parse(girFilename, contentHandler)

class _MallardContentHandler(xml.sax.handler.ContentHandler):
    def startDocument(self):
        logging.debug('startDocument()')
    
    def endDocument(self):
        logging.debug('endDocument()')
    
    def startElement(self, tag, attrs):
        logging.debug('startElement(): tag = {}; attrs[\'name\'] = {}'.format(tag, attrs['name'] if attrs.has_key('name') else '(none)'))
    
    def endElement(self, tag):
        logging.debug('endElement(): tag = {}'.format(tag))
    
    def characters(self, content):
        # content may be in Unicode format, but the .format() method of
        # an ASCII string can only accept other ASCII strings, so use
        # repr to escape it
        logging.debug('characters({})'.format(repr(content)))
