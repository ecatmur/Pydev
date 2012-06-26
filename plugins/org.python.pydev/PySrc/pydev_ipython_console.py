import sys
from pydev_console_utils import BaseInterpreterInterface
import re

#Uncomment to force PyDev standard shell.   
#raise ImportError()

try:
    from pydev_ipython_console_010 import PyDevFrontEnd
    sys.stderr.write('PyDev console: using IPython 0.10\n')
except ImportError:
    #IPython 0.11 broke compatibility...
    from pydev_ipython_console_011 import PyDevFrontEnd
    sys.stderr.write('PyDev console: using IPython 0.11\n')
 
# NB this is a cyclic import ; fix someother way.
#from pydevconsole import log

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
        self.interpreter = PyDevFrontEnd()
        self._input_error_printed = False


    def doAddExec(self, line):
        return bool(self.interpreter.addExec(line))
    
    def getNamespace(self):
        return self.interpreter.getNamespace()

    def getCompletions(self, text, act_tok, ipython_only):
        if not text:
            return []
        try:
            ipython_completion = ipython_only or text.startswith('%')
            if not ipython_completion:
                s = re.search(r'\bcd\b', text)
                if s is not None and s.start() == 0:
                    ipython_completion = True
                
            if ipython_completion:
                TYPE_LOCAL = '9'

                # looks like:
                # text = numpy.  -> _line = numpy.  ; completions = [numpy.abs, numpy....
                # text = dir(a   -> _line = a ; completions = [abs, ...
                _line, completions = self.interpreter.complete(text)

                if text.strip().startswith("cd "):
                    # TODO: it might be better to make the completion API return the fully completed string in all cases
                    text_prefix = text[:len(text) - len(_line)]
                    completions = [text_prefix + x for x in completions]
                else:
                    # Note that PyDev doesn't expect completions with dots in the name, as might be 
                    # return by this API. See PyDevConsoleCommunciation#convertToICompletions
                    completions = [comp if not '.' in comp else comp[comp.rfind('.') + 1:] for comp in completions]

                #log("ipython completion: " + text + " -> " + str(_line) + " , " + str(completions) )

                ret = []
                append = ret.append
                for completion in completions:
                    # Return the full completion
                    append((completion, '', '', TYPE_LOCAL))
                return ret

            #Otherwise, use the default PyDev completer (to get nice icons)
            from _completer import Completer
            completer = Completer(self.getNamespace(), None)
            return completer.complete(act_tok)
        except:
            import traceback;traceback.print_exc()
            return []

    def interrupt(self):
        self.interpreter.interrupt()

    def close(self):
        sys.exit(0)

