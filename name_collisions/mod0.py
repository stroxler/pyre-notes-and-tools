from parent.child import A
import parent


child_A = A()
reveal_type(child_A.x)

parent_A = parent.child.A()
reveal_type(parent_A.x)
