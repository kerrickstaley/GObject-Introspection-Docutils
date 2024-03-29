# -*- Mode: Python -*-
# GObject-Introspection - a framework for introspecting GObject libraries
# Copyright (C) 2008  Johan Dahlin
# Copyright (C) 2008, 2009 Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#

import copy

from .message import Position
from .odict import odict
from .utils import to_underscores

class Type(object):
    """A Type can be either:
* A reference to a node (target_giname)
* A reference to a "fundamental" type like 'utf8'
* A "foreign" type - this can be any string."
If none are specified, then it's in an "unresolved" state.  An
unresolved type can have two data sources; a "ctype" which comes
from a C type string, or a gtype_name (from g_type_name()).
""" # '''

    def __init__(self,
                 ctype=None,
                 gtype_name=None,
                 target_fundamental=None,
                 target_giname=None,
                 target_foreign=None,
                 _target_unknown=False,
                 is_const=False,
                 origin_symbol=None):
        self.ctype = ctype
        self.gtype_name = gtype_name
        self.origin_symbol = origin_symbol
        if _target_unknown:
            assert isinstance(self, TypeUnknown)
        elif target_fundamental:
            assert target_giname is None
            assert target_foreign is None
        elif target_giname:
            assert '.' in target_giname
            assert target_fundamental is None
            assert target_foreign is None
        elif target_foreign:
            assert ctype is not None
            assert target_giname is None
            assert target_fundamental is None
        else:
            assert (ctype is not None) or (gtype_name is not None)
        self.target_fundamental = target_fundamental
        self.target_giname = target_giname
        self.target_foreign = target_foreign
        self.is_const = is_const

    @property
    def resolved(self):
        return (self.target_fundamental or
                self.target_giname or
                self.target_foreign)

    @property
    def unresolved_string(self):
        if self.ctype:
            return self.ctype
        elif self.gtype_name:
            return self.gtype_name
        else:
            assert False

    @classmethod
    def create_from_gtype_name(cls, gtype_name):
        """Parse a GType name (as from g_type_name()), and return a
Type instance.  Note that this function performs namespace lookup,
in contrast to the other create_type() functions."""
        # First, is it a fundamental?
        fundamental = type_names.get(gtype_name)
        if fundamental is not None:
            return cls(target_fundamental=fundamental.target_fundamental)
        if gtype_name == 'GHashTable':
            return Map(TYPE_ANY, TYPE_ANY, gtype_name=gtype_name)
        elif gtype_name in ('GArray', 'GPtrArray', 'GByteArray'):
            return Array('GLib.' + gtype_name[1:], TYPE_ANY,
                         gtype_name=gtype_name)
        elif gtype_name == 'GStrv':
            bare_utf8 = TYPE_STRING.clone()
            bare_utf8.ctype = None
            return Array(None, bare_utf8, ctype=None, gtype_name=gtype_name,
                         is_const=False)

        # Workaround for Gdk.Rectangle being boxed alias for
        # cairo.RectangleInt.  G-I does not support boxing of aliases.
        # See https://bugzilla.gnome.org/show_bug.cgi?id=655423
        if gtype_name == 'GdkRectangle':
            gtype_name = 'CairoRectangleInt'

        return cls(gtype_name=gtype_name)

    def get_giname(self):
        assert self.target_giname is not None
        return self.target_giname.split('.')[1]

    def __cmp__(self, other):
        if self.target_fundamental:
            return cmp(self.target_fundamental, other.target_fundamental)
        if self.target_giname:
            return cmp(self.target_giname, other.target_giname)
        if self.target_foreign:
            return cmp(self.target_foreign, other.target_foreign)
        return cmp(self.ctype, other.ctype)

    def is_equiv(self, typeval):
        """Return True if the specified types are compatible at
        an introspection level, disregarding their C types.
        A sequence may be given for typeval, in which case
        this function returns True if the type is compatible with
        any."""
        if isinstance(typeval, (list, tuple)):
            for val in typeval:
                if self.is_equiv(val):
                    return True
            return False
        return self == typeval

    def clone(self):
        return Type(target_fundamental=self.target_fundamental,
                    target_giname=self.target_giname,
                    target_foreign=self.target_foreign,
                    ctype=self.ctype,
                    is_const=self.is_const)

    def __str__(self):
        if self.target_fundamental:
            return self.target_fundamental
        elif self.target_giname:
            return self.target_giname
        elif self.target_foreign:
            return self.target_foreign

    def __repr__(self):
        if self.target_fundamental:
            data = 'target_fundamental=%s, ' % (self.target_fundamental, )
        elif self.target_giname:
            data = 'target_giname=%s, ' % (self.target_giname, )
        elif self.target_foreign:
            data = 'target_foreign=%s, ' % (self.target_foreign, )
        else:
            data = ''
        return '%s(%sctype=%s)' % (self.__class__.__name__, data, self.ctype)

