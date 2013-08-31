"""Interface to TerminalInteractiveShell for PyDev Interactive Console frontend
   for IPython 0.11 to 1.0+.
"""

from __future__ import print_function
import re
from IPython.core.error import UsageError
from IPython.core.inputsplitter import IPythonInputSplitter
from IPython.core.interactiveshell import InteractiveShell, InteractiveShellABC
from IPython.core.usage import default_banner_parts
try:
    from IPython.terminal.interactiveshell import TerminalInteractiveShell
except ImportError:
    # Versions of IPython [0.11,1.0) had an extra hierarchy level
    from IPython.frontend.terminal.interactiveshell import TerminalInteractiveShell
from IPython.utils.traitlets import CBool, Unicode

pydev_banner_parts = [
    '\n',
    'PyDev -- Python IDE for Eclipse\n',  # @todo can we get a version number in here?
    'For help on using PyDev\'s Console see http://pydev.org/manual_adv_interactive_console.html\n',
]

default_pydev_banner_parts = default_banner_parts + pydev_banner_parts

default_pydev_banner = ''.join(default_pydev_banner_parts)

def show_in_pager(self, strng):
    """ Run a string through pager """
    # On PyDev we just output the string, there are scroll bars in the console
    # to handle "paging". This is the same behaviour as when TERM==dump (see
    # page.py)
    print(strng)

class PyDevTerminalInteractiveShell(TerminalInteractiveShell):
    banner1 = Unicode(default_pydev_banner, config=True,
        help="""The part of the banner to be printed before the profile"""
    )

    # @todo editor
    # @todo term_title: (can PyDev's title be changed???, see terminal.py for where to inject code, in particular set_term_title as used by %cd)
    # for now, just disable term_title
    term_title = CBool(False)

    # Note in version 0.11 there is no guard in the IPython code about displaying a
    # warning, so with 0.11 you get:
    #  WARNING: Readline services not available or not loaded.
    #  WARNING: The auto-indent feature requires the readline library
    # Disable readline, readline type code is all handled by PyDev (on Java side)
    readline_use = CBool(False)
    # autoindent has no meaning in PyDev (PyDev always handles that on the Java side),
    # and attempting to enable it will print a warning in the absence of readline.
    autoindent = CBool(False)
    # Force console to not give warning about color scheme choice and default to NoColor.
    # @todo It would be nice to enable colors in PyDev but:  
    # - The PyDev Console (Eclipse Console) does not support the full range of colors, so the
    #   effect isn't as nice anyway at the command line
    # - If done, the color scheme should default to LightBG, but actually be dependent on
    #   any settings the user has (such as if a dark theme is in use, then Linux is probably
    #   a better theme).
    colors_force = CBool(True)
    colors = Unicode("NoColor")

    # In the PyDev Console, GUI control is done via hookable XML-RPC server
    @staticmethod
    def enable_gui(gui=None, app=None):
        """Switch amongst GUI input hooks by name.
        """
        # Deferred import
        from pydev_ipython.inputhook import enable_gui as real_enable_gui
        try:
            return real_enable_gui(gui, app)
        except ValueError as e:
            raise UsageError("%s" % e)

    #-------------------------------------------------------------------------
    # Things related to hooks
    #-------------------------------------------------------------------------

    def init_hooks(self):
        super(PyDevTerminalInteractiveShell, self).init_hooks()
        self.set_hook('show_in_pager', show_in_pager)

    #-------------------------------------------------------------------------
    # Things related to exceptions
    #-------------------------------------------------------------------------

    def showtraceback(self, exc_tuple=None, filename=None, tb_offset=None,
                  exception_only=False):
        # IPython does a lot of clever stuff with Exceptions. However mostly
        # it is related to IPython running in a terminal instead of an IDE.
        # (e.g. it prints out snippets of code around the stack trace)
        # PyDev does a lot of clever stuff too, so leave exception handling
        # with default print_exc that PyDev can parse and do its clever stuff
        # with (e.g. it puts links back to the original source code)
        import traceback;traceback.print_exc()

    #-------------------------------------------------------------------------
    # Things related to aliases
    #-------------------------------------------------------------------------

    def init_alias(self):
        # InteractiveShell defines alias's we want, but TerminalInteractiveShell defines
        # ones we don't. So don't use super and instead go right to InteractiveShell
        InteractiveShell.init_alias(self)

    #-------------------------------------------------------------------------
    # Things related to exiting
    #-------------------------------------------------------------------------
    def ask_exit(self):
        """ Ask the shell to exit. Can be overiden and used as a callback. """
        # @todo PyDev's console does not have support from the Python side to exit
        # the console. If user forces the exit (with sys.exit()) then the console
        # simply reports errors. e.g.:
        # >>> import sys
        # >>> sys.exit()
        # Failed to create input stream: Connection refused
        # >>>
        # Console already exited with value: 0 while waiting for an answer.
        # Error stream:
        # Output stream:
        # >>>
        #
        # Alternatively if you use the non-IPython shell this is what happens
        # >>> exit()
        # <type 'exceptions.SystemExit'>:None
        # >>>
        # <type 'exceptions.SystemExit'>:None
        # >>>
        #
        super(PyDevTerminalInteractiveShell, self).ask_exit()
        print('To exit the PyDev Console, terminate the console within Eclipse.')

    #-------------------------------------------------------------------------
    # Things related to magics
    #-------------------------------------------------------------------------

    def init_magics(self):
        super(PyDevTerminalInteractiveShell, self).init_magics()
        # @todo Any additional magics for PyDev?

