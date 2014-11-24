
import venusian

DACE_ROLES = {}


class role(object):

    def __init__(self, 
                 name='', 
                 superiors=[], 
                 lowers=[], 
                 islocal=False):
        self.name = name
        self.superiors = superiors
        self.lowers = lowers
        self.islocal = islocal

    def __call__(self, wrapped):
        def callback(scanner, name, ob):
            ob.name = self.name
            ob.islocal = self.islocal
            ob.superiors = self.superiors
            def get_allsuperiors(ob):
                superiors = list(ob.superiors)
                for sup in ob.superiors:
                    superiors.extend(get_allsuperiors(sup))

                return list(set(superiors))

            ob.all_superiors = get_allsuperiors(ob)
            for role in self.lowers:
                role.superiors.append(ob)
                role.all_superiors = get_allsuperiors(role)

            DACE_ROLES[ob.name] = ob
 
        venusian.attach(wrapped, callback)
        return wrapped


class Role(object):
    name = NotImplemented
    superiors = NotImplemented
    all_superiors = NotImplemented
    islocal = NotImplemented

@role(name='Admin')
class Administrator(Role):
    pass

@role(name='Collaborator', superiors=[Administrator])
class Collaborator(Role):
    pass
    

@role(name='System', superiors=[Administrator])
class System(Role):
    pass


@role(name='Anonymous', superiors=[Administrator])
class Anonymous(Role):
    pass


@role(name='Owner', islocal=True)
class Owner(Role):
    pass