class TypeUnknown(Type):
    def __init__(self):
        Type.__init__(self, _target_unknown=True)

######
## Fundamental types
######
# Two special ones
TYPE_NONE = Type(target_fundamental='none', ctype='void')
TYPE_ANY = Type(target_fundamental='gpointer', ctype='gpointer')
# "Basic" types
TYPE_BOOLEAN = Type(target_fundamental='gboolean', ctype='gboolean')
TYPE_INT8 = Type(target_fundamental='gint8', ctype='gint8')
TYPE_UINT8 = Type(target_fundamental='guint8', ctype='guint8')
TYPE_INT16 = Type(target_fundamental='gint16', ctype='gint16')
TYPE_UINT16 = Type(target_fundamental='guint16', ctype='guint16')
TYPE_INT32 = Type(target_fundamental='gint32', ctype='gint32')
TYPE_UINT32 = Type(target_fundamental='guint32', ctype='guint32')
TYPE_INT64 = Type(target_fundamental='gint64', ctype='gint64')
TYPE_UINT64 = Type(target_fundamental='guint64', ctype='guint64')
TYPE_CHAR = Type(target_fundamental='gchar', ctype='gchar')
TYPE_SHORT = Type(target_fundamental='gshort', ctype='gshort')
TYPE_USHORT = Type(target_fundamental='gushort', ctype='gushort')
TYPE_INT = Type(target_fundamental='gint', ctype='gint')
TYPE_UINT = Type(target_fundamental='guint', ctype='guint')
TYPE_LONG = Type(target_fundamental='glong', ctype='glong')
TYPE_ULONG = Type(target_fundamental='gulong', ctype='gulong')
TYPE_SIZE = Type(target_fundamental='gsize', ctype='gsize')
TYPE_SSIZE = Type(target_fundamental='gssize', ctype='gssize')
TYPE_INTPTR = Type(target_fundamental='gintptr', ctype='gintptr')
TYPE_UINTPTR = Type(target_fundamental='guintptr', ctype='guintptr')
# C99 types
TYPE_LONG_LONG = Type(target_fundamental='long long', ctype='long long')
TYPE_LONG_ULONG = Type(target_fundamental='unsigned long long',
                       ctype='unsigned long long')
TYPE_FLOAT = Type(target_fundamental='gfloat', ctype='gfloat')
TYPE_DOUBLE = Type(target_fundamental='gdouble', ctype='gdouble')
# ?
TYPE_LONG_DOUBLE = Type(target_fundamental='long double',
                        ctype='long double')
TYPE_UNICHAR = Type(target_fundamental='gunichar', ctype='gunichar')

# C types with semantics overlaid
TYPE_GTYPE = Type(target_fundamental='GType', ctype='GType')
TYPE_STRING = Type(target_fundamental='utf8', ctype='gchar*')
TYPE_FILENAME = Type(target_fundamental='filename', ctype='gchar*')

TYPE_VALIST = Type(target_fundamental='va_list', ctype='va_list')

