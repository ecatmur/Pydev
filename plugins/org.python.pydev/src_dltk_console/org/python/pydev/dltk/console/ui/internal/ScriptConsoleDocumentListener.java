/**
 * Copyright (c) 2005-2011 by Appcelerator, Inc. All Rights Reserved.
 * Licensed under the terms of the Eclipse Public License (EPL).
 * Please see the license.txt included with this distribution for details.
 * Any modifications to this file must keep this entire header intact.
 */
package org.python.pydev.dltk.console.ui.internal;

import java.lang.ref.WeakReference;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Formatter;
import java.util.Iterator;
import java.util.List;

import org.eclipse.core.runtime.Assert;
import org.eclipse.core.runtime.IProgressMonitor;
import org.eclipse.core.runtime.IStatus;
import org.eclipse.core.runtime.Status;
import org.eclipse.core.runtime.jobs.ISchedulingRule;
import org.eclipse.core.runtime.jobs.Job;
import org.eclipse.debug.ui.console.IConsoleLineTracker;
import org.eclipse.jface.text.BadLocationException;
import org.eclipse.jface.text.Document;
import org.eclipse.jface.text.DocumentEvent;
import org.eclipse.jface.text.IDocument;
import org.eclipse.jface.text.IDocumentListener;
import org.eclipse.jface.text.IDocumentPartitioner;
import org.eclipse.jface.text.Region;
import org.eclipse.jface.text.TextUtilities;
import org.eclipse.jface.text.contentassist.ICompletionProposal;
import org.eclipse.swt.widgets.Display;
import org.python.pydev.core.Tuple;
import org.python.pydev.core.callbacks.ICallback;
import org.python.pydev.core.docutils.PySelection;
import org.python.pydev.core.docutils.StringUtils;
import org.python.pydev.core.docutils.PySelection.ActivationTokenAndQual;
import org.python.pydev.core.log.Log;
import org.python.pydev.core.uiutils.RunInUiThread;
import org.python.pydev.dltk.console.InterpreterResponse;
import org.python.pydev.dltk.console.ScriptConsoleHistory;
import org.python.pydev.dltk.console.ScriptConsolePrompt;
import org.python.pydev.dltk.console.ui.IConsoleStyleProvider;
import org.python.pydev.dltk.console.ui.ScriptConsolePartitioner;
import org.python.pydev.dltk.console.ui.ScriptStyleRange;
import org.python.pydev.editor.autoedit.DocCmd;
import org.python.pydev.editor.autoedit.PyAutoIndentStrategy;
import org.python.pydev.editor.codecompletion.PyLinkedModeCompletionProposal;

import sun.org.mozilla.javascript.internal.IdScriptableObject;

/**
 * This class will listen to the document and will:
 * 
 * - pass the commands to the handler
 * - add the results from the asynchronous stream
 * - show the prompt
 * - set the color of the console regions
 */
public class ScriptConsoleDocumentListener implements IDocumentListener, IStreamListener {

    private ICommandHandler handler;

    private ScriptConsolePrompt prompt;

    private ScriptConsoleHistory history;

    private int offset;
    
    private volatile boolean promptReady;

    /**
     * Document to which this listener is attached.
     */
    private IDocument doc;
    
    private int disconnectionLevel = 0;  
    
    /**
     * The time for the last change in the document that was listened in this console.
     */
    private long lastChangeMillis;

    /**
     * The commands that should be initially set in the console
     */
    private String initialCommands;
    
    /**
     * @return the last time the document that this console was listening to was changed.
     */
    public long getLastChangeMillis() {
        return lastChangeMillis;
    }

