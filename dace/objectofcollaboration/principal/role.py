# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

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
            ob.superiors = list(ob.superiors)
            ob.superiors.extend(self.superiors)
            ob.superiors = list(set(ob.superiors))
            def get_allsuperiors(role_ob):
                superiors = list(role_ob.superiors)
                for sup in role_ob.superiors:
                    superiors.extend(get_allsuperiors(sup))

                return list(set(superiors))

            ob.all_superiors = list(ob.all_superiors)
            ob.all_superiors.extend(get_allsuperiors(ob))
            ob.all_superiors = list(set(ob.all_superiors))
            for role in ob.all_superiors:
                role.lowers = list(set(getattr(role, 'lowers', [])))
                role.lowers.append(ob)
                role.lowers = list(set(role.lowers))

            for role in getattr(ob, 'lowers', self.lowers):
                role.superiors = list(role.superiors)
                role.superiors.append(ob)
                role.superiors = list(set(role.superiors))
                role.all_superiors = list(role.all_superiors)
                role.all_superiors.append(ob)
                role.all_superiors.extend(ob.all_superiors)
                role.all_superiors = list(set(role.all_superiors))

            DACE_ROLES[ob.name] = ob
 
        venusian.attach(wrapped, callback)
        return wrapped


class Role(object):
    name = NotImplemented
    superiors = []
    all_superiors = []
    islocal = False


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