BASIC_GIR_TYPES = [TYPE_BOOLEAN, TYPE_INT8, TYPE_UINT8, TYPE_INT16,
                   TYPE_UINT16, TYPE_INT32, TYPE_UINT32, TYPE_INT64,
                   TYPE_UINT64, TYPE_CHAR, TYPE_SHORT, TYPE_USHORT, TYPE_INT,
                   TYPE_UINT, TYPE_LONG, TYPE_ULONG, TYPE_SIZE, TYPE_SSIZE,
                   TYPE_LONG_LONG, TYPE_LONG_ULONG, TYPE_INTPTR, TYPE_UINTPTR,
                   TYPE_FLOAT, TYPE_DOUBLE,
                   TYPE_LONG_DOUBLE, TYPE_UNICHAR, TYPE_GTYPE]
GIR_TYPES = [TYPE_NONE, TYPE_ANY]
GIR_TYPES.extend(BASIC_GIR_TYPES)
GIR_TYPES.extend([TYPE_STRING, TYPE_FILENAME, TYPE_VALIST])

# These are the only basic types that are guaranteed to
# be as big as a pointer (and thus are allowed in GPtrArray)
POINTER_TYPES = [TYPE_ANY, TYPE_INTPTR, TYPE_UINTPTR]

INTROSPECTABLE_BASIC = list(GIR_TYPES)
for v in [TYPE_NONE, TYPE_ANY,
          TYPE_LONG_LONG, TYPE_LONG_ULONG,
          TYPE_LONG_DOUBLE, TYPE_VALIST]:
    INTROSPECTABLE_BASIC.remove(v)

type_names = {}
for typeval in GIR_TYPES:
    type_names[typeval.target_fundamental] = typeval
basic_type_names = {}
for typeval in BASIC_GIR_TYPES:
    basic_type_names[typeval.target_fundamental] = typeval

# C builtin
type_names['char'] = TYPE_CHAR
type_names['signed char'] = TYPE_INT8
type_names['unsigned char'] = TYPE_UINT8
type_names['short'] = TYPE_SHORT
type_names['signed short'] = TYPE_SHORT
type_names['unsigned short'] = TYPE_USHORT
type_names['int'] = TYPE_INT
type_names['signed int'] = TYPE_INT
type_names['unsigned short int'] = TYPE_USHORT
type_names['signed'] = TYPE_INT
type_names['unsigned int'] = TYPE_UINT
type_names['unsigned'] = TYPE_UINT
type_names['long'] = TYPE_LONG
type_names['signed long'] = TYPE_LONG
type_names['unsigned long'] = TYPE_ULONG
type_names['unsigned long int'] = TYPE_ULONG
type_names['float'] = TYPE_FLOAT
type_names['double'] = TYPE_DOUBLE
type_names['char*'] = TYPE_STRING
type_names['void*'] = TYPE_ANY
type_names['void'] = TYPE_NONE
# Also alias the signed one here
type_names['signed long long'] = TYPE_LONG_LONG

# A few additional GLib type aliases
type_names['guchar'] = TYPE_UINT8
type_names['gchararray'] = TYPE_STRING
type_names['gchar*'] = TYPE_STRING
type_names['goffset'] = TYPE_INT64
type_names['gunichar2'] = TYPE_UINT16
type_names['gsize'] = TYPE_SIZE
type_names['gssize'] = TYPE_SSIZE
type_names['gintptr'] = TYPE_INTPTR
type_names['guintptr'] = TYPE_UINTPTR
type_names['gconstpointer'] = TYPE_ANY

# We used to support these; continue to do so
type_names['any'] = TYPE_ANY
type_names['boolean'] = TYPE_BOOLEAN
type_names['uint'] = TYPE_UINT
type_names['ulong'] = TYPE_ULONG

# C stdio, used in GLib public headers; squash this for now here
# until we move scanning into GLib and can (skip)
type_names['FILE*'] = TYPE_ANY