    /**
     * Constructor
     * 
     * @param viewer this is the viewer to which this listener is attached. It's the main viewer. Other viewers
     * may be added later through addViewer() for sharing the same listener and being properly updated.
     * 
     * @param handler this is the object that'll handle the commands
     * @param prompt shows the prompt to the user
     * @param history keeps track of the commands added by the user.
     * @param initialCommands the commands that should be initially added 
     */
    public ScriptConsoleDocumentListener(IScriptConsoleViewer2ForDocumentListener viewer, 
            ICommandHandler handler, ScriptConsolePrompt prompt,
            ScriptConsoleHistory history, List<IConsoleLineTracker> consoleLineTrackers, String initialCommands) {
        this.prompt = prompt;
        
        this.handler = handler;
        
        this.history = history;

        this.viewer = viewer;

        this.offset = 0;

        this.doc = null;
        
        this.consoleLineTrackers = consoleLineTrackers;
        
        this.initialCommands = initialCommands;
        
        this.lastChangeMillis = System.currentTimeMillis();
    }
    
    /**
     * Viewer for the document contained in this listener.
     */
    private IScriptConsoleViewer2ForDocumentListener viewer;
    
    /**
     * Additional viewers for the same document.
     */
    private List<WeakReference<IScriptConsoleViewer2ForDocumentListener>> otherViewers = new ArrayList<WeakReference<IScriptConsoleViewer2ForDocumentListener>>();

    /**
     * Empty document (should not be written to).
     */
    IDocument EMPTY_DOCUMENT = new Document();


    /**
     * Strategy used for indenting / tabs
     */
    private PyAutoIndentStrategy strategy = new PyAutoIndentStrategy();

    /**
     * Console line trackers (for hyperlinking)
     */
    private List<IConsoleLineTracker> consoleLineTrackers;
    
    public PyAutoIndentStrategy getIndentStrategy(){
        return strategy;
    }


    /**
     * Stops listening changes in one document and starts listening another one.
     * 
     * @param oldDoc may be null (if not null, this class will stop listening changes in it).
     * @param newDoc the document that should be listened from now on.
     */
    protected synchronized void reconnect(IDocument oldDoc, IDocument newDoc) {
        Assert.isTrue(disconnectionLevel == 0);
        
        if(oldDoc != null){
            oldDoc.removeDocumentListener(this);
        }
        
        newDoc.addDocumentListener(this);
        this.doc = newDoc;
        
    }
    
    /**
     * Stop listening to changes (so that we're able to change the document in this class without having
     * any loops back into the function that will change it)
     */
    protected synchronized void startDisconnected() {
        if(disconnectionLevel == 0){
            doc.removeDocumentListener(this);
        }
        disconnectionLevel += 1;
    }
    
    /**
     * Start listening to changes again.
     */
    protected synchronized void stopDisconnected() {
        disconnectionLevel -= 1;
        
        if(disconnectionLevel == 0){
            doc.addDocumentListener(this);
        }
    }


    /**
     * Clear the document and show the initial prompt.
     * @param addInitialCommands indicates if the initial commands should be appended to the document. 
     */
    public void clear(boolean addInitialCommands) {
        startDisconnected();
        try{
            doc.set(""); //$NON-NLS-1$
            appendInvitation(true);
        }finally{
            stopDisconnected();
        }
        
        if(addInitialCommands){
            try {
                doc.replace(doc.getLength(), 0, this.initialCommands);
            } catch (BadLocationException e) {
                Log.log(e);
            }
        }
    }

    /**
     * Adds some other viewer for the same document.
     * 
     * @param scriptConsoleViewer this is the viewer that should be added as a second viewer for the same
     * document.
     */
    public void addViewer(IScriptConsoleViewer2ForDocumentListener scriptConsoleViewer) {
        this.otherViewers.add(new WeakReference<IScriptConsoleViewer2ForDocumentListener>(scriptConsoleViewer));
    }

    /**
     * Set the document that this class should listen.
     * 
     * @param doc the document that should be used in the console.
     */
    public void setDocument(IDocument doc) {
        reconnect(this.doc, doc);
    }

    /**
     * Ignore 
     */
    public void documentAboutToBeChanged(DocumentEvent event) {
        
    }

