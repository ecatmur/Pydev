
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
import thread, time

try:
    False
    True
except NameError: # version < 2.3 -- didn't have the True/False builtins
    import __builtin__
    setattr(__builtin__, 'True', 1) #Python 3.0 does not accept __builtin__.True = 1 in its syntax
    setattr(__builtin__, 'False', 0)

from pydev_console_utils import BaseStdIn, StdIn, BaseInterpreterInterface
sys.stdin = BaseStdIn()



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
        self.namespace = globals()
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

import threading
import traceback
from pydev_imports import SimpleXMLRPCServer, Queue
from wing_extensions._matplotlib import _ExecHelper

import logging
def log(msg):
    logging.getLogger('pydevconsole').debug(msg)

class PyDevServer(SimpleXMLRPCServer):
    def __init__(self, host, port):
        self.req_queue = Queue.Queue()
        self.resp_queue = Queue.Queue()
        SimpleXMLRPCServer.__init__(self, (host,port), logRequests=False)
        self.register_function(self.addExec)
        self.register_function(self.getCompletions)
        self.register_function(self.getDescription)
        self.register_function(self.close)

    def addExec(self, line):
        log("server-addExec: %r" % line)
        self.req_queue.put(('addExec',(line,)))
        return self.resp_queue.get(block=True)

    def getCompletions(self, text, act_tok, ipython_only):
        log("server-getCompletions: %r %r %r" % (text, act_tok, ipython_only))
        self.req_queue.put(('getCompletions', (text, act_tok, ipython_only)))
        return self.resp_queue.get(block=True)

    def getDescription(self, text):
        log("server-getDescription: %r" % text)
        self.req_queue.put(('getDescription',(text,)))
        return self.resp_queue.get(block=True)

    def close(self):
        log("server-close")
        self.req_queue.put(('close',None))
        # Main thread shuts us down after this

class ServerThread(threading.Thread):
    """
    This thread runs the XMLRPC Server
    """
    def __init__(self, server):
        threading.Thread.__init__(self)
        log('Creating server thread')
        self.daemon = True
        self.server = server
        self.running = True
        log('Finished creating server thread')
    def run(self):
        log('Server running')
        self.server.serve_forever()
        log('Server finished')

def run(host, port, client_port):
    gui_helper = _ExecHelper()
    interpreter = InterpreterInterface(host, client_port)
    server = PyDevServer(host, port)
    server_thread = ServerThread(server)
    server_thread.start()
    while True:
        try:
            try:
                func_name, param = server.req_queue.get(block=True, timeout=1.0/10.0)
                log("got cmd from queue: %r %r" % (func_name, param))
                if func_name == 'addExec':
                    gui_helper.Prepare()
                func = getattr(interpreter, func_name)
                if func_name == 'close' :
                    server.shutdown()
                if param is not None:
                    log("Calling %r(%r)" % (func, param))
                    server.resp_queue.put(func(*param))
                else:
                   server.resp_queue.put(func())
                if func_name == 'addExec':
                    gui_helper.Cleanup()
            except Queue.Empty:
                #log("nothing in queue")
                gui_helper.Update()
        except:
            log(traceback.format_exc())
            print traceback.format_exc()


#=======================================================================================================================
# main
#=======================================================================================================================
if __name__ == '__main__':
    # Uncomment this to make logging go
    #import ahl.logging

    # http://jira.maninvestments.com/jira/browse/AHLRAP-1421
    def exit_on_parent_death():
        while True:
            time.sleep(5)
            # http://stackoverflow.com/questions/269494/how-can-i-cause-a-child-process-to-exit-when-the-parent-does
            if os.getppid() == 1:
                _DoExit()
    thread.start_new_thread(exit_on_parent_death, ())

    port, client_port = sys.argv[1:3]
    import pydev_localhost
    host = pydev_localhost.get_localhost()
    run(host, int(port), int(client_port))

