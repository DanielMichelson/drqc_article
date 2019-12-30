# PR: hack of wradlib-wradlib-6c2a093c8a04/build/lib/wradlib/util.py
import warnings

class OptionalModuleStub(object):
    """Stub class for optional imports.

    Objects of this class are instantiated when optional modules are not
    present on the user's machine.
    This allows global imports of optional modules with the code only breaking
    when actual attributes from this module are called.
    """
    def __init__(self, name):
        self.name = name

    def __getattr__(self, name):
        raise AttributeError, ('Module "'+ self.name +
                           '" is not installed.\n\n' +
                           'You tried to access function/module/attribute "' +
                            name + '"\nfrom module "' + self.name + '".\nThis '+
                            'module is optional right now in wradlib.\n' +
                            'You need to separately install this dependency.\n' +
                            'Please refer to http://wradlib.bitbucket.org/gettingstarted.html#optional-dependencies\n' +
                            'for further instructions.'
                            )


def import_optional(module):
    """Allowing for lazy loading of optional wradlib modules or dependencies.

    This function removes the need to satisfy all dependencies of wradlib before
    being able to work with it.

    Parameters:
    -----------
    module : string
             name of the module

    Returns:
    --------
    mod : object
          if module is present, returns the module object, on ImportError
          returns an instance of `OptionalModuleStub` which will raise an
          AttributeError as soon as any attribute is accessed.

    Examples:
    ---------
    Trying to import a module that exists makes the module available as normal.
    You can even use an alias. You cannot use the '*' notation, or import only
    select functions, but you can simulate most of the standard import syntax
    behavior
    >>> m = import_optional('math')
    >>> m.log10(100)
    2.0

    Trying to import a module that does not exists, does not produce any errors.
    Only when some function is used, the code triggers an error
    >>> m = import_optional('nonexistentmodule')
    >>> m.log10(100)
    Traceback (most recent call last):
    ...
    AttributeError: Module "nonexistentmodule" is not installed.
    <BLANKLINE>
    You tried to access function/module/attribute "log10"
    from module "nonexistentmodule".
    This module is optional right now in wradlib.
    You need to separately install this dependency.
    Please refer to http://wradlib.bitbucket.org/gettingstarted.html#optional-dependencies
    for further instructions.
    """
    try:
        mod = __import__(module)
    except ImportError:
        mod = OptionalModuleStub(module)

    return mod
