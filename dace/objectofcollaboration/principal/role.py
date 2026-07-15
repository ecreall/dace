# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

"""Role declarations.

Roles are classes registered by the ``@role`` venusian decorator into
``DACE_ROLES``; the decorator wires the superior/lower hierarchy both
ways and computes ``all_superiors`` transitively. ``islocal`` marks
context-local roles (``Owner``). Built-ins: Admin, Collaborator,
System, Anonymous, Owner.
"""
import venusian

DACE_ROLES = {}


class role(object):

    """Venusian decorator declaring a role and wiring its hierarchy into ``DACE_ROLES``."""
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
    """Base role: ``name``, hierarchy (``superiors``/``all_superiors``), ``islocal``."""
    name = NotImplemented
    superiors = []
    all_superiors = []
    islocal = False


@role(name='Admin')
class Administrator(Role):
    """'Admin' — implicit superior of every non-local role, granted to the sd admin."""
    pass


@role(name='Collaborator', superiors=[Administrator])
class Collaborator(Role):
    """'Collaborator' — ordinary member role."""
    pass
    

@role(name='System', superiors=[Administrator])
class System(Role):
    """'System' — the reactor's role."""
    pass


@role(name='Anonymous', superiors=[Administrator])
class Anonymous(Role):
    """'Anonymous' — unauthenticated visitors."""
    pass


@role(name='Owner', islocal=True)
class Owner(Role):
    """'Owner' — context-local role (granted per object)."""
    pass