    /**
     * Process the result that came from pushing some text to the interpreter.
     * 
     * @param result the response from the interpreter after sending some command for it to process.
     */
    protected void processResult(final InterpreterResponse result) {
        if (result != null) {
            history.commit();
            try{
                offset = getLastLineLength();
            }catch(BadLocationException e){
                Log.log(e);
            }
        }
        appendInvitation(false);
    }

    /**
     * Adds some text that came as an output to stdout or stderr to the console.
     * 
     * @param out the text that should be added
     * @param stdout true if it came from stdout and false if it came from stderr
     */
    
    private void addToConsoleView(String out, boolean stdout){
        if(out.length() == 0){
            return; //nothing to add!
        }

        int start = doc.getLength();
        
        IConsoleStyleProvider styleProvider = viewer.getStyleProvider();
        Tuple<List<ScriptStyleRange>, String> style = null;
        if (styleProvider != null) {
            if(stdout){
                style = styleProvider.createInterpreterOutputStyle(out, start);
            }else{ //stderr
                style = styleProvider.createInterpreterErrorStyle(out, start);
            }
            if (style != null) {
                for(ScriptStyleRange s:style.o1){
                    addToPartitioner(s);
                }
            }
        }
        if(style != null){
            appendText(style.o2);
        }
        
        PySelection ps = new PySelection(doc, start);
        int cursorLine = ps.getCursorLine();
        int numberOfLines = doc.getNumberOfLines();
        
        //right after appending the text, let's notify line trackers
        for(int i=cursorLine;i<numberOfLines;i++){
            try{
                int offset = ps.getLineOffset(i);
                int endOffset = ps.getEndLineOffset(i);
                
                Region region = new Region(offset, endOffset-offset);
                
                for(IConsoleLineTracker lineTracker:this.consoleLineTrackers){
                    lineTracker.lineAppended(region);
                }
            }catch(Exception e){
                Log.log(e);
            }
        }
    }

    
    /**
     * Adds a given style range to the partitioner.
     * 
     * Note that the style must be added before the actual text is added! (because as 
     * soon as it's added, the style is asked for).
     *  
     * @param style the style to be added.
     */
    private void addToPartitioner(ScriptStyleRange style) {
        IDocumentPartitioner partitioner = this.doc.getDocumentPartitioner();
        if (partitioner instanceof ScriptConsolePartitioner) {
            ScriptConsolePartitioner scriptConsolePartitioner = (ScriptConsolePartitioner) partitioner;
            scriptConsolePartitioner.addRange(style);
        }
    }

    /**
     * Should be called right after adding some text to the console (it'll actually go on,
     * remove the text just added and add it line-by-line in the document so that it can be 
     * correctly treated in the console).
     * 
     * @param offset the offset where the addition took place
     * @param text the text that should be added
     */
    protected void proccessAddition(int offset, String text){
        //we have to do some gymnastics here to add line-by-line the contents that the user entered.
        //(mostly because it may have been a copy/paste with multi-lines)
        
        String indentString = "";
        boolean addedNewLine = false;
        boolean addedParen = false;
        boolean addedCloseParen = false;
        int addedLen = text.length();
        if(addedLen == 1){
            if(text.equals("\r") || text.equals("\n")){
                addedNewLine = true;
                
            }else if(text.equals("(")){
                addedParen = true;
                
            } else if(text.equals(")")){
                addedCloseParen = true;
            }
            
        }else if(addedLen == 2){
            if(text.equals("\r\n")){
                addedNewLine = true;
            }
        }
        
        
        String delim = getDelimeter();
        
        int newDeltaCaretPosition = doc.getLength() - (offset + text.length());

        //1st, remove the text the user just entered (and enter it line-by-line later)
        try{
            text = doc.get(offset, doc.getLength() - offset);
        }catch(BadLocationException e){
            text = "";
            Log.log(e);
        }

        try{
            doc.replace(offset, text.length(), ""); //$NON-NLS-1$
        }catch(BadLocationException e){
            Log.log(e);
        }

        text = text.replaceAll("\r\n|\n|\r", delim); //$NON-NLS-1$

        //now, add it line-by-line (it won't even get into the loop if there's no 
        //new line in the text added).
        int start = 0;
        int index = -1;
        List<String> commands = new ArrayList<String>();
        while ((index = text.indexOf(delim, start)) != -1) {
            String cmd = text.substring(start, index);
            cmd = convertTabs(cmd);
            commands.add(cmd);
            start = index + delim.length();
        }
        

        final String[] finalIndentString = new String[]{indentString};
        
        if(commands.size() > 0){
            //Note that we'll disconnect from the document here and reconnect when the last line is executed.
            startDisconnected();
            String cmd = commands.get(0);
            execCommand(addedNewLine, delim, finalIndentString, cmd, commands, 0,
                    text, addedParen, start, addedCloseParen, newDeltaCaretPosition);
        }else{
            onAfterAllLinesHandled(text, addedParen, start, offset, addedCloseParen, finalIndentString[0], newDeltaCaretPosition);            
        }
        
    }