# One off C unix type definitions; note some of these may be GNU Libc
# specific.  If someone is actually bitten by this, feel free to do
# the required configure goop to determine their size and replace
# here.
#
# We don't want to encourage people to use these in their APIs because
# they compromise the platform-independence that GLib gives you.
# These are here mostly to avoid blowing when random platform-specific
# methods are added under #ifdefs inside GLib itself.  We could just (skip)
# the relevant methods, but on the other hand, since these types are just
# integers it's easy enough to expand them.
type_names['size_t'] = type_names['gsize']
type_names['time_t'] = TYPE_LONG
type_names['off_t'] = type_names['gsize']
type_names['pid_t'] = TYPE_INT
type_names['uid_t'] = TYPE_UINT
type_names['gid_t'] = TYPE_UINT
type_names['dev_t'] = TYPE_INT
type_names['socklen_t'] = TYPE_INT32
type_names['size_t'] = TYPE_ULONG
type_names['ssize_t'] = TYPE_LONG

# Obj-C
type_names['id'] = TYPE_ANY

##
## Parameters
##

PARAM_DIRECTION_IN = 'in'
PARAM_DIRECTION_OUT = 'out'
PARAM_DIRECTION_INOUT = 'inout'

PARAM_SCOPE_CALL = 'call'
PARAM_SCOPE_ASYNC = 'async'
PARAM_SCOPE_NOTIFIED = 'notified'

PARAM_TRANSFER_NONE = 'none'
PARAM_TRANSFER_CONTAINER = 'container'
PARAM_TRANSFER_FULL = 'full'

SIGNAL_FIRST = 'first'
SIGNAL_LAST = 'last'
SIGNAL_CLEANUP = 'cleanup'
SIGNAL_MUST_COLLECT = 'must-collect'


class Namespace(object):
    def __init__(self, name, version,
                 identifier_prefixes=None,
                 symbol_prefixes=None):
        self.name = name
        self.version = version
        if identifier_prefixes is not None:
            self.identifier_prefixes = identifier_prefixes
        else:
            self.identifier_prefixes = [name]
        if symbol_prefixes is not None:
            self.symbol_prefixes = symbol_prefixes
        else:
            ps = self.identifier_prefixes
            self.symbol_prefixes = [to_underscores(p).lower() for p in ps]
        # cache upper-cased versions
        self._ucase_symbol_prefixes = [p.upper() for p in self.symbol_prefixes]
        self._names = odict() # Maps from GIName -> node
        self._aliases = {} # Maps from GIName -> GIName
        self._type_names = {} # Maps from GTName -> node
        self._ctypes = {} # Maps from CType -> node
        self._symbols = {} # Maps from function symbols -> Function

    @property
    def names(self):
        return self._names

    @property
    def aliases(self):
        return self._aliases

    @property
    def type_names(self):
        return self._type_names

    @property
    def ctypes(self):
        return self._ctypes

    def type_from_name(self, name, ctype=None):
        """Backwards compatibility method for older .gir files, which
only use the 'name' attribute.  If name refers to a fundamental type,
create a Type object referncing it.  If name is already a
fully-qualified GIName like 'Foo.Bar', returns a Type targeting it .
Otherwise a Type targeting name qualififed with the namespace name is
returned."""
        if name in type_names:
            return Type(target_fundamental=name, ctype=ctype)
        if '.' in name:
            target = name
        else:
            target = '%s.%s' % (self.name, name)
        return Type(target_giname=target, ctype=ctype)

    def append(self, node, replace=False):
        previous = self._names.get(node.name)
        if previous is not None:
            if not replace:
                raise ValueError("Namespace conflict: %r" % (node, ))
            self.remove(previous)
        # A layering violation...but oh well.
        if isinstance(node, Alias):
            self._aliases[node.name] = node
        elif isinstance(node, Registered) and node.gtype_name is not None:
            self._type_names[node.gtype_name] = node
        elif isinstance(node, Function):
            self._symbols[node.symbol] = node
        assert isinstance(node, Node)
        assert node.namespace is None
        node.namespace = self
        self._names[node.name] = node
        if hasattr(node, 'ctype'):
            self._ctypes[node.ctype] = node
        if hasattr(node, 'symbol'):
            self._ctypes[node.symbol] = node

    def remove(self, node):
        if isinstance(node, Alias):
            del self._aliases[node.name]
        elif isinstance(node, Registered) and node.gtype_name is not None:
            del self._type_names[node.gtype_name]
        del self._names[node.name]
        node.namespace = None
        if hasattr(node, 'ctype'):
            del self._ctypes[node.ctype]
        if isinstance(node, Function):
            del self._symbols[node.symbol]

    def float(self, node):
        """Like remove(), but doesn't unset the node's namespace
back-reference, and it's still possible to look up
functions via get_by_symbol()."""
        if isinstance(node, Function):
            symbol = node.symbol
        self.remove(node)
        self._symbols[symbol] = node
        node.namespace = self

    def __iter__(self):
        return iter(self._names)

    def iteritems(self):
        return self._names.iteritems()

    def itervalues(self):
        return self._names.itervalues()

    def get(self, name):
        return self._names.get(name)

    def get_by_ctype(self, ctype):
        return self._ctypes.get(ctype)

    def get_by_symbol(self, symbol):
        return self._symbols.get(symbol)

    def walk(self, callback):
        for node in self.itervalues():
            node.walk(callback, [])

