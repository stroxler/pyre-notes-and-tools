### Base __init_subclass__ example ###

class Base:
    @staticmethod
    def __init_subclass__(**kwargs):
        print("Base.__init_subclass__", kwargs)
    
    
class Foo0(Base, x=True, y=6): pass

# Base.__init_subclass__ {'x': True, 'y': 6}

### Metaclass __init__ + __new__ example ###

class Meta(type):
    def __init__(cls, name, bases, namespace, **kwargs):
       print("Meta.__init__(", name, ")", kwargs)
       super().__init__(name, bases, namespace)
    
    def __new__(metacls, name, bases, namespace, **kwargs):
       print("Meta.__new__(", name, ")", kwargs)
       return super().__new__(metacls, name, bases, namespace)
    
class Foo1(metaclass=Meta, x=True, y=6):
   pass


# Meta.__new__( Foo1 ) {'x': True, 'y': 6}
# Meta.__init__( Foo1 ) {'x': True, 'y': 6}


### Example of both: the metaclass "wins" ###

class Middle(metaclass=Meta, x=True, y=6):
    @staticmethod
    def __init_subclass__(**kwargs):
        print("Middle.__init_subclass__", kwargs)
   

class Lower(Middle, x=False, y=7):
   pass

# Meta.__new__( Middle ) {'x': True, 'y': 6}
# Meta.__init__( Middle ) {'x': True, 'y': 6}
# Meta.__new__( Lower ) {'x': False, 'y': 7}
# Middle.__init_subclass__ {}
# Meta.__init__( Lower ) {'x': False, 'y': 7}

