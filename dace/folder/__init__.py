from substanced.folder import Folder as FD
from persistent.list import PersistentList
from dace.interfaces import INameChooser

class Property(FD):

    def __init__(self, name, opposit=None, isunique=False):
        super(Property, self).__init__()
        self.name = name
        self.opposit = opposit
        self.isunique = isunique

    def addvalue(self, value):
        pass

    def setvalue(self, value):
        pass

    def getvalue(self, value):
        pass

    def removevalue(self, value):
        pass


class SharedProperty(Property):
    pass


class CompositProperty(Property):    

    def __init__(self, name, opposit=None, isunique=False):
        Property.__init__(self, name, opposit)


class CompositUniqueProperty(CompositProperty):

    def __init__(self, name, opposit=None, value=None):
        CompositProperty.__init__(self, name, opposit, True)
        self.valuekey = None

    def addvalue(self, value, initiator=True):
        self.setvalue(value, initiator)

    def setvalue(self, value, initiator=True):
        if self.valuekey is not None and self.__parent__[self.valuekey] == value:
            return

        if initiator and self.opposit is not None:
            value[self.opposit].addvalue(self.__parent__, False)

        if self.valuekey is not None:
            self.removevalue(self.__parent__[self.valuekey])

        if hasattr(value,'__property__'):
            value.__property__.removevalue(value)

        value.__property__ = self
        name = INameChooser(self.__parent__).chooseName(u'', value)
        self.valuekey = name
        self.__parent__.add(self.valuekey, value)

    def getvalue(self):
        if self.valuekey is not None:
            return self.__parent__[self.valuekey]

    def removevalue(self, value, initiator=True):
        if self.valuekey is not None and self.__parent__[self.valuekey] == value:
            if initiator and self.opposit is not None:
                value[self.name].removevalue(self.__parent__, False)
            self.__parent__.remove(self.valuekey)


class CompositMultipleProperty(CompositProperty):

    def __init__(self, name, opposit=None, isunique=False, values=None):
        super(CompositMultipleProperty, self).__init__(name, opposit, isunique)
        self.contents_keys = PersistentList()

    def addvalue(self, value, initiator=True):
        if self.isunique and value in self.getvalue():
            return

        if initiator and self.opposit is not None:
            value[self.opposit].addvalue(self.__parent__, False)

        if hasattr(value,'__property__') :
            value.__property__.removevalue(value)

        value.__property__ = self
        name = INameChooser(self.__parent__).chooseName(u'', value)
        self.contents_keys.append(name)
        self.__parent__.add(name, value)

    def setvalue(self, value, initiator=True):
        if (not isinstance(value, list) and not isinstance(value, tuple) ):
            value = [value]

        oldvalues = self.getvalue()
        toremove = [v for v in oldvalues if not (v in value)]
        toadd = [v for v in value if not (v in oldvalues)]
        self.removevalue(toremove)
        if toadd:
            for v in value:
                self.addvalue(v)

    def getvalue(self):
        return [self.__parent__[key] for key in self.contents_keys]

    def removevalue(self, value, initiator=True):
        if (not isinstance(value, list) and not isinstance(value, tuple) ):
            value = [value]

        for v in value:
            if initiator and self.opposit is not None:
                v[self.name].removevalue(self.__parent__, False)

            if self.__parent__.__contains__(v.name):
                self.contents_keys.remove(v.name)
                self.__parent__.remove(v.name)


class SharedUniqueProperty(SharedProperty):

    def __init__(self, name, opposit=None, value=None):
        super(SharedUniqueProperty, self).__init__(name, opposit, True)
        self.value = value

    def addvalue(self, value):
        pass

    def setvalue(self, value):
        pass

    def getvalue(self, value):
        pass

    def removevalue(self, value):
        pass


class SharedMultipleProperty(SharedProperty):

    def __init__(self, name, opposit=None, isunique=False, values=None):
        super(SharedMultipleProperty, self).__init__(name, opposit, isunique)
        self.values = PersistentList()

    def addvalue(self, value):
        pass

    def setvalue(self, value):
        pass

    def getvalue(self, value):
        pass

    def removevalue(self, value):
        pass


class Folder(FD):

    def __init__(self):
        FD.__init__(self)
        self.attributes = PersistentList()

    def __addproperty__(self, _property):
        self[_property.name] = _property
        self.attributes.append(_property.name)

    def __setattr__(self, name, value):
        if hasattr(self,'attributes') and  name in self.attributes:
            self[name].setvalue(value)
        else:
            super(Folder,self).__setattr__(name, value)
