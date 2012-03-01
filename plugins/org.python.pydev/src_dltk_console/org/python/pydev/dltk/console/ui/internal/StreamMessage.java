package org.python.pydev.dltk.console.ui.internal;

  
public class StreamMessage {
        public StreamType type;
        public String     message;
        
        StreamMessage(StreamType type, String message) {
            this.type    = type;
            this.message = message;
        }
}
