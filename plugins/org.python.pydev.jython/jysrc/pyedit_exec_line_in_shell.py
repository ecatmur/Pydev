#--------------------------------------------------------------- REQUIRED LOCALS
#interface: String indicating which command will be executed #As this script will be watching the PyEdit (that is the actual editor in Pydev), and this script
#will be listening to it, this string can indicate any of the methods of org.python.pydev.editor.IPyEditListener
assert cmd is not None

#interface: PyEdit object: this is the actual editor that we will act upon assert editor is not None

import sys
print 'Command: ' + cmd
print 'File: ' + editor.getEditorFile().getName()
print 'sys.version:' + sys.version

from org.eclipse.jface.action import Action #@UnresolvedImport
from org.eclipse.jface.dialogs import MessageDialog #@UnresolvedImport
from org.eclipse.jface.text import IDocumentListener #@UnresolvedImport
from org.eclipse.core.runtime.jobs import Job #@UnresolvedImport
from org.eclipse.ui.progress import UIJob #@UnresolvedImport
from org.eclipse.core.runtime import Status


from org.python.pydev.core.docutils import PySelection #@UnresolvedImport
from string import rstrip

from org.python.pydev.debug.newconsole import PydevConsoleConstants
from org.python.pydev.debug.newconsole import PydevConsoleFactory #@UnresolvedImport
from org.python.pydev.debug.newconsole import PydevConsole
from org.python.pydev.editor.actions import PyAction #@UnresolvedImport

from org.eclipse.ui import PlatformUI #@UnresolvedImport
from org.eclipse.ui.console import ConsolePlugin #@UnresolvedImport
from org.eclipse.ui.console import IConsoleConstants #@UnresolvedImport
from java.lang import Runnable #@UnresolvedImport
from org.eclipse.swt.widgets import Display #@UnresolvedImport

#from com.python.pydev.interactiveconsole import EvaluateActionSetter

# This is the command ID as specified in plugin.xml
COMMAND_ID = "com.mi.ahl.eclipse.python.execLineInConsole"

import re
RE_COMMENT = re.compile('^\s*#')

class ConsoleDocumentListener(IDocumentListener):
    def __init__(self, execution_engine):
        self.execution_engine = execution_engine
        self.new_prompt = False
    
    def documentAboutToBeChanged(self,event):
        pass 
    
    def documentChanged(self,event):
        if (self.new_prompt and len(event.getText())== 0 and self.lines_to_process == 0) or self.lines_to_process < 0 :  
            self.new_prompt = False        
            self.execution_engine.complete_top_command()
        else :
            self.new_prompt = event.getText() == '>>> ' or event.getText() == '... '
            if self.new_prompt :
                self.lines_to_process = self.lines_to_process - 1
      
class DoTopCommandJob(UIJob):  
    def __init__(self, executor) :
        UIJob.__init__(self,'do top command')
        self.executor=executor
        self.setPriority(Job.SHORT)
        
    def runInUIThread(self, progress_monitor):
        try:
            self.executor._do_top_command()
        except:
            # This can be benign if, e.g. the Script Console has focus.
            pass
        return Status.OK_STATUS

