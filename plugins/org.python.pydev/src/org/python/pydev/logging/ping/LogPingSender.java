/**
 * Copyright (c) 2005-2011 by Appcelerator, Inc. All Rights Reserved.
 * Licensed under the terms of the Eclipse Public License (EPL).
 * Please see the license.txt included with this distribution for details.
 * Any modifications to this file must keep this entire header intact.
 */
package org.python.pydev.logging.ping;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.InputStreamReader;
import java.net.URL;
import java.net.URLConnection;
import java.net.UnknownHostException;
import java.util.zip.GZIPOutputStream;

import org.python.pydev.core.log.Log;
import org.python.pydev.plugin.PydevPlugin;

public class LogPingSender implements ILogPingSender{

	private static final String UPDATE_URL = "https://ping.aptana.com/ping.php"; //$NON-NLS-1$

	public boolean sendPing(String pingString) {
	    return true;
	}

}
