from substanced.folder import Folder
from persistent.list import PersistentList


class Property(Folder):

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
        self.valuekey = '__value__'

    def addvalue(self, value, initiator=True):
        self.setvalue(value)

    def setvalue(self, value, initiator=True):
        if self.__contains__(self.valuekey) and self[self.valuekey] == value:
            return

        if initiator and self.opposit is not None:
            value[self.opposit].addvalue(self.__parent__, False)

        if self.__contains__(self.valuekey):
            self.removevalue(self[self.valuekey])

        if getattr(value,'__parent__', None) is not None:
            value.__parent__.removevalue(value)

        self.add(self.valuekey, value)

    def getvalue(self):
        if self.__contains__(self.valuekey):
            return self[self.valuekey]

    def removevalue(self, value, initiator=True):
        if self.valuekey in self and self[self.valuekey] == value:
            if initiator and self.opposit is not None:
                value[self.name].removevalue(self.__parent__, False)
            self.remove(self.valuekey)


class CompositMultipleProperty(CompositProperty):

    def __init__(self, name, opposit=None, isunique=False, values=None):
        super(CompositMultipleProperty, self).__init__(name, opposit, isunique)

    def addvalue(self, value, initiator=True):
        if isunique and value in self.values():
            return

        if initiator and self.opposit is not None:
            value[self.opposit].addvalue(self.__parent__, False)

        # name = INameChoser(value).chosename()
        if getattr(value,'__parent__', None) is not None:
            value.__parent__.removevalue(value)

        self.add(name, value)

    def setvalue(self, value, initiator=True):
        self.removevalue(self.getvalue())
        if value:
            for v in value:
                self.addvalue(value)

    def getvalue(self):
        self.values()

    def removevalue(self, value, initiator=True):
        for v in value:
            if initiator and self.opposit is not None:
                v[self.name].removevalue(self.__parent__, False)

            if self.__contains__(v.__name__):
                self.remove(v.__name__)


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

   
