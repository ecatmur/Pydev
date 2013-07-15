
# This import is needed as pkg_resources does some one-time library path
# checking, the results of which are invalidated by Ipython as it messes
# with sys.modules for the readline library.
import pkg_resources
try:
    from code import InteractiveConsole
except ImportError:
    from pydevconsole_code_for_ironpython import InteractiveConsole

import os
import sys

try:
    False
    True
except NameError: # version < 2.3 -- didn't have the True/False builtins
    import __builtin__
    setattr(__builtin__, 'True', 1) #Python 3.0 does not accept __builtin__.True = 1 in its syntax
    setattr(__builtin__, 'False', 0)

import threading
import functools
import atexit
from pydev_imports import SimpleXMLRPCServer, Queue
from pydev_console_utils import BaseStdIn, StdIn, BaseInterpreterInterface


try:
    class ExecState:
        FIRST_CALL = True
        PYDEV_CONSOLE_RUN_IN_UI = False #Defines if we should run commands in the UI thread.

    from org.python.pydev.core.uiutils import RunInUiThread #@UnresolvedImport
    from java.lang import Runnable #@UnresolvedImport
    class Command(Runnable):

        def __init__(self, interpreter, line):
            self.interpreter = interpreter
            self.line = line

        def run(self):
            if ExecState.FIRST_CALL:
                ExecState.FIRST_CALL = False
                sys.stdout.write('\nYou are now in a console within Eclipse.\nUse it with care as it can halt the VM.\n')
                sys.stdout.write('Typing a line with "PYDEV_CONSOLE_TOGGLE_RUN_IN_UI"\nwill start executing all the commands in the UI thread.\n\n')

            if self.line == 'PYDEV_CONSOLE_TOGGLE_RUN_IN_UI':
                ExecState.PYDEV_CONSOLE_RUN_IN_UI = not ExecState.PYDEV_CONSOLE_RUN_IN_UI
                if ExecState.PYDEV_CONSOLE_RUN_IN_UI:
                    sys.stdout.write('Running commands in UI mode. WARNING: using sys.stdin (i.e.: calling raw_input()) WILL HALT ECLIPSE.\n')
                else:
                    sys.stdout.write('No longer running commands in UI mode.\n')
                self.more = False
            else:
                self.more = self.interpreter.push(self.line)


    def Sync(runnable):
        if ExecState.PYDEV_CONSOLE_RUN_IN_UI:
            return RunInUiThread.sync(runnable)
        else:
            return runnable.run()

except:
    #If things are not there, define a way in which there's no 'real' sync, only the default execution.
    class Command:

        def __init__(self, interpreter, line):
            self.interpreter = interpreter
            self.line = line

        def run(self):
            self.more = self.interpreter.push(self.line)

    def Sync(runnable):
        runnable.run()


try:
    try:
        execfile #Not in Py3k
    except NameError:
        from pydev_imports import execfile
        import builtins #@UnresolvedImport -- only Py3K
        builtins.execfile = execfile

except:
    pass


#=======================================================================================================================
# InterpreterInterface
#=======================================================================================================================
class InterpreterInterface(BaseInterpreterInterface):
    '''
        The methods in this class should be registered in the xml-rpc server.
    '''

    def __init__(self, host, client_port):
        self.client_port = client_port
        self.host = host
        try:
            import pydevd
        except:
            # This happens on Jython embedded in host eclipse
            self.namespace = globals()
        else:
            #Adapted from the code in pydevd
            #patch provided by: Scott Schlesier - when script is run, it does not
            #pretend pydevconsole is not the main module, and
            #convince the file to be debugged that it was loaded as main
            sys.modules['pydevconsole'] = sys.modules['__main__']
            sys.modules['pydevconsole'].__name__ = 'pydevconsole'

            from imp import new_module
            m = new_module('__main__')
            sys.modules['__main__'] = m
            ns = m.__dict__
            try:
                ns['__builtins__'] = __builtins__
            except NameError:
                pass #Not there on Jython...
            self.namespace = ns
        self.interpreter = InteractiveConsole(self.namespace)
        self._input_error_printed = False


    def doAddExec(self, line):
        command = Command(self.interpreter, line)
        Sync(command)
        return command.more


    def getNamespace(self):
        return self.namespace


    def getCompletions(self, text, act_tok, ipython_only):
        try:
            from _completer import Completer
            completer = Completer(self.namespace, None)
            return completer.complete(act_tok)
        except:
            import traceback;traceback.print_exc()
            return []


    def close(self):
        sys.exit(0)


try:
    from pydev_ipython_console import InterpreterInterface
except:
    sys.stderr.write('PyDev console: using default backend (IPython not available).\n')
    pass #IPython not available, proceed as usual.

#=======================================================================================================================
# _DoExit
#=======================================================================================================================
def _DoExit(*args):
    '''
        We have to override the exit because calling sys.exit will only actually exit the main thread,
        and as we're in a Xml-rpc server, that won't work.
    '''

    try:
        import java.lang.System
        java.lang.System.exit(1)
    except ImportError:
        if len(args) == 1:
            os._exit(args[0])
        else:
            os._exit(0)