    /**
     * Here is where we run things not using the UI thread. It's a recursive function. In summary, it'll
     * run each line in the commands received in a new thread, and as each finishes, it calls itself again
     * for the next command. The last command will reconnect to the document.
     * 
     * Exceptions had to be locally handled, because they're not well tolerated under this scenario
     * (if on of the callbacks fail, the others won't be executed and we'd get into a situation
     * where the shell becomes unusable).
     */
    private void execCommand(
            final boolean addedNewLine, 
            final String delim, 
            final String[] finalIndentString, 
            final String cmd, 
            final List<String> commands, 
            final int currentCommand,
            final String text, 
            final boolean addedParen, 
            final int start, 
            final boolean addedCloseParen, 
            final int newDeltaCaretPosition
            ){
        applyStyleToUserAddedText(cmd, doc.getLength());
        
        //the cmd could be something as '\n'
        appendText(cmd);

        //and the command line the actual contents to be executed at this time
        final String commandLine = getCommandLine();
        history.update(commandLine);
        
        
        // handle the command line:
        // When the user presses a return and goes to a new line,  the contents of the current line are sent to 
        // the interpreter (and its results properly handled).

        appendText(getDelimeter());
        final boolean finalAddedNewLine = addedNewLine;
        final String finalDelim = delim;
        
        final ICallback<Object, InterpreterResponse> onResponseReceived = new ICallback<Object, InterpreterResponse>(){
            
            public Object call(final InterpreterResponse arg){
                //When we receive the response, we must handle it in the UI thread.
                Runnable runnable = new Runnable(){
                    
                    public void run(){
                        try{
                            processResult(arg);
                            if(finalAddedNewLine){
                                IDocument historyDoc = history.getAsDoc();
                                int currHistoryLen = historyDoc.getLength();
                                if(currHistoryLen > 0){
                                    DocCmd docCmd = new DocCmd(currHistoryLen-1, 0, finalDelim);
                                    strategy.customizeNewLine(historyDoc, docCmd);
                                    finalIndentString[0] = docCmd.text.replaceAll("\\r\\n|\\n|\\r", ""); //remove any new line added!
                                    if(currHistoryLen != historyDoc.getLength()){
                                        Log.log("Error: the document passed to the customizeNewLine should not be changed!");
                                    }
                                }
                            }
                        }catch(Throwable e){
                            //Yeap, it can never fail!
                            Log.log(e);
                        }
                        if(currentCommand + 1 < commands.size()){
                            execCommand(
                                    finalAddedNewLine, 
                                    finalDelim, 
                                    finalIndentString, 
                                    commands.get(currentCommand+1), 
                                    commands, 
                                    currentCommand+1,
                                    text, 
                                    addedParen, 
                                    start, 
                                    addedCloseParen, 
                                    newDeltaCaretPosition
                                );
                        }else{
                            //last one
                            try{
                                onAfterAllLinesHandled(
                                        text, addedParen, start, offset, addedCloseParen, finalIndentString[0], newDeltaCaretPosition);
                            }finally{
                                //We must disconnect
                                stopDisconnected(); //reconnect with the document
                            }
                        }
                    }
                };
                RunInUiThread.async(runnable);
                return null;
            }
        };
        
        final ICallback<Object, Tuple<String, String>> onContentsReceived = new ICallback<Object, Tuple<String, String>>(){

            public Object call(final Tuple<String, String> result) {
                Runnable runnable = new Runnable() {
                    
                    public void run() {
                        if (result != null) {
                            //TODO: cleanup
                            //addToConsoleView(result.o1, true);
                            //addToConsoleView(result.o2, false);
                            revealEndOfDocument();
                        }
                    }
                };
                RunInUiThread.async(runnable);
                return null;
            }
            
        };
        //Handle the command in a thread that doesn't block the U/I.
        // Use the eclipse threadpool so we don't go trigger-happy with OS threads
        Job j = new Job("PyDev Console Hander") {
            protected IStatus run(IProgressMonitor monitor) {
                promptReady = false;
                handler.handleCommand(commandLine, onResponseReceived, onContentsReceived);        
                return Status.OK_STATUS;
            };
        };
        j.setSystem(true);
        j.schedule();
    }
   
    
    private static class TabCompletionSingletonRule implements ISchedulingRule {
        public boolean contains(ISchedulingRule rule) {
            return rule == this;
        }

