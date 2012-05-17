/**
 * Copyright (c) 2005-2011 by Appcelerator, Inc. All Rights Reserved.
 * Licensed under the terms of the Eclipse Public License (EPL).
 * Please see the license.txt included with this distribution for details.
 * Any modifications to this file must keep this entire header intact.
 */
/*
 * Created on Aug 16, 2004
 *
 * @author Fabio Zadrozny
 */
package org.python.pydev.editor.codecompletion.shell;

import java.io.File;
import java.io.IOException;
import java.util.Arrays;

import org.eclipse.core.runtime.CoreException;
import org.python.pydev.core.IInterpreterInfo;
import org.python.pydev.core.IInterpreterManager;
import org.python.pydev.core.REF;
import org.python.pydev.core.log.Log;
import org.python.pydev.plugin.PydevPlugin;
import org.python.pydev.runners.SimplePythonRunner;
import org.python.pydev.runners.SimpleRunner;

/**
 * @author Fabio Zadrozny
 */
public class PythonShell extends AbstractShell{

    
    /**
     * Initialize with the default python server file.
     * 
     * @throws IOException
     * @throws CoreException
     */
    public PythonShell() throws IOException, CoreException {
        super(PydevPlugin.getScriptWithinPySrc("pycompletionserver.py"));
    }


    @Override
    protected synchronized String createServerProcess(IInterpreterInfo interpreter, int pWrite, int pRead) throws IOException {
        File file = new File(interpreter.getExecutableOrJar());
        if(file.exists() == false ){
            throw new RuntimeException("The interpreter location found does not exist. "+interpreter);
        }
        if(file.isDirectory() == true){
            throw new RuntimeException("The interpreter location found is a directory. "+interpreter);
        }


        String execMsg;
        if(REF.isWindowsPlatform()){ //in windows, we have to put python "path_to_file.py"
            execMsg = interpreter+" \""+REF.getFileAbsolutePath(serverFile)+"\" "+pWrite+" "+pRead;
        }else{ //however in mac, or linux, this gives an error...
            execMsg = interpreter+" "+REF.getFileAbsolutePath(serverFile)+" "+pWrite+" "+pRead;
        }
        String[] parameters = SimplePythonRunner.preparePythonCallParameters(
                interpreter.getExecutableOrJar(), REF.getFileAbsolutePath(serverFile), new String[]{""+pWrite, ""+pRead});
        
        IInterpreterManager manager = PydevPlugin.getPythonInterpreterManager();
        
        String[] envp = null;
        try {
            envp = SimpleRunner.getEnvironment(null, interpreter, manager, true);
        } catch (CoreException e) {
            Log.log(e);
        }
        
        // Don't inherit the Java tool opts from the user's virtual environment
        for (int i = 0; i < envp.length; i++) {
            if (envp[i].contains("JAVA_TOOL_OPTIONS")) {
                envp[i] = "JAVA_TOOL_OPTIONS=-Xmx128M";
            }
        }

        process = SimpleRunner.createProcess(parameters, envp, serverFile.getParentFile());

        return execMsg;
    }



}