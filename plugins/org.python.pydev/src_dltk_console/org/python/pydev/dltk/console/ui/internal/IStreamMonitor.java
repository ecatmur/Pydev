package org.python.pydev.dltk.console.ui.internal;

public interface IStreamMonitor {
    public void addListener(IStreamListener listener);

    public void removeListener(IStreamListener listener);
}
