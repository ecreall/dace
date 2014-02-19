from zope.interface import implements
from persistent.list import PersistentList
from substanced.folder import Folder
#from zope.container.interfaces import INameChooser
#from zope.copypastemove.interfaces import IObjectMover
from .interfaces import IRuntime


class Runtime(Folder):
    implements(IRuntime)

    def __init__(self ):
        super(Runtime, self).__init__()
        self._processes = PersistentList()

    def getprocesses(self):
        return self.processes

    @property
    def processes(self):
        results = []
        for process_id in self._processes:
            results.append(self[process_id])

        return results

    def _addOneof_processes(self, Key, newprocess):
        has_key = (Key in self)
        super(Runtime, self).__setitem__(Key, newprocess)
        if (not has_key ):
            self._processes.append(Key)

    def addprocesses(self, newprocesses):
        if not isinstance(newprocesses, (list, tuple)):
            newprocesses = [newprocesses]

        chooser = INameChooser(self)
        for process in newprocesses:
            oldname = process.__name__
            name = chooser.chooseName(u'', process)
            if not process.__parent__ is None:
                process.__parent__.delKey(oldname)
                mover = IObjectMover(process)
                mover.moveTo(self, name)
                self._processes.append(name)
            else :
                self._addOneof_processes(name, process)

    def delKey(self, key):
        if key in self._processes:
            self._processes.remove(key)