        public boolean isConflicting(ISchedulingRule rule) {
            return rule instanceof TabCompletionSingletonRule;
        }
    }
    
    /**
     * Attempts to query the console backend (ipython) for completions
     * and update the console's cursor as appropriate.
     */
    public void handleConsoleTabCompletions() {
        final String commandLine = getCommandLine();
        final int commandLineOffset = viewer.getCommandLineOffset();
        final int caretOffset = viewer.getCaretOffset();
        
        // Don't block the UI when talking to the console
        Job j = new Job("Async Fetch completions") {

            @Override
            protected IStatus run(IProgressMonitor monitor) {
                final StringBuilder sb = new StringBuilder("\n");
                ICompletionProposal[] completions = handler.getCompletions(commandLine, caretOffset - commandLineOffset);
                if (completions.length == 0)
                    return Status.OK_STATUS;
                
                // Evaluate all the completions
                final List<String> compList = new ArrayList<String>();
                for (ICompletionProposal completion : completions) {
                    Document out = new Document(commandLine);
                    completion.apply(out);
                    compList.add(out.get());
                }

                // Discover the longest possible completion so we can zip up to it
                String longestCommonPrefix = null;
                int length = 0;
                for (String completion : compList) {
                    // Handle magic % character -> IPython does the right thing
                    if (completion.charAt(0) == '%')
                        completion = completion.substring(1);
                    // Calculate the longest common prefix so we can auto-complete at least up to there.
                    if (longestCommonPrefix == null) {
                        longestCommonPrefix = completion;
                    } else {
                        for (int i = 0 ; i < longestCommonPrefix.length() && i < completion.length(); i++) {
                            if (longestCommonPrefix.charAt(i) != completion.charAt(i)) {
                                longestCommonPrefix = longestCommonPrefix.substring(0, i);
                                break;
                            }
                        }
                        // Handle mismatched lengths: dir and dirs
                        if (longestCommonPrefix.length() > completion.length())
                            longestCommonPrefix = completion;
                    }

                    // Calculate the maximum length of the completions for string formatting
                    length = Math.max(length, completion.length());
                }
                if (longestCommonPrefix == null)
                    longestCommonPrefix = commandLine;
                
                final String fLongestCommonPrefix = longestCommonPrefix;
                final int maxLength = length;

                // Find common substring
                Runnable r = new Runnable() {
                    public void run() {
                        String currentCommand = getCommandLine();

                        // disconnect the console so we can write content into it
                        startDisconnected();

                        // Get the viewer width + format the auto-completion output appropriately
                        int consoleWidth = viewer.getConsoleWidthInCharacters();
                        int formatLength = maxLength + 4;
                        int completionsPerLine = consoleWidth / formatLength;
                        if (completionsPerLine <= 0)
                            completionsPerLine = 1;

                        String formatString = "%-" + formatLength + "s";

                        int i = 0;
                        for (String completion : compList) {
                            sb.append(String.format(formatString, completion));
                            if (++i % completionsPerLine == 0) {
                                sb.append("\n");
                            }
                        }
                        sb.append("\n");

                        // Add our completions to the console
                        addToConsoleView(sb.toString(), true);

                        // Re-add >>> 
                        appendInvitation(false);
                        stopDisconnected();

                        // Auto-complete the command up to the longest common prefix (if it hasn't changed since we were last here)
                        if (!currentCommand.equals(commandLine) || fLongestCommonPrefix.isEmpty())
                            addToConsoleView(currentCommand, true);
                        else
                            addToConsoleView(fLongestCommonPrefix, true);
                    }
                };
                RunInUiThread.async(r);

                return Status.OK_STATUS;
            }
        };
        j.setPriority(Job.INTERACTIVE);
        j.setRule(new TabCompletionSingletonRule());        
        j.setSystem(true);
        j.schedule();
    }