class ExecuteLine(Action):
    '''
    Code to execute a line
    '''
    def __init__(self, editor=None):
        Action.__init__(self)
        self._editor = editor
        self._console = None
        self._console_listener = ConsoleDocumentListener(self)
        self._commands = []
        self._current_block_indent = None
        self._prev_line_indent = None


    def _find_top_console(self):
        def isConsoleView(view):
            if view is None:
                return False
            return view.getId() == IConsoleConstants.ID_CONSOLE_VIEW

        window = PlatformUI.getWorkbench().getActiveWorkbenchWindow()
        if window is None:
             return None
        page = window.getActivePage()
        if page is None:
            return None
        views = page.getViewReferences()

        cviews = map(lambda v: v.getView(True), filter(isConsoleView, views))
        if not len(cviews):
            return None
        return cviews[0].getConsole()

    def _show_console(self):
        def isPyDevConsole(console):
            if console is None:
                return False
            return console.getType() == PydevConsoleConstants.CONSOLE_TYPE
        
        console_manager = ConsolePlugin.getDefault().getConsoleManager()
        consoles = console_manager.getConsoles()
        
        top_console = self._find_top_console()#

        if  isPyDevConsole(top_console):
            self._console = top_console
        elif self._console not in consoles:
            pydev_consoles = filter(isPyDevConsole, consoles)
            if len(pydev_consoles):
                self._console = pydev_consoles[0]
            else: 
                self._console = PydevConsoleFactory().createConsole()

        console_manager.showConsoleView(self._console)
     
    def _get_newline(self):
        return PyAction.getDelimiter(self._editor.getDocument())

    def _get_selection(self):
        return PySelection(self._editor).getSelectedText()

    def _send_to_console(self, text):
        if len(rstrip(text)):
            self._commands.append( text ) 
            if len(self._commands)==1:
                job = DoTopCommandJob(self)
                job.schedule()
                
    def _do_top_command(self):
        document = self._console.getDocument()
        text = self._commands[0]
        document.addDocumentListener(self._console_listener)
        self._console_listener.lines_to_process = text.count('\n')
        document.replace(document.getLength(), 0, text)
    
    def complete_top_command(self):
        self._console.getDocument().removeDocumentListener(self._console_listener)
        self._commands = self._commands[1:]
        if len(self._commands) > 0 :
            job = DoTopCommandJob(self)
            job.schedule()

    def _reset_line_state(self):
        self._current_block_indent = None
        self._prev_line_indent     = None


    def _get_line(self):
        '''
        Find the current line.
        '''
        selection = PySelection(self._editor).getLine()
        # strip tailing whitespace
        return rstrip(selection)

    def _goto_next_line(self):
        '''
        Find the next line. Return if there was a new line to traverse to.
        Note: the selection system appears to wrap around to the beginning if 
        the line is incremented past the end. No user wants to go back to imports 
        once they've completed their step-through, so we protect against that.
        '''

        # skip cursor to next line
        oSelection = PySelection(self._editor)
        current_line = oSelection.getCursorLine()
        last_line = oSelection.getDoc().getNumberOfLines()-1
        offset = oSelection.getLineOffset(current_line + 1)
        if current_line == last_line:
            return False
        self._editor.setSelection(offset, 0)
        return True

    def _should_skip(self, line):
        return len(line) == 0 or RE_COMMENT.match(line)

    def _run_selection_mode(self, selection):
        '''
        User has selected a block of text and hit F1
        '''
        self._reset_line_state()
        if selection[-1]=='\n' :
            text = selection
        else :
            text = selection + '\n'
        self._send_to_console(text)

    def _run_line_mode(self):
        ''' 
        User is running through the code line by line
        '''
        # Save away the current line which we'll send to the console
        current_line = self._get_line()

        # Skip through to the next non-blank line
        self._goto_next_line()
        next_line = self._get_line()
        while self._should_skip(next_line) and self._goto_next_line():
            next_line = self._get_line()

        # Look-ahead for indentation changes
        indentation = len(next_line) - len(next_line.lstrip())
        if self._current_block_indent is None:
            # We're starting a new block which might not be at indent 0
            self._current_block_indent = indentation
            self._prev_line_indent = indentation

        if indentation <= self._current_block_indent and indentation != self._prev_line_indent:
            # We've finished a block - need to send 2 newlines to IPython to tell it to
            # close the block. Don't do this though if we're tracking the same level
            # of indentation.
            self._current_block_indent = indentation
            self._prev_line_indent = indentation
            # Current line gets an extra newline to terminate the block
            current_line = "%s%s" % (current_line, 2 * self._get_newline())

        self._prev_line_indent = indentation

        # add newline
        current_line += self._get_newline()

        # send command to console
        self._send_to_console(current_line)

    def run(self):
        self._show_console()

        selection = self._get_selection()

        if not len(selection) == 0:
            # User has selected a block of text
            self._run_selection_mode(selection)
        else:
            # User has no selection, use line-by-line mode
            self._run_line_mode()
            
    def unhook(self):
        if self._console:
            self._console.getDocument().removeDocumentListener(self._console_listener)
        
def bindInInterface():
        # Cribbed from http://eclipse-pydev.sourcearchive.com/documentation/1.2.5/pyedit__next__problem_8py-source.html
        #bind the action to some internal definition
        action = ExecuteLine(editor)

        #The plugin.xml file defined a command and a binding with the string from COMMAND_ID.
        #by seting the action definition id and the id itself, we will bind this command to the keybinding defined
        #(this is the right way of doing it, as it will enter the abstractions of Eclipse and allow the user to
        #later change that keybinding).
        action.setActionDefinitionId(COMMAND_ID)
        action.setId(COMMAND_ID)
        try:
            #We're starting in a thread, so, it may be closed before
            #we've the change to bind it
            last_execute_line = editor.getAction(COMMAND_ID)
            if last_execute_line :
                last_execute_line.unhook()
            editor.setAction(COMMAND_ID, action)
        except:
            pass


class RunInUi(Runnable):
    '''Helper class that implements a Runnable (just so that we
    can pass it to the Java side). It simply calls some callable.
    '''
    def __init__(self, c):
        self.callable = c

    def run(self):
        self.callable()


def runInUi(c):
    '''
    @param c: the callable that will be run in the UI
    '''
    Display.getDefault().asyncExec(RunInUi(c))

if cmd == 'onCreateActions' or cmd == 'onSave' or cmd == 'onSetDocument':
    # This chain of crazy bind calls allows us to bind this command to a key. Go figure ;)
    runInUi(bindInInterface)