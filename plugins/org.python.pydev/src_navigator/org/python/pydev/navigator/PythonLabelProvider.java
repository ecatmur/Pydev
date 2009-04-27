/*
 * Created on Oct 7, 2006
 * @author Fabio
 */
package org.python.pydev.navigator;

import org.eclipse.core.resources.IFile;
import org.eclipse.core.resources.IFolder;
import org.eclipse.core.resources.IMarker;
import org.eclipse.core.resources.IProject;
import org.eclipse.jface.viewers.DecorationOverlayIcon;
import org.eclipse.jface.viewers.IDecoration;
import org.eclipse.jface.viewers.ILabelProvider;
import org.eclipse.jface.viewers.ILabelProviderListener;
import org.eclipse.swt.graphics.Image;
import org.eclipse.ui.model.WorkbenchLabelProvider;
import org.python.pydev.core.structure.TreeNode;
import org.python.pydev.navigator.elements.IWrappedResource;
import org.python.pydev.navigator.elements.ProjectConfigError;
import org.python.pydev.navigator.elements.PythonFolder;
import org.python.pydev.navigator.elements.PythonNode;
import org.python.pydev.navigator.elements.PythonProjectSourceFolder;
import org.python.pydev.navigator.elements.PythonSourceFolder;
import org.python.pydev.plugin.PydevPlugin;
import org.python.pydev.ui.UIConstants;
import org.python.pydev.ui.filetypes.FileTypesPreferencesPage;

/**
 * Provides the labels for the pydev package explorer.
 * 
 * @author Fabio
 */
public class PythonLabelProvider implements ILabelProvider{

    private WorkbenchLabelProvider provider;
    
    private Image projectWithError = null;
    
    private Object lock = new Object();

    public PythonLabelProvider() {
        provider = new WorkbenchLabelProvider();
    }
    
    /**
     * @see org.eclipse.jface.viewers.ILabelProvider#getImage(java.lang.Object)
     */
    public Image getImage(Object element) {
        if(element instanceof PythonProjectSourceFolder){
            return PydevPlugin.getImageCache().get(UIConstants.PROJECT_SOURCE_FOLDER_ICON);
        }
        if(element instanceof PythonSourceFolder){
            return PydevPlugin.getImageCache().get(UIConstants.SOURCE_FOLDER_ICON);
        }
        if(element instanceof PythonFolder){
            PythonFolder folder = (PythonFolder) element;
            IFolder actualObject = folder.getActualObject();
            if(actualObject != null){
                final String[] validInitFiles = FileTypesPreferencesPage.getValidInitFiles();
                
                for(String init:validInitFiles){
                    if(actualObject.getFile(init).exists()){
                        if(checkParentsHaveInit(folder, validInitFiles)){
                            return PydevPlugin.getImageCache().get(UIConstants.FOLDER_PACKAGE_ICON);
                        }else{
                            break;
                        }
                    }
                }
            }
            return provider.getImage(actualObject);
        }
        if(element instanceof PythonNode){
            PythonNode node = (PythonNode) element;
            return node.entry.getImage();
        }
        if(element instanceof IWrappedResource){
            IWrappedResource resource = (IWrappedResource) element;
            return provider.getImage(resource.getActualObject());
        }
        if(element instanceof ProjectConfigError){
            return PydevPlugin.getImageCache().get(UIConstants.ERROR);
        }
        if(element instanceof TreeNode<?>){
            TreeNode<?> treeNode = (TreeNode<?>) element;
            LabelAndImage data = (LabelAndImage) treeNode.getData();
            return data.o2;
        }
        if(element instanceof IProject){
            IProject project = (IProject) element;
            try {
                IMarker[] markers = project.findMarkers(PythonBaseModelProvider.PYDEV_PACKAGE_EXPORER_PROBLEM_MARKER, true, 0);
                Image image = provider.getImage(element);
                if(markers == null || markers.length == 0){
                    return image;
                }
                
                //We have errors: make them explicit.
                if(projectWithError == null){
                    synchronized(lock){
                        //we must recheck again (if 2 got here and 1 got the lock while the other was waiting, when
                        //the other enters the lock, it does not need to recalculated).
                        if(projectWithError == null){
                            try {
                                DecorationOverlayIcon decorationOverlayIcon = new DecorationOverlayIcon(
                                        image, 
                                        PydevPlugin.getImageCache().getDescriptor(UIConstants.ERROR_SMALL), 
                                        IDecoration.BOTTOM_LEFT);
                                projectWithError = decorationOverlayIcon.createImage();
                            } catch (Exception e) {
                                PydevPlugin.log("Unable to create error decoration for project icon.", e);
                                projectWithError = image;
                            }
                        }
                    }
                }
                
            } catch (Exception e1) {
                PydevPlugin.log(e1);
            }
            return projectWithError;
        }
        return provider.getImage(element);
    }

    /**
     * Checks if all the parents have the needed __init__ files (needed to consider some folder an actual python module)
     * 
     * @param pythonFolder the python folder whose hierarchy should be checked (note that the folder itself must have already
     * been checked at this point)
     * @param validInitFiles the valid names for the __init__ files (because we can have more than one matching extension)
     * 
     * @return true if all the parents have the __init__ files and false otherwise.
     */
    private final boolean checkParentsHaveInit(final PythonFolder pythonFolder, final String[] validInitFiles) {
        IWrappedResource parentElement = pythonFolder.getParentElement();
        while(parentElement != null){
            if(parentElement instanceof PythonSourceFolder){
                //gotten to the source folder: this one doesn't need to have an __init__.py
                return true;
            }
            
            Object actualObject = parentElement.getActualObject();
            if(actualObject instanceof IFolder){
                IFolder folder = (IFolder) actualObject;
                boolean foundInit = false;
                for(String init:validInitFiles){
                    final IFile file = folder.getFile(init);
                    if(file.exists()){
                        foundInit = true;
                        break;
                    }
                }
                if(!foundInit){
                    return false;
                }
            }
            
            Object tempParent = parentElement.getParentElement();
            if(!(tempParent instanceof IWrappedResource)){
                break;
            }
            parentElement = (IWrappedResource) tempParent;

        }
        return true;
    }

    /**
     * @see org.eclipse.jface.viewers.ILabelProvider#getText(java.lang.Object)
     */
    public String getText(Object element) {
        if(element instanceof PythonNode){
            PythonNode node = (PythonNode) element;
            return node.entry.toString();
        }
            
        if(element instanceof PythonSourceFolder){
            PythonSourceFolder sourceFolder = (PythonSourceFolder) element;
            return provider.getText(sourceFolder.container);
        }
        
        if(element instanceof IWrappedResource){
            IWrappedResource resource = (IWrappedResource) element;
            return provider.getText(resource.getActualObject());
        }
        if(element instanceof TreeNode<?>){
            TreeNode<?> treeNode = (TreeNode<?>) element;
            LabelAndImage data = (LabelAndImage) treeNode.getData();
            return data.o1;
        }
        if(element instanceof ProjectConfigError){
            return ((ProjectConfigError)element).getLabel();
        }
        
        return provider.getText(element);
    }

    /**
     * @see org.eclipse.jface.viewers.IBaseLabelProvider#addListener(org.eclipse.jface.viewers.ILabelProviderListener)
     */
    public void addListener(ILabelProviderListener listener) {
        provider.addListener(listener);
    }

    public void dispose() {
        provider.dispose();
    }

    public boolean isLabelProperty(Object element, String property) {
        return provider.isLabelProperty(element, property);
    }

    public void removeListener(ILabelProviderListener listener) {
        provider.removeListener(listener);
    }


}