    /**
     * This method should be called after all the lines received were processed.
     */
    private void onAfterAllLinesHandled(
        final String finalText,
        final boolean finalAddedParen,
        final int finalStart,
        final int finalOffset,
        final boolean finalAddedCloseParen,
        final String finalIndentString,
        final int finalNewDeltaCaretPosition
        ){
        boolean shiftsCaret = true;
        String newText = finalText.substring(finalStart, finalText.length());
        if(finalAddedParen){
            String cmdLine = getCommandLine();
            Document parenDoc = new Document(cmdLine+newText);
            int currentOffset = cmdLine.length()+1;
            DocCmd docCmd = new DocCmd(currentOffset, 0, "(");
            docCmd.shiftsCaret = true;
            try{
                PyAutoIndentStrategy.customizeParenthesis(parenDoc, docCmd, true, strategy.getIndentPrefs());
            }catch(BadLocationException e){
                Log.log(e);
            }
            newText = docCmd.text+newText.substring(1);
            if(!docCmd.shiftsCaret){
                shiftsCaret = false;
                setCaretOffset(finalOffset + (docCmd.caretOffset-currentOffset));
            }
        }else if (finalAddedCloseParen){
            String cmdLine = getCommandLine();
            String existingDoc = cmdLine+finalText.substring(1);
            int cmdLineOffset = cmdLine.length();
            if(existingDoc.length() > cmdLineOffset){
                Document parenDoc = new Document(existingDoc);
                DocCmd docCmd = new DocCmd(cmdLineOffset, 0, ")");
                docCmd.shiftsCaret = true;
                boolean canSkipOpenParenthesis;
                try{
                    canSkipOpenParenthesis = strategy.canSkipCloseParenthesis(parenDoc, docCmd);
                }catch(BadLocationException e){
                    canSkipOpenParenthesis = false;
                    Log.log(e);
                }
                if(canSkipOpenParenthesis){
                    shiftsCaret = false;
                    setCaretOffset(finalOffset + 1);
                    newText = newText.substring(1);
                }
            }
        }

        //and now add the last line (without actually handling it).
        String cmd = finalIndentString+newText;
        cmd = convertTabs(cmd);
        applyStyleToUserAddedText(cmd, doc.getLength());
        appendText(cmd);
        if(shiftsCaret){
            setCaretOffset(doc.getLength()-finalNewDeltaCaretPosition);
        }


        history.update(getCommandLine());
    }

