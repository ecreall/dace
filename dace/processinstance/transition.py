class Transition:

    def __init__(self, source, target):
        self.source = source
        self.target = target


    def equal(self, transition):
        return self.source is transition.source and self.target is transition.target

    def __repr__(self):
        return "Transition(%r, %r)" % (self.source, self.target)