#=======================================================================================================================
# AHL Pydev Extensions
#=======================================================================================================================
# Set terminal to 'dumb' - this fixes terminal paging in Ipython 0.11
os.environ['TERM'] = 'dumb'

import signal
import logging
def log(msg):
    logging.getLogger('pydevconsole').debug(msg)


class ThreadedXMLRPCServer(SimpleXMLRPCServer):
    def __init__(self, addr, main_loop, **kwargs):
        SimpleXMLRPCServer.__init__(self, addr, **kwargs)
        self.main_loop = main_loop
        self.resp_queue = Queue.Queue()

    def register_function(self, fn, name=None):
        @functools.wraps(fn)
        def proxy_fn(*args, **kwargs):
            def main_loop_cb():
                try:
                    int_handler = signal.signal(signal.SIGINT, signal.default_int_handler)
                    sys.exc_clear()
                    log("Calling %r(*%r, **%r)" % (fn, args, kwargs))
                    self.resp_queue.put(fn(*args, **kwargs))
                except:
                    import traceback;traceback.print_exc()
                    log(traceback.format_exc())
                    self.resp_queue.put(None)
                finally:
                    signal.signal(signal.SIGINT, int_handler)
            self.main_loop.call_in_main_thread(main_loop_cb)
            return self.resp_queue.get(block=True)
        SimpleXMLRPCServer.register_function(self, proxy_fn, name)


class MainLoop(object):
    def run(self):
        """Run the main loop of the GUI library.  This method should not
        return.
        """
        raise NotImplementedError

    def call_in_main_thread(self, cb):
        """Given a callable `cb`, pass it to the main loop of the GUI library
        so that it will eventually be called in the main thread.  It's OK but
        not compulsory for this method to block until the main thread has
        finished processing `cb`; as such, this method must not be called from
        the main thread.
        """
        raise NotImplementedError


class QtMainLoop(MainLoop):
    def __init__(self):
        from PyQt4 import QtCore, QtGui
        self.ping = type('Ping', (QtCore.QThread,), {'call': QtCore.pyqtSignal(object)})()
        self.ping.call.connect(lambda cb: cb(), type=QtCore.Qt.BlockingQueuedConnection)
        self.app = QtGui.QApplication([])

    def run(self):
        while True:
            self.app.exec_()

    def call_in_main_thread(self, cb):
        self.ping.call.emit(cb)


class GtkMainLoop(MainLoop):
    def run(self):
        import gtk
        gtk.main()

    def call_in_main_thread(self, cb):
        import gobject
        gobject.idle_add(cb)


class NoGuiMainLoop(MainLoop):
    """
    If we can't initialize a GUI, it still makes sense to run the XML-RPC
    server in a separate thread so we can handle things like SIGINT properly.
    """
    def __init__(self):
        self.queue = Queue.Queue()

    def run(self):
        while True:
            cb = self.queue.get(block=True)
            try:
                cb()
            except:
                import traceback;traceback.print_exc()

    def call_in_main_thread(self, cb):
        self.queue.put(cb)


#=======================================================================================================================
# StartServer
#=======================================================================================================================
def StartServer(host, port, client_port):
    try:
        from pydev_ipython_console import find_gui_and_backend
        gui, _ = find_gui_and_backend()
    except Exception as ex:
        sys.stdout.write("Can't initialize GUI integration: %s\n" % str(ex))
        gui = None
    MainLoop_cls = {'qt': QtMainLoop,
                    'qt4': QtMainLoop,
                    'gtk': GtkMainLoop,
                    }.get(gui, NoGuiMainLoop)
    main_loop = MainLoop_cls()

    try:
        interpreter = InterpreterInterface(host, client_port)
        server = ThreadedXMLRPCServer((host, port), main_loop, logRequests=False)
    except:
        sys.stderr.write('Error starting server with host: %s, port: %s, client_port: %s\n' % (host, port, client_port))
        raise

    signal.signal(signal.SIGINT, lambda signum, frame: interpreter.interrupt())

    #Functions for basic protocol
    server.register_function(interpreter.addExec)
    server.register_function(interpreter.getCompletions)
    server.register_function(interpreter.getDescription)
    server.register_function(interpreter.close)

    #Functions so that the console can work as a debugger (i.e.: variables view, expressions...)
    server.register_function(interpreter.connectToDebugger)
    server.register_function(interpreter.postCommand)
    server.register_function(interpreter.hello)

    atexit.register(server.shutdown)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    main_loop.run()


#=======================================================================================================================
# main
#=======================================================================================================================
if __name__ == '__main__':
    sys.stdin = BaseStdIn()

    # Uncomment this to make logging go
    import ahl.logging

    # http://jira.maninvestments.com/jira/browse/AHLRAP-1421
    import time
    def exit_on_parent_death():
        while True:
            time.sleep(5)
            # http://stackoverflow.com/questions/269494/how-can-i-cause-a-child-process-to-exit-when-the-parent-does
            if os.getppid() == 1:
                _DoExit()
    exit_on_parent_death_thread = threading.Thread(target=exit_on_parent_death)
    exit_on_parent_death_thread.daemon = True
    exit_on_parent_death_thread.start()

    port, client_port = sys.argv[1:3]
    import pydev_localhost
    StartServer(pydev_localhost.get_localhost(), int(port), int(client_port))
