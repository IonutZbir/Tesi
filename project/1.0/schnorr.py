import random

class Schnorr:
    def __init__(self, p, q, g):
        self.p = p
        self.q = q
        self.g = g

class SchnorrProver(Schnorr):
    def __init__(self, p, q, g):
        super().__init__(p, q, g)
        self.sk = random.randint(0, q - 1)
    
class SchnorrVerifier(Schnorr):
    pass
    