class Include(object):

    def __init__(self, name, version):
        self.name = name
        self.version = version

    @classmethod
    def from_string(cls, string):
        return cls(*string.split('-', 1))

    def __cmp__(self, other):
        namecmp = cmp(self.name, other.name)
        if namecmp != 0:
            return namecmp
        return cmp(self.version, other.version)

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return '%s-%s' % (self.name, self.version)

class Annotated(object):
    """An object which has a few generic metadata
properties."""
    def __init__(self):
        self.version = None
        self.skip = False
        self.introspectable = True
        self.attributes = [] # (key, value)*
        self.deprecated = None
        self.deprecated_version = None
        self.doc = None

class Node(Annotated):
    """A node is a type of object which is uniquely identified by its
(namespace, name) pair.  When combined with a ., this is called a
GIName.  It's possible for nodes to contain or point to other nodes."""

    c_name = property(lambda self: self.namespace.name + self.name)
    gi_name = property(lambda self: '%s.%s' % (self.namespace.name, self.name))

    def __init__(self, name=None):
        Annotated.__init__(self)
        self.namespace = None # Should be set later by Namespace.append()
        self.name = name
        self.foreign = False
        self.file_positions = set()

    def create_type(self):
        """Create a Type object referencing this node."""
        assert self.namespace is not None
        return Type(target_giname=('%s.%s' % (self.namespace.name, self.name)))

    def __cmp__(self, other):
        nscmp = cmp(self.namespace, other.namespace)
        if nscmp != 0:
            return nscmp
        return cmp(self.name, other.name)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

    def inherit_file_positions(self, node):
        self.file_positions.update(node.file_positions)

    def add_file_position(self, position):
        self.file_positions.add(position)

    def add_symbol_reference(self, symbol):
        if symbol.source_filename:
            self.add_file_position(Position(symbol.source_filename, symbol.line))

    def walk(self, callback, chain):
        res = callback(self, chain)
        assert res in (True, False), "Walk function must return boolean, not %r" % (res, )
        if not res:
            return False
        chain.append(self)
        self._walk(callback, chain)
        chain.pop()

    def _walk(self, callback, chain):
        pass


class Registered:
    """A node that (possibly) has gtype_name and get_type."""
    def __init__(self, gtype_name, get_type):
        assert (gtype_name is None and get_type is None) or \
               (gtype_name is not None and get_type is not None)
        self.gtype_name = gtype_name
        self.get_type = get_type


class Callable(Node):

    def __init__(self, name, retval, parameters, throws):
        Node.__init__(self, name)
        self.retval = retval
        self.parameters = parameters
        self.throws = not not throws
        self.instance_parameter = None # Parameter

    def get_parameter_index(self, name):
        for i, parameter in enumerate(self.parameters):
            if parameter.argname == name:
                return i
        raise ValueError("Unknown argument %s" % (name, ))

    def get_parameter(self, name):
        for parameter in self.parameters:
            if parameter.argname == name:
                return parameter
        raise ValueError("Unknown argument %s" % (name, ))


