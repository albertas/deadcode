'''
DeadCode PEP1:  Make usage tracking more precise.

    Problem statement:
        A variable name has to be unique in a whole code base in order to make detect its usage properly.
        When the variable with the same name is defined several times a different approach has to be taken into account
        Variable definitoin scope has to be tracked.
        When the usage is being detected, the scope of the used variable has to be correctly identified.


    Argumentation:
        Its hard to track every single variable definition, since its being renamed during the calls.
            Attribute accesses map could be built for a function definition.
                This access map could be applied for different invocation arguments (we know the type of the attributes).

    Example:

    Solution:
        Feature request:
            Track the scopes where variables are being defined.

        Feature request:
            Build local scopes of defined variables (available classes).

            During instantiation track the type of the variable and mark the usages of those classes.

        Feature request:
            For invocation: resolve which arguments were converted into which parameters.

        Feature request:
            When a variable value is being assigned, the type of value has to be tracked.
                Which class usages have to registered, when instance attributes are being used?

        Insight:
            The data structure for storing used code items should be built by scope, instead of a common pool of names.
                When an attribute is used of a variable in local scope: its types usage has to be marked as used.




    How could that look like?
        when parsing function annotation: build argument usage map.
        for every invocation: compile mapping from invocation arguments to parameters map
            update invocation argument usage based on function parameter usage map.



        When an instance is being assigned: its type have to be assigned.

        on instance creation: its type has to be assigned to


'''


### Parsed of ast:
# Module(
#     body=[
#         ClassDef(
#             name='Bar',
#             bases=[],
#             keywords=[],
#             body=[
#                 FunctionDef(
#                     name='bar',
#                     args=arguments(
#                         posonlyargs=[],
#                         args=[
#                             arg(arg='self')],
#                         kwonlyargs=[],
#                         kw_defaults=[],
#                         defaults=[]),
#                     body=[
#                         Pass()],
#                     decorator_list=[])],
#             decorator_list=[]),
#         FunctionDef(
#             name='labas',
#             args=arguments(
#                 posonlyargs=[],
#                 args=[
#                     arg(arg='instance')],
#                 kwonlyargs=[],
#                 kw_defaults=[],
#                 defaults=[]),
#             body=[
#                 Expr(
#                     value=Call(
#                         func=Name(id='print', ctx=Load()),
#                         args=[
#                             Call(
#                                 func=Attribute(
#                                     value=Name(id='instance', ctx=Load()),
#                                     attr='bar',
#                                     ctx=Load()),
#                                 args=[],
#                                 keywords=[])],
#                         keywords=[]))],
#             decorator_list=[]),
#         Expr(
#             value=Call(
#                 func=Name(id='labas', ctx=Load()),
#                 args=[
#                     Call(
#                         func=Name(id='Bar', ctx=Load()),
#                         args=[],
#                         keywords=[])],
#                 keywords=[]))],
#     type_ignores=[])


code = """
class Bar:
    def bar(self):
        pass


def labas(instance):
    print(instance.bar())


labas(Bar())
"""




# The idea is that I could mock arguments using MagicMock - provide the instance it self, or the scope.
# Then evaluate the invocation using python eval and check the resulting arguments inside the function call.
import ast

def show(node: ast.AST) -> None:
    print(ast.dump(node, indent=4))


def get_instance(code):
    parsed = ast.parse(code)

    # I would like to get these lines:
    #
    # labas(Bar())
    # def labas(instance):
    #
    # I would like to construct this:
    # MagicMock.expression = "Bar()"
    # def labas(instance):
    #     construct_function_scope(locals())  # Problem: how to applie AST parsing, when I know the types of the arguments?
    #                                         # I should ast parse the function,
                                              # but use the meta information of the function scope,
                                              # which was constructed using evaluation.
    #     ...
    # labas(mock)  # - was that mock executed?
    #
    #

    show(parsed)

get_instance(code)

#######################################################################
# I have a line where the function is defined.                        #
# I have a call of the function: how the parameters are provided.     #
#######################################################################


# The steps to solve this issue:
# I have to store the invocations of the function






