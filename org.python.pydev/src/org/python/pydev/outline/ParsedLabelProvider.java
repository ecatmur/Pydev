/*
 * Author: atotic
 * Created: Jul 25, 2003
 * License: Common Public License v1.0
 */
package org.python.pydev.outline;

import org.eclipse.jface.viewers.LabelProvider;
import org.eclipse.swt.graphics.Image;
import org.python.pydev.editor.model.*;
import org.python.pydev.ui.ImageCache;
import org.python.pydev.ui.UIConstants;

/**
 * 
 * LabelProvider for ParsedItems inside an outline view
 */
public class ParsedLabelProvider extends LabelProvider {
	
	ImageCache imageCache;
	
	public ParsedLabelProvider(ImageCache imageCache) {
		this.imageCache = imageCache;
	}

	public String getText(Object element) {
		return ((ParsedItem)element).toString();
	}

	// returns images based upon element type
	public Image getImage(Object element) {
		AbstractNode token = ((ParsedItem)element).getToken();
		if (token instanceof ClassNode) {
			return imageCache.get(UIConstants.CLASS_ICON);
		}
		else if (token instanceof FunctionNode) {
			if (((FunctionNode)token).astNode.name.startsWith("_")) {
				return imageCache.get(UIConstants.PRIVATE_METHOD_ICON);
			}
			else
				return imageCache.get(UIConstants.PUBLIC_METHOD_ICON);
		}
		else if (token instanceof ImportNode) {
			return imageCache.get(UIConstants.IMPORT_ICON);
		}
		else if (token instanceof ImportFromNode) {
			return imageCache.get(UIConstants.IMPORT_ICON);
		}
		else if (token instanceof NameEqualsMainNode) {
			return imageCache.get(UIConstants.MAIN_FUNCTION_ICON);
		}
		else {
			return imageCache.get("ERROR");
		}
	}
}