class Function(Callable):

    def __init__(self, name, retval, parameters, throws, symbol):
        Callable.__init__(self, name, retval, parameters, throws)
        self.symbol = symbol
        self.is_method = False
        self.is_constructor = False
        self.shadowed_by = None # C symbol string
        self.shadows = None # C symbol string
        self.moved_to = None # namespaced function name string

    def clone(self):
        clone = copy.copy(self)
        # copy the parameters array so a change to self.parameters does not
        # influence clone.parameters.
        clone.parameters = self.parameters[:]
        return clone


class ErrorQuarkFunction(Function):

    def __init__(self, name, retval, parameters, throws, symbol, error_domain):
        Function.__init__(self, name, retval, parameters, throws, symbol)
        self.error_domain = error_domain


class VFunction(Callable):

    def __init__(self, name, retval, parameters, throws):
        Callable.__init__(self, name, retval, parameters, throws)
        self.invoker = None

    @classmethod
    def from_callback(cls, cb):
        obj = cls(cb.name, cb.retval, cb.parameters[1:],
                  cb.throws)
        return obj



class Varargs(Type):

    def __init__(self):
        Type.__init__(self, '<varargs>', target_fundamental='<varargs>')


class Array(Type):
    C = '<c>'
    GLIB_ARRAY = 'GLib.Array'
    GLIB_BYTEARRAY = 'GLib.ByteArray'
    GLIB_PTRARRAY = 'GLib.PtrArray'

    def __init__(self, array_type, element_type, **kwargs):
        Type.__init__(self, target_fundamental='<array>',
                      **kwargs)
        if (array_type is None or array_type == self.C):
            self.array_type = self.C
        else:
            assert array_type in (self.GLIB_ARRAY,
                                  self.GLIB_BYTEARRAY,
                                  self.GLIB_PTRARRAY), array_type
            self.array_type = array_type
        assert isinstance(element_type, Type)
        self.element_type = element_type
        self.zeroterminated = True
        self.length_param_name = None
        self.size = None

    def clone(self):
        arr = Array(self.array_type, self.element_type)
        arr.zeroterminated = self.zeroterminated
        arr.length_param_name = self.length_param_name
        arr.size = self.size
        return arr

class List(Type):

    def __init__(self, name, element_type, **kwargs):
        Type.__init__(self, target_fundamental='<list>',
                      **kwargs)
        self.name = name
        assert isinstance(element_type, Type)
        self.element_type = element_type

    def clone(self):
        l = List(self.name, self.element_type)
        l.zeroterminated = self.zeroterminated
        l.length_param_name = self.length_param_name
        l.size = self.size
        return l

class Map(Type):

    def __init__(self, key_type, value_type, **kwargs):
        Type.__init__(self, target_fundamental='<map>', **kwargs)
        assert isinstance(key_type, Type)
        self.key_type = key_type
        assert isinstance(value_type, Type)
        self.value_type = value_type

    def clone(self):
        return Map(self.key_type, self.value_type)

class Alias(Node):

    def __init__(self, name, target, ctype=None):
        Node.__init__(self, name)
        self.target = target
        self.ctype = ctype


class TypeContainer(Annotated):
    """A fundamental base class for Return and Parameter."""

    def __init__(self, typenode, transfer):
        Annotated.__init__(self)
        self.type = typenode
        if transfer is not None:
            self.transfer = transfer
        elif typenode.is_const:
            self.transfer = PARAM_TRANSFER_NONE
        else:
            self.transfer = None


class Parameter(TypeContainer):
    """An argument to a function."""

    def __init__(self, argname, typenode, direction=None,
                 transfer=None, allow_none=False, scope=None,
                 caller_allocates=False):
        TypeContainer.__init__(self, typenode, transfer)
        self.argname = argname
        self.direction = direction
        self.allow_none = allow_none
        self.scope = scope
        self.caller_allocates = caller_allocates
        self.closure_name = None
        self.destroy_name = None


class Return(TypeContainer):
    """A return value from a function."""

    def __init__(self, rtype, transfer=None):
        TypeContainer.__init__(self, rtype, transfer)
        self.direction = PARAM_DIRECTION_OUT


