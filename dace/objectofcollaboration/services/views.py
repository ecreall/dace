from substanced.sdi import mgmt_view
from substanced.sdi import LEFT

from ..runtime import Runtime
from .processdef_container import ProcessDefinitionContainer



@mgmt_view(
    name = 'Processes',
    context=Runtime,
    renderer='templates/runtime_view.pt',
    tab_near=LEFT
    )
class RuntimeView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request


    def _processes(self):
        processes = self.context.processes
        allprocesses = []
        for p in processes:
            processe = {'url':self.request.mgmt_path(p, '@@contents'), 'process':p}
            allprocesses.append(processe) 

        return allprocesses

    def __call__(self):
       result = {'processes': self._processes()}
       return result


@mgmt_view(
    name = 'Processes',
    context=ProcessDefinitionContainer,
    renderer='templates/defcontainer_view.pt',
    tab_near=LEFT
    )
class ProcessDefinitionContainerView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request


    def _processes(self):
        processes = self.context.definitions
        allprocesses = []
        for p in processes:
            processe = {'url':self.request.mgmt_path(p, '@@contents'), 'process':p}
            allprocesses.append(processe) 

        return allprocesses

    def __call__(self):
       result = {'processes': self._processes()}
       return result
