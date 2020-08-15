class A:
    def __init__(self, number):
        self.number = number

    def default_func(self):
        print("Default behavior :", self.number)

    func = default_func


class Modifier:
    def __init__(self, number):
        self.number = number

    def modifyA(self):
        A.func = self.substitute

    def substitute(self, objectA):
        print("Modified behavior :", self.number, objectA.number)

obj = A(5)
modif = Modifier(3)

A.func(obj)

modif.modifyA()

A.func(obj)
    