InteractiveShellABC.register(PyDevTerminalInteractiveShell)  # @UndefinedVariable

#=======================================================================================================================
# PyDevFrontEnd
#=======================================================================================================================
class PyDevFrontEnd:

    def __init__(self, *args, **kwargs):
        # Create and initialize our IPython instance.
        self.ipython = PyDevTerminalInteractiveShell.instance()
        # Create an input splitter to handle input separation
        self.input_splitter = IPythonInputSplitter()

        # Display the IPython banner, this has version info and
        # help info
        self.ipython.show_banner()

    def complete(self, string):
        return self.ipython.complete(None, line=string)

    def getCompletions(self, text, act_tok):
        try:
            ipython_completion = text.startswith('%')
            if not ipython_completion:
                s = re.search(r'\bcd\b', text)
                if s is not None and s.start() == 0:
                    ipython_completion = True

            if ipython_completion:
                TYPE_LOCAL = '9'
                _line, completions = self.complete(text)

                ret = []
                append = ret.append
                for completion in completions:
                    append((completion, '', '', TYPE_LOCAL))
                return ret

            # Otherwise, use the default PyDev completer (to get nice icons)
            from _pydev_completer import Completer
            completer = Completer(self.getNamespace(), None)
            return completer.complete(act_tok)
        except:
            import traceback;traceback.print_exc()
            return []


    def getNamespace(self):
        return self.ipython.user_ns

    def addExec(self, line):
        self.input_splitter.push(line)
        if not self.input_splitter.push_accepts_more():
            self.ipython.run_cell(self.input_splitter.source_reset(), store_history=True)
            return False
        else:
            return True

# If we have succeeded in importing this module, then monkey patch inputhook
# in IPython to redirect to PyDev's version. This is essential to make
# %gui in 0.11 work (0.12+ fixes it by calling self.enable_gui, which is implemented
# above, instead of inputhook.enable_gui).
# See testGui (test_pydev_ipython_011.TestRunningCode) which fails on 0.11 without
# this patch
import IPython.lib.inputhook
import pydev_ipython.inputhook
IPython.lib.inputhook.enable_gui = pydev_ipython.inputhook.enable_gui
# In addition to enable_gui, make all publics in pydev_ipython.inputhook replace
# the IPython versions. This enables the examples in IPython's examples/lib/gui-*
# to operate properly because those examples don't use %gui magic and instead
# rely on using the inputhooks directly.
for name in pydev_ipython.inputhook.__all__:
    setattr(IPython.lib.inputhook, name, getattr(pydev_ipython.inputhook, name))
