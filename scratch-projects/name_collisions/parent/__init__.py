# evil code! Aliasing the classname parent.child.A
# creates a collision because of our use of fully-qualified names
class child:

    class A:
        x: int = 5
