# evil code! Aliasing the classname parent.child.A
# creates a collision because of our use of fully-qualified names
class child0:

    class A:
        x: str = "child0.A.x in parent/__init__"

child1: str = "value of child1 in parent/__init__"

def __getattr__(name: str):
    return f"__getattr__ produced {name}"