    private String convertTabs(String cmd) {
        DocCmd newStr = new DocCmd(0, 0, cmd);
        strategy.getIndentPrefs().convertToStd(EMPTY_DOCUMENT, newStr);
        cmd = newStr.text;
        return cmd;
    }

    /**
     * Applies the style in the text for the contents that've been just added. 
     * 
     * @param cmd
     * @param offset2
     */
    private void applyStyleToUserAddedText(String cmd, int offset2) {
        IConsoleStyleProvider styleProvider = viewer.getStyleProvider();
        if (styleProvider != null) {
            ScriptStyleRange style = styleProvider.createUserInputStyle(cmd, offset2);
            if (style != null) {
                addToPartitioner(style);
            }
        }
    }

    /**
     * Whenever the document changes, we stop listening to change the document from
     * within this listener (passing commands to the handler if needed, getting results, etc).
     */
    public void documentChanged(DocumentEvent event) {
        lastChangeMillis = System.currentTimeMillis();
        startDisconnected();
        try{
            int eventOffset = event.getOffset();
            String eventText = event.getText();
            proccessAddition(eventOffset, eventText);
        }finally{
            stopDisconnected();
        }
    }

    /**
     * Appends some text at the end of the document.
     * 
     * @param text the text to be added.
     */
    protected void appendText(String text) {
        int initialOffset = doc.getLength();
        try{
            doc.replace(initialOffset, 0, text);
        }catch(BadLocationException e){

        }
    }
    private String formattedPrompt() {
        int start = doc.getLength();
        String promptStr = prompt.toString();
        IConsoleStyleProvider styleProvider = viewer.getStyleProvider();
        if (styleProvider != null) {
            ScriptStyleRange style = styleProvider.createPromptStyle(promptStr, start);
            if (style != null) {
                addToPartitioner(style);
            }
        }
        return promptStr;
    }

    /**
     * Shows the prompt for the user (e.g.: >>>)
     */
    protected void appendInvitation(boolean async){
        String promptStr = formattedPrompt();
        appendText(promptStr); //caret already updated
        setCaretOffset(doc.getLength(), async);
        revealEndOfDocument();
        
        promptReady = true;
    }
    
    private class PromptContext {
        public boolean removedPrompt;
        // offset from the end of the document.
        public int     cursorOffset;
        public String   userInput;
        
        public PromptContext(boolean removedPrompt, int cursorOffset, String userInput) {
            this.removedPrompt = removedPrompt;
            this.cursorOffset  = cursorOffset;
            this.userInput     = userInput;
        }
    }
    
    protected PromptContext removeUserInput() {
        if(!promptReady)
            return new PromptContext(false, -1, "");

        PromptContext pc = new PromptContext(true, -1, "");
        try {
            int lastLine = doc.getNumberOfLines()-1;
            int lastLineLength = doc.getLineLength(lastLine);
            int end = doc.getLength();
            int start = end - lastLineLength;
            pc.userInput = doc.get(start, lastLineLength);
            pc.cursorOffset = end - viewer.getCaretOffset();
            doc.replace(start, lastLineLength, "");
            
            pc.userInput = pc.userInput.replace(formattedPrompt(), "");
            
        } catch (BadLocationException e) {
            e.printStackTrace();
        }
        return pc;
    }

    /**
     * Shows the end of the document for the main viewer and all the related viewer for the same document. 
     */
    private void revealEndOfDocument() {
        viewer.revealEndOfDocument();
        for(Iterator<WeakReference<IScriptConsoleViewer2ForDocumentListener>> it=otherViewers.iterator();it.hasNext();){
            WeakReference<IScriptConsoleViewer2ForDocumentListener> ref = it.next();
            IScriptConsoleViewer2ForDocumentListener v = ref.get();
            if(v == null){
                it.remove();
            }else{
                v.revealEndOfDocument();
            }
        }
    }

