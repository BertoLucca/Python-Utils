# Definition of the `Freeze` function. Any other object here is either from
# Python's standard library or defined as a helper and should be not cared
# about.
#
# The `Freeze` function, which also is a decorator, is responsible for searching
# any directly accessible constant value stored on a variable refered inside of
# a Function, Lambda or Class and "freeze" it by replacing its reference for its
# actual value instead.
#
# This function is not meant to speed up codes, in fact it may even slow them,
# but it ensures any global value defined before its call remains "unchanged".

import ast
import inspect

from types import FunctionType

_constantTypes = (int, float, complex, str, tuple, bytes, bool, type(None))

class NotInitialized:
    pass # It does nothing


class FreezeError(Exception):
    pass


class ConstantReplacer(ast.NodeTransformer):
    def __init__(self, freeze_data):
        super().__init__()
        self.freeze_data = freeze_data
        self.freeze_keys = freeze_data.keys()
        
    def visit_Name(self, node):
        if node.id in self.freeze_keys:
            if isinstance(node.ctx, ast.Load):
                return ast.Constant(value=self.freeze_data[node.id], kind=None)
            else:
                del self.freeze_data[node.id]
                return node
                    
        return node

    def visit_Global(self, node):
        return None
        

def Freeze(fnc = NotInitialized,
           enforce_globals = False,
           overwrite_with = {},
           ignore = [],
           *, depth = 0):

    if fnc is NotInitialized:
        return lambda _fnc: \
               Freeze(fnc = _fnc, enforce_globals = enforce_globals,
                      overwrite_with = overwrite_with, ignore = ignore,
                      depth = 1)
    elif not isinstance(fnc, (FunctionType, type)):
        # This decorator should work only on Functions, Lambdas, and Classes.
        raise FreezeError("incorrect input.")

    try:
        print(f">>> Excecuting `Freeze` for funcion `{fnc.__qualname__}`.") 
        src = inspect.getsource(fnc)

        try:
            source_code = inspect.cleandoc(src)
            astMod = ast.parse(source_code)
            
        except IndentationError:
            pass
        
        finally:
            astMod = ast.parse(src)
            astTgt = astMod.body[0]
        
        # Go to the scope where the function is defined.
        frame = inspect.currentframe().f_back.f_back if depth else \
                inspect.currentframe().f_back

        if enforce_globals:
            scope = frame.f_locals.copy()
            scope.update(frame.f_globals)
        else:
            scope = frame.f_globals.copy()
            scope.update(frame.f_locals)

        # Don't care about 'nonlocal' as these are "frozen" to some extent.
           
    except Exception as error:
        raise FreezeError("while trying to freeze the function "
            f"`{fnc.__qualname__}`, an error of type '{type(e)}' occured.")

    finally:
        del frame

    # This block removes 'Freeze' from the decorator list.
    # <!-- Begin -->

    # Finds the name by wich `Freeze` is stored in the code. Otherwise it
    # will notice the function was called on a <lambda>.
    try:
        for deco in astTgt.decorator_list:
            if isinstance(deco, ast.Name) and scope[deco.id] is Freeze:
                _self = deco.id
                break
            elif isinstance(deco, ast.Call) and scope[deco.func.id] is Freeze:
                _self = deco.func.id
                break

        newDecoList = []
        for deco in astTgt.decorator_list:
            # @Freeze
            if isinstance(deco, ast.Name) and deco.id != _self:
                newDecoList.append(deco)

            # @Freeze(...)
            elif isinstance(deco, ast.Call) and deco.func.id != _self:
                newDecoList.append(deco)
                
    except AttributeError as e:
        isNotAssign = False

        # This is, likely, a lambda function or assignment of a Freeze call.
        if isinstance(astTgt, ast.Assign):
            astTgt = astTgt.value.args[0]
        else:
            raise e
    else:
        isNotAssign = True

    # <!-- End -->

    # Clean our stored variables to keep only the values which are stored as
    # constants, or not to-be ignored.
    for key, value in scope.copy().items(): 
        if not isinstance(value, _constantTypes):
            del scope[key]
        elif key in ignore:
            del scope[key]

    newFnc = ConstantReplacer(scope).visit(astTgt)
    
    if isNotAssign:
        newFnc.decorator_list = newDecoList

    ast.fix_missing_locations(newFnc)

    if isNotAssign:
        astMod.body[0] = newFnc
    else:
        astMod.body[0].value = newFnc

    exec(compile(astMod, '<ast>', 'exec'))
    
    if isNotAssign:
        fnc.__code__ = locals()[newFnc.name].__code__
    else:
        fnc = locals()[astMod.body[0].targets[0].id]

    return fnc
