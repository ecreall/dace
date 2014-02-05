class Transition:

    def __init__(self, from_, to):
        self.from_ = from_
        self.to = to

    def __repr__(self):
        return "Transition(%r, %r)" % (self.from_, self.to)