class Enum(Node, Registered):

    def __init__(self, name, ctype,
                 gtype_name=None,
                 get_type=None,
                 c_symbol_prefix=None,
                 members=None):
        Node.__init__(self, name)
        Registered.__init__(self, gtype_name, get_type)
        self.c_symbol_prefix = c_symbol_prefix
        self.ctype = ctype
        self.members = members
        # Associated error domain name
        self.error_domain = None
        self.static_methods = []

    def _walk(self, callback, chain):
        for meth in self.static_methods:
            meth.walk(callback, chain)


class Bitfield(Node, Registered):

    def __init__(self, name, ctype,
                 gtype_name=None,
                 c_symbol_prefix=None,
                 get_type=None,
                 members=None):
        Node.__init__(self, name)
        Registered.__init__(self, gtype_name, get_type)
        self.ctype = ctype
        self.c_symbol_prefix = c_symbol_prefix
        self.members = members
        self.static_methods = []

    def _walk(self, callback, chain):
        for meth in self.static_methods:
            meth.walk(callback, chain)


class Member(Annotated):

    def __init__(self, name, value, symbol, nick):
        Annotated.__init__(self)
        self.name = name
        self.value = value
        self.symbol = symbol
        self.nick = nick

    def __cmp__(self, other):
        return cmp(self.name, other.name)



class Compound(Node, Registered):
    def __init__(self, name,
                 ctype=None,
                 gtype_name=None,
                 get_type=None,
                 c_symbol_prefix=None,
                 disguised=False):
        Node.__init__(self, name)
        Registered.__init__(self, gtype_name, get_type)
        self.ctype = ctype
        self.methods = []
        self.static_methods = []
        self.fields = []
        self.constructors = []
        self.disguised = disguised
        self.gtype_name = gtype_name
        self.get_type = get_type
        self.c_symbol_prefix = c_symbol_prefix

    def add_gtype(self, gtype_name, get_type):
        self.gtype_name = gtype_name
        self.get_type = get_type

    def _walk(self, callback, chain):
        for ctor in self.constructors:
            ctor.walk(callback, chain)
        for func in self.methods:
            func.walk(callback, chain)
        for func in self.static_methods:
            func.walk(callback, chain)
        for field in self.fields:
            if field.anonymous_node is not None:
                field.anonymous_node.walk(callback, chain)

class Field(Annotated):

    def __init__(self, name, typenode, readable, writable, bits=None,
                 anonymous_node=None):
        Annotated.__init__(self)
        assert (typenode or anonymous_node)
        self.name = name
        self.type = typenode
        self.readable = readable
        self.writable = writable
        self.bits = bits
        self.anonymous_node = anonymous_node
        self.private = False

    def __cmp__(self, other):
        return cmp(self.name, other.name)


class Record(Compound):

    def __init__(self, name,
                 ctype=None,
                 gtype_name=None,
                 get_type=None,
                 c_symbol_prefix=None,
                 disguised=False):
        Compound.__init__(self, name,
                          ctype=ctype,
                          gtype_name=gtype_name,
                          get_type=get_type,
                          c_symbol_prefix=c_symbol_prefix,
                          disguised=disguised)
        # If non-None, this record defines the FooClass C structure
        # for some Foo GObject (or similar for GInterface)
        self.is_gtype_struct_for = None


class Union(Compound):

    def __init__(self, name,
                 ctype=None,
                 gtype_name=None,
                 get_type=None,
                 c_symbol_prefix=None,
                 disguised=False):
        Compound.__init__(self, name,
                          ctype=ctype,
                          gtype_name=gtype_name,
                          get_type=get_type,
                          c_symbol_prefix=c_symbol_prefix,
                          disguised=disguised)