    private void setCaretOffset(int offset) {
        setCaretOffset(offset, false);
    }
    
    /**
     * Sets the caret offset to the passed offset for the main viewer and all the related viewer for the same document. 
     * @param offset the offset to which the caret should be moved
     */
    private void setCaretOffset(int offset, boolean async) {
        viewer.setCaretOffset(offset, async);
        for(Iterator<WeakReference<IScriptConsoleViewer2ForDocumentListener>> it=otherViewers.iterator();it.hasNext();){
            WeakReference<IScriptConsoleViewer2ForDocumentListener> ref = it.next();
            IScriptConsoleViewer2ForDocumentListener v = ref.get();
            if(v == null){
                it.remove();
            }else{
                v.setCaretOffset(offset, async);
            }
        }
    }


    /**
     * @return the delimiter to be used to add new lines to the console.
     */
    public String getDelimeter() {
        return TextUtilities.getDefaultLineDelimiter(doc);
    }

    /**
     * @return the length of the last line
     */
    public int getLastLineLength() throws BadLocationException {
        int lastLine = doc.getNumberOfLines() - 1;
        return doc.getLineLength(lastLine);
    }
    
    /**
     * @return the offset where the last line starts
     * @throws BadLocationException
     */
    public int getLastLineOffset() throws BadLocationException {
        int lastLine = doc.getNumberOfLines() - 1;
        return doc.getLineOffset(lastLine);
    }

    public int getLastLineReadOnlySize() {
        return offset + prompt.toString().length();
    }

    public int getCommandLineOffset() throws BadLocationException {
        int lastLine = doc.getNumberOfLines() - 1;
        return doc.getLineOffset(lastLine) + getLastLineReadOnlySize();
    }

    /**
     * @return the length of the current command line (all the currently
     * editable area)
     * 
     * @throws BadLocationException
     */
    public int getCommandLineLength() throws BadLocationException {
        int lastLine = doc.getNumberOfLines() - 1;
        return doc.getLineLength(lastLine) - getLastLineReadOnlySize();
    }
    
    /**
     * @return the command line that the user entered.
     * @throws BadLocationException
     */
    public String getCommandLine() {
        int commandLineOffset;
        int commandLineLength;
        try{
            commandLineOffset = getCommandLineOffset();
            commandLineLength = getCommandLineLength();
        }catch(BadLocationException e1){
            Log.log(e1);
            return "";
        }
        if(commandLineLength < 0){
            return "";
        }

        try {
            return doc.get(commandLineOffset, commandLineLength);
        } catch (BadLocationException e) {
            Log.log(StringUtils.format(
            "Error: bad location: offset:%s text:%s", commandLineOffset, commandLineLength));
            return "";
        }
    }

    /**
     * Sets the current command line to be executed (but without executing it).
     * Used by the up/down arrow to set a previous/next command.
     * 
     * @param command this is the command that should be in the command line.
     * 
     * @throws BadLocationException
     */
    public void setCommandLine(String command) throws BadLocationException {
        doc.replace(getCommandLineOffset(), getCommandLineLength(), command);
    }

    /**
     * Applies the new text from the input stream to the console. This must run
     * in the UI thread as it's updating a widget.
     */
    public void onStream(final StreamMessage msg) {
        Runnable r = new Runnable() {
            public void run() {
                startDisconnected();
                PromptContext pc = removeUserInput();
                addToConsoleView(msg.message, msg.type == StreamType.STDOUT);
                
                if(pc.removedPrompt) {
                    appendInvitation(false);
                }
                
                stopDisconnected();
                
                if(pc.removedPrompt) {
                    appendText(pc.userInput);
                    viewer.setCaretOffset(doc.getLength() - pc.cursorOffset, false);
                }
                
                revealEndOfDocument();
            }
        };
        RunInUiThread.async(r);
    }


}