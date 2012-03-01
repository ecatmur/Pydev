/*******************************************************************************
 * Copyright (c) 2005, 2007 IBM Corporation and others.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 
 *******************************************************************************/
package org.python.pydev.dltk.console;

import org.eclipse.jface.text.contentassist.ICompletionProposal;
import org.python.pydev.core.Tuple;
import org.python.pydev.core.callbacks.ICallback;
import org.python.pydev.dltk.console.ui.internal.IStreamMonitor;

/**
 * Interface for the console communication.
 * 
 * This interface is meant to be the way to communicate with the shell.
 */
public interface IScriptConsoleCommunication extends IStreamMonitor {
    
    /**
     * Executes a given command in the interpreter (push a line)
     * 
     * @param command the command to be executed
     * @param onContentsReceived 
     * @return the response from the interpreter.
     * @throws Exception
     */
    void execInterpreter(
            String command, 
            ICallback<Object, InterpreterResponse> onResponseReceived, 
            ICallback<Object, Tuple<String, String>> onContentsReceived);

    /**
     * Creates the completions to be applied in the interpreter.
     * 
     * Equivalent to {@link #getCompletions(String, String, int, false)}
     * 
     * @param text the full line
     * @param actTok the text with what should be completed (e.g.: xxx.bar.foo) 
     * @param offset the offset where the completion was requested in the console document
     * @return a list of proposals that can be applied for the given text.
     * @throws Exception
     */
    public ICompletionProposal[] getCompletions(String text, String actTok, int offset) throws Exception;
    
    /**
     * Creates the completions to be applied in the interpreter.
     * 
     * @param text the full line
     * @param actTok the text with what should be completed (e.g.: xxx.bar.foo) 
     * @param offset the offset where the completion was requested in the console document
     * @param ipythonOnly flag which indicates if the completions returned should be restricted to those returned from Ipython (if available
     * @return a list of proposals that can be applied for the given text.
     * @throws Exception
     */
    public ICompletionProposal[] getCompletions(String text, String actTok, int offset, boolean ipythonOnly) throws Exception;

    
    /**
     * Gets the description to be shown on hover to the user
     * 
     * @param text the text representing the completion to be applied
     * @return the description to be shown to the user
     * @throws Exception
     */
    public String getDescription(String text) throws Exception;

    /**
     * Stops the communication with the server. Should ask the server to terminate at this point.
     * @throws Exception
     */
    void close() throws Exception;

    /**
     * Send the signal to the underlying process
     * @param signal
     * @throws Exception
     */
    void interrupt(int signal) throws Exception;
}