class Boxed(Node, Registered):
    """A boxed type with no known associated structure/union."""
    def __init__(self, name,
                 gtype_name=None,
                 get_type=None,
                 c_symbol_prefix=None):
        assert gtype_name is not None
        assert get_type is not None
        Node.__init__(self, name)
        Registered.__init__(self, gtype_name, get_type)
        if get_type is not None:
            assert c_symbol_prefix is not None
        self.c_symbol_prefix = c_symbol_prefix
        self.constructors = []
        self.methods = []
        self.static_methods = []

    def _walk(self, callback, chain):
        for ctor in self.constructors:
            ctor.walk(callback, chain)
        for meth in self.methods:
            meth.walk(callback, chain)
        for meth in self.static_methods:
            meth.walk(callback, chain)


class Signal(Callable):

    def __init__(self, name, retval, parameters, when=None,
                 no_recurse=False, detailed=False, action=False,
                 no_hooks=False):
        Callable.__init__(self, name, retval, parameters, False)
        self.when = when
        self.no_recurse = no_recurse
        self.detailed = detailed
        self.action = action
        self.no_hooks = no_hooks


class Class(Node, Registered):

    def __init__(self, name, parent,
                 ctype=None,
                 gtype_name=None,
                 get_type=None,
                 c_symbol_prefix=None,
                 is_abstract=False):
        Node.__init__(self, name)
        Registered.__init__(self, gtype_name, get_type)
        self.ctype = ctype
        self.c_symbol_prefix = c_symbol_prefix
        self.parent = parent
        self.fundamental = False
        self.unref_func = None
        self.ref_func = None
        self.set_value_func = None
        self.get_value_func = None
        # When we're in the scanner, we keep around a list
        # of parents so that we can transparently fall back
        # if there are 'hidden' parents
        self.parent_chain = []
        self.glib_type_struct = None
        self.is_abstract = is_abstract
        self.methods = []
        self.virtual_methods = []
        self.static_methods = []
        self.interfaces = []
        self.constructors = []
        self.properties = []
        self.fields = []
        self.signals = []

    def _walk(self, callback, chain):
        for meth in self.methods:
            meth.walk(callback, chain)
        for meth in self.virtual_methods:
            meth.walk(callback, chain)
        for meth in self.static_methods:
            meth.walk(callback, chain)
        for ctor in self.constructors:
            ctor.walk(callback, chain)
        for field in self.fields:
            if field.anonymous_node:
                field.anonymous_node.walk(callback, chain)
        for sig in self.signals:
            sig.walk(callback, chain)


class Interface(Node, Registered):

    def __init__(self, name, parent,
                 ctype=None,
                 gtype_name=None,
                 get_type=None,
                 c_symbol_prefix=None):
        Node.__init__(self, name)
        Registered.__init__(self, gtype_name, get_type)
        self.ctype = ctype
        self.c_symbol_prefix = c_symbol_prefix
        self.parent = parent
        self.parent_chain = []
        self.methods = []
        self.signals = []
        self.static_methods = []
        self.virtual_methods = []
        self.glib_type_struct = None
        self.properties = []
        self.fields = []
        self.prerequisites = []

    def _walk(self, callback, chain):
        for meth in self.methods:
            meth.walk(callback, chain)
        for meth in self.static_methods:
            meth.walk(callback, chain)
        for meth in self.virtual_methods:
            meth.walk(callback, chain)
        for field in self.fields:
            if field.anonymous_node:
                field.anonymous_node.walk(callback, chain)
        for sig in self.signals:
            sig.walk(callback, chain)


class Constant(Node):

    def __init__(self, name, value_type, value, ctype):
        Node.__init__(self, name)
        self.value_type = value_type
        self.value = value
        self.ctype = ctype


class Property(Node):

    def __init__(self, name, typeobj, readable, writable,
                 construct, construct_only, transfer=None):
        Node.__init__(self, name)
        self.type = typeobj
        self.readable = readable
        self.writable = writable
        self.construct = construct
        self.construct_only = construct_only
        if transfer is None:
            self.transfer = PARAM_TRANSFER_NONE
        else:
            self.transfer = transfer


class Callback(Callable):

    def __init__(self, name, retval, parameters, throws, ctype=None):
        Callable.__init__(self, name, retval, parameters, throws)
        self.ctype = ctype
