/**
 * Copyright (c) 2005-2011 by Appcelerator, Inc. All Rights Reserved.
 * Licensed under the terms of the Eclipse Public License (EPL).
 * Please see the license.txt included with this distribution for details.
 * Any modifications to this file must keep this entire header intact.
 */
package org.python.pydev.debug.newconsole;

import java.net.MalformedURLException;

import org.apache.xmlrpc.XmlRpcException;

/**
 * Interface that determines what's needed from the xml-rpc server.
 *
 * @author Fabio
 */
public interface IPydevXmlRpcClient {

    /**
     * Sets the port which the server is expecting to communicate. 
     * @param port port where the server was started.
     * 
     * @throws MalformedURLException
     */
    void setPort(int port) throws MalformedURLException;

    /**
     * @param command the command to be executed in the server
     * @param args the arguments passed to the command
     * @return the result from executing the command
     * 
     * @throws XmlRpcException
     */
    Object execute(String command, Object[] args) throws XmlRpcException;

    /**
     * Send an interrupt signal to the underlying python process
     */
    void interrupt(int signal);
}
