from substanced.folder import Folder as FD
from persistent.list import PersistentList
from dace.interfaces import INameChooser
from dace.object import Object

class Property(FD):
     
    multiple = NotImplemented

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

    multiple = NotImplemented


class CompositProperty(Property):    

    multiple = NotImplemented

    def __init__(self, name, opposit=None, isunique=False):
        Property.__init__(self, name, opposit)


class CompositUniqueProperty(CompositProperty):

    multiple = False

    def __init__(self, name, opposit=None, value=None):
        CompositProperty.__init__(self, name, opposit, True)
        self.valuekey = None
        if value is not None:
            self.addvalue(value)

    def addvalue(self, value, initiator=True):
        self.setvalue(value, initiator)

    def setvalue(self, value, initiator=True):
        if self.valuekey is not None and self.__parent__[self.valuekey] == value:
            return

        if initiator and self.opposit is not None:
            value[self.opposit].addvalue(self.__parent__, False)

        if self.valuekey is not None:
            self.removevalue(self.__parent__[self.valuekey])

        if value is None:
            self.valuekey = None
            return            

        if getattr(value,'__property__', None) is not None:
            value.__property__.removevalue(value)
 
        import pdb; pdb.set_trace()
        value.__property__ = self
        name = INameChooser(self.__parent__).chooseName(u'', value)
        self.__parent__.add(name, value)
        self.valuekey = name

    def getvalue(self):
        if self.valuekey is not None and  self.__parent__.__contains__(self.valuekey):
            return self.__parent__[self.valuekey]

        return None

    def removevalue(self, value, initiator=True):
        if self.valuekey is not None and self.__parent__[self.valuekey] == value:
            if initiator and self.opposit is not None:
                value[self.name].removevalue(self.__parent__, False)
            self.__parent__.remove(self.valuekey)


class CompositMultipleProperty(CompositProperty):

    multiple = True

    def __init__(self, name, opposit=None, isunique=False, values=None):
        super(CompositMultipleProperty, self).__init__(name, opposit, isunique)
        self.contents_keys = PersistentList()
        if values is not None:
            if (not isinstance(values, list) and not isinstance(values, tuple) ):
                values = [values]

            if values:
                self.setvalue(values)

    def addvalue(self, value, initiator=True):
        if self.isunique and value in self.getvalue():
            return

        if initiator and self.opposit is not None:
            value[self.opposit].addvalue(self.__parent__, False)

        if  getattr(value,'__property__', None) is not None :
            value.__property__.removevalue(value)

        value.__property__ = self
        name = INameChooser(self.__parent__).chooseName(u'', value)
        self.contents_keys.append(name)
        self.__parent__.add(name, value)

    def setvalue(self, value, initiator=True):
        if (not isinstance(value, list) and not isinstance(value, tuple) ):
            value = [value]

        oldvalues = self.getvalue()
        toremove = []
        toadd = []
        if value is None:
            toremove = oldvalues
        else:  
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

    multiple = False

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

    multiple = True

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


class Folder(Object, FD):

    def __init__(self):
        Object.__init__(self)
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

    def get_data2(self, node):
        result = Object.get_data(self, node)
        for p in self.attributes:
            if self[p].multiple:
                intresult = []
                values = self[p].getvalue()
                for v in values:
                    intresult.append(v.get_data(node.get(p)))

                result[p] = values
            else:
                value = self[p].getvalue()
                if value is not None:
                    result[p]=self[p].getvalue().get_data(node.get(p))

        return  result  
