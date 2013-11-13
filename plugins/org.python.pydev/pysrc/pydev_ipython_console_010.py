from IPython.frontend.prefilterfrontend import PrefilterFrontEnd
from pydev_console_utils import Null
from pydev_imports import xmlrpclib
import os
import sys
import re
original_stdout = sys.stdout
original_stderr = sys.stderr


# If user specifies a GUI, that dictates the backend, otherwise we read the
# user's mpl default from the mpl rc structure
backends = {'tk': 'TkAgg',
            'gtk': 'GTKAgg',
            'wx': 'WXAgg',
            'qt': 'Qt4Agg', # qt3 not supported
            'qt4': 'Qt4Agg',
            'osx': 'MacOSX',
            'inline' : 'module://IPython.zmq.pylab.backend_inline'}

# We also need a reverse backends2guis mapping that will properly choose which
# GUI support to activate based on the desired matplotlib backend.  For the
# most part it's just a reverse of the above dict, but we also need to add a
# few others that map to the same GUI manually:
backend2gui = dict(zip(backends.values(), backends.keys()))
# In the reverse mapping, there are a few extra valid matplotlib backends that
# map to the same GUI support
backend2gui['GTK'] = backend2gui['GTKCairo'] = 'gtk'
backend2gui['WX'] = 'wx'
backend2gui['CocoaAgg'] = 'osx'


# Backport from IPython 0.11
def find_gui_and_backend(gui=None):
    """Given a gui string return the gui and mpl backend.

    Parameters
    ----------
    gui : str
        Can be one of ('tk','gtk','wx','qt','qt4','inline').

    Returns
    -------
    A tuple of (gui, backend) where backend is one of ('TkAgg','GTKAgg',
    'WXAgg','Qt4Agg','module://IPython.zmq.pylab.backend_inline').
    """

    import matplotlib

    if gui:
        # select backend based on requested gui
        backend = backends[gui]
    else:
        backend = matplotlib.rcParams['backend']
        # In this case, we need to find what the appropriate gui selection call
        # should be for IPython, so we can activate inputhook accordingly
        gui = backend2gui.get(backend, None)
    return gui, backend


def create_editor_hook(pydev_host, pydev_client_port):
    def call_editor(self, filename, line=0, wait=True):
        """ Open an editor in PyDev """
        if line is None:
            line = 0

        # Make sure to send an absolution path because unlike most editor hooks
        # we don't launch a process. This is more like what happens in the zmqshell
        filename = os.path.abspath(filename)

        # Tell PyDev to open the editor
        server = xmlrpclib.Server('http://%s:%s' % (pydev_host, pydev_client_port))
        server.OpenEditor(filename, line)

        if wait:
            raw_input("Press Enter when done editing:")
    return call_editor

#=======================================================================================================================
# PyDevFrontEnd
#=======================================================================================================================
class PyDevFrontEnd(PrefilterFrontEnd):


    def __init__(self, pydev_host, pydev_client_port, *args, **kwargs):
        PrefilterFrontEnd.__init__(self, *args, **kwargs)
        # Disable the output trap: we want all that happens to go to the output directly
        self.shell.output_trap = Null()
        self._curr_exec_lines = []
        self._continuation_prompt = ''

        # Back channel to PyDev to open editors (in the future other
        # info may go back this way. This is the same channel that is
        # used to get stdin, see StdIn in pydev_console_utils)
        self.ipython0.set_hook('editor', create_editor_hook(pydev_host, pydev_client_port))

    def capture_output(self):
        pass


    def release_output(self):
        pass


    def continuation_prompt(self):
        return self._continuation_prompt


    def write(self, txt, refresh=True):
        original_stdout.write(txt)


    def new_prompt(self, prompt):
        self.input_buffer = ''
        # The java side takes care of this part.
        # self.write(prompt)


    def show_traceback(self):
        import traceback;traceback.print_exc()


    def write_out(self, txt, *args, **kwargs):
        original_stdout.write(txt)


    def write_err(self, txt, *args, **kwargs):
        original_stderr.write(txt)


    def getNamespace(self):
        return self.shell.user_ns

    def interrupt(self):
        pass

    def addExec(self, line):
        if self._curr_exec_lines:
            if not line:
                self._curr_exec_lines.append(line)

                # Would be the line below, but we've set the continuation_prompt to ''.
                # buf = self.continuation_prompt() + ('\n' + self.continuation_prompt()).join(self._curr_exec_lines)
                buf = '\n'.join(self._curr_exec_lines)

                self.input_buffer = buf + '\n'
                if self._on_enter():
                    del self._curr_exec_lines[:]
                    return False  # execute complete (no more)

                return True  # needs more
            else:
                self._curr_exec_lines.append(line)
                return True  # needs more

        else:

            self.input_buffer = line
            if not self._on_enter():
                # Did not execute
                self._curr_exec_lines.append(line)
                return True  # needs more

            return False  # execute complete (no more)

    def getCompletions(self, text, act_tok, ipython_only):
        try:
            ipython_completion = ipython_only or text.startswith('%')
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
