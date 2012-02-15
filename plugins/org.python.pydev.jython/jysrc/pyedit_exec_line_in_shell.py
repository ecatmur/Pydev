if False:
    from org.python.pydev.editor import PyEdit #@UnresolvedImport
    cmd = 'command string'
    editor = PyEdit

#--------------------------------------------------------------- REQUIRED LOCALS
#interface: String indicating which command will be executed #As this script will be watching the PyEdit (that is the actual editor in Pydev), and this script
#will be listening to it, this string can indicate any of the methods of org.python.pydev.editor.IPyEditListener
assert cmd is not None

#interface: PyEdit object: this is the actual editor that we will act upon assert editor is not None

#---- Uncomment the line below to see the outputs received

import sys
print 'Command: ' + cmd
print 'File: ' + editor.getEditorFile().getName()
print 'sys.version:' + sys.version

from org.eclipse.jface.action import Action #@UnresolvedImport
from org.eclipse.jface.dialogs import MessageDialog #@UnresolvedImport
from org.python.pydev.core.docutils import PySelection #@UnresolvedImport
from string import rstrip

from org.python.pydev.debug.newconsole import PydevConsoleConstants
from org.python.pydev.debug.newconsole import PydevConsoleFactory #@UnresolvedImport
from org.python.pydev.debug.newconsole import PydevConsole
from org.python.pydev.editor.actions import PyAction #@UnresolvedImport

from org.eclipse.ui import PlatformUI #@UnresolvedImport
from org.eclipse.ui.console import IConsoleConstants #@UnresolvedImport
from java.lang import Runnable #@UnresolvedImport
from org.eclipse.swt.widgets import Display #@UnresolvedImport

#from com.python.pydev.interactiveconsole import EvaluateActionSetter

# This is the command ID as specified in plugin.xml
COMMAND_ID = "com.mi.ahl.eclipse.python.execLineInConsole"

import re
RE_COMMENT = re.compile('^\s*#')

# Code to execute a line
class ExecuteLine(Action):
    def __init__(self, editor=None):
        Action.__init__(self)
        self.editor = editor
        self.console = None
        self.current_block_indent = None
        self.prev_line_indent = None

    def getConsoleParts(self, page, restore):
        # logic taken from EvaluationActionSetter.java
        consoleParts = []
        viewReferences = page.getViewReferences()
        for ref in viewReferences:
            if ref.getId() == IConsoleConstants.ID_CONSOLE_VIEW:
                part = ref.getView(restore)
                if part is not None:
                    consoleParts.append(part)
                    if restore:
                        return consoleParts
        return consoleParts;

    def showConsole(self):
        # logic derived from EvaluationActionSetter.java
        window = PlatformUI.getWorkbench().getActiveWorkbenchWindow()
        if window is not None:
            page = window.getActivePage()
            if page is not None:
                consoleParts = self.getConsoleParts(page, False)
                if len(consoleParts) == 0:
                    consoleParts = self.getConsoleParts(page, True)
#                if len(consoleParts) > 1:
#                    MessageDialog.openInformation(editor.getSite().getShell(), "Execute line", "Too many consoles open");

                for part in consoleParts:
                    if part.getConsole().getType() == PydevConsoleConstants.CONSOLE_TYPE:
                        self.console = part.getConsole()
#                        part.display(self.console)
        return

    def create_console(self):
        self.console = PydevConsoleFactory().createConsole()

    def get_newline(self):
        return PyAction.getDelimiter(self.editor.getDocument())

    def get_selection(self):
        return PySelection(self.editor).getSelectedText()

    def send_to_console(self, text):
        if len(rstrip(text)):
            document = self.console.getDocument()
            document.replace(document.getLength(), 0, text)

    def reset_line_state(self):
        self.current_block_indent = None
        self.prev_line_indent = None

    def get_next_line(self):
        selection = PySelection(self.editor).getLine()
        # strip tailing whitespace
        return rstrip(selection)

    def goto_next_line(self):
        # skip cursor to next line
        oSelection = PySelection(self.editor)
        offset = oSelection.getLineOffset(oSelection.getCursorLine() + 1)
        self.editor.setSelection(offset, 0)

    def should_skip(self, line):
        return len(line) == 0 or RE_COMMENT.match(line)

    def run_selection_mode(self, selection):
        """ User has selected a block of text and hit F1
        """
        self.reset_line_state()
        self.send_to_console(selection)

    def run_line_mode(self):
        """ User is running through the code line by line
        """
        # Save away the current line which we'll send to the console
        current_line = self.get_next_line()

        # Skip through to the next non-blank line
        self.goto_next_line()
        next_line = self.get_next_line()
        while self.should_skip(next_line):
            self.goto_next_line()
            next_line = self.get_next_line()

        # Look-ahead for indentation changes
        indentation = len(next_line) - len(next_line.lstrip())
        if self.current_block_indent is None:
            # We're starting a new block which might not be at indent 0
            self.current_block_indent = indentation
            self.prev_line_indent = indentation

        if indentation <= self.current_block_indent and indentation != self.prev_line_indent:
            # We've finished a block - need to send 2 newlines to IPython to tell it to
            # close the block. Don't do this though if we're tracking the same level
            # of indentation.
            self.current_block_indent = indentation
            self.prev_line_indent = indentation
            # Current line gets an extra newline to terminate the block
            current_line = "%s%s" % (current_line, 2 * self.get_newline())

        self.prev_line_indent = indentation

        # add newline
        current_line += self.get_newline()

        # send command to console
        self.send_to_console(current_line)

    def run(self):
#        # create console on first use
#        if self.console is None or self.console.getViewer() is None:
#            self.create_console()

#        # if console has been closed then recreate
#        if self.console.getViewer().getDocument() is None:
#            self.create_console()

        self.showConsole()

        selection = self.get_selection()

        if not len(selection) == 0:
            # User has selected a block of text
            self.run_selection_mode(selection)
        else:
            # User has no selection, use line-by-line mode
            self.run_line_mode()

def bindInInterface():
        # Cribbed from http://eclipse-pydev.sourcearchive.com/documentation/1.2.5/pyedit__next__problem_8py-source.html
        #bind the action to some internal definition
        action = ExecuteLine(editor)

        #ok, the plugin.xml file defined a command and a binding with the string from COMMAND_ID.
        #by seting the action definition id and the id itself, we will bind this command to the keybinding defined
        #(this is the right way of doing it, as it will enter the abstractions of Eclipse and allow the user to
        #later change that keybinding).
        action.setActionDefinitionId(COMMAND_ID)
        action.setId(COMMAND_ID)
        try:
            #may happen because we're starting it in a thread, so, it may be closed before
            #we've the change to bind it
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



