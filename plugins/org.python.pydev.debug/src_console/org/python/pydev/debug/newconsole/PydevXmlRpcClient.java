/**
 * Copyright (c) 2005-2011 by Appcelerator, Inc. All Rights Reserved.
 * Licensed under the terms of the Eclipse Public License (EPL).
 * Please see the license.txt included with this distribution for details.
 * Any modifications to this file must keep this entire header intact.
 */
package org.python.pydev.debug.newconsole;

import java.lang.reflect.Field;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.concurrent.atomic.AtomicReference;

import org.apache.xmlrpc.XmlRpcException;
import org.apache.xmlrpc.XmlRpcRequest;
import org.apache.xmlrpc.client.AsyncCallback;
import org.apache.xmlrpc.client.XmlRpcClient;
import org.apache.xmlrpc.client.XmlRpcClientConfigImpl;
import org.eclipse.core.runtime.IStatus;
import org.python.pydev.core.docutils.StringUtils;
import org.python.pydev.core.net.LocalHost;
import org.python.pydev.debug.core.PydevDebugPlugin;

/**
 * Subclass of XmlRpcClient that will monitor the process so that if the process is destroyed, we stop waiting 
 * for messages from it.
 *
 * @author Fabio
 */
public class PydevXmlRpcClient implements IPydevXmlRpcClient{

    /**
     * Internal xml-rpc client (responsible for the actual communication with the server)
     */
    private XmlRpcClient impl;
    
    /**
     * The process where the server is being executed.
     */
    private Process process;

    /**
     * Constructor (see fields description)
     */
    public PydevXmlRpcClient(Process process) {
        this.impl = new XmlRpcClient();
        this.process = process;
    }

    /**
     * Sets the port where the server is started.
     * @throws MalformedURLException 
     */
    public void setPort(int port) throws MalformedURLException {
        XmlRpcClientConfigImpl config = new XmlRpcClientConfigImpl();
        config.setServerURL(new URL("http://"+LocalHost.getLocalHost()+":"+port));

        this.impl.setConfig(config);
    }
    

    /**
     * Executes a command in the server. 
     * 
     * Within this method, we should be careful about being able to return if the server dies.
     * If we wanted to have a timeout, this would be the place to add it.
     * 
     * @return the result from executing the given command in the server.
     */
    public Object execute(String command, Object[] args) throws XmlRpcException{
        final AtomicReference<Object> result = new AtomicReference<Object>(null);
        
        //make an async call so that we can keep track of not actually having an answer.
        this.impl.executeAsync(command, args, new AsyncCallback(){

            public void handleError(XmlRpcRequest request, Throwable error) {
                result.set(new Object[]{error.getMessage()});
            }

            public void handleResult(XmlRpcRequest request, Object receivedResult) {
                result.set(receivedResult);
            }}
        );

        // loop waiting for the answer (or having the console die).
        // The volatile variable gives us a memory barrier which makes this less insane
        while(result.get() == null){
            try {
                if(process != null){
                    int exitValue = process.exitValue();
                    result.set(new Object[]{
                            StringUtils.format("Console already exited with value: %s while waiting for an answer.\n", exitValue)});

                    //ok, we have an exit value!
                    break;
                }
            } catch (IllegalThreadStateException e) {
                //that's ok... let's sleep a bit
                try {
                    Thread.sleep(1);
                } catch (InterruptedException e1) {
//                        Log.log(e1);
                }
            }
        }
        return result.get();
    }

    public void interrupt(int signal) {
        // This is evil evil evil. I'm sorry.
        // Todo this properly, borrow the native process signalling bits from Eclipse CDT
        try {
            Field f = process.getClass().getDeclaredField("pid");
            f.setAccessible(true);
            Runtime.getRuntime().exec("kill -" + signal + " " + f.get(process));
        } catch (Exception e) {
            PydevDebugPlugin.log(IStatus.ERROR, "Problem interrupting python process", e);
        }
    }

}
