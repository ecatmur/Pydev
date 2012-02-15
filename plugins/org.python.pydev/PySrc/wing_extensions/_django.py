#########################################################################
""" _django.py -- Django hooks for the debugger

Copyright (c) 1999-2010, Archaeopteryx Software, Inc.  All rights reserved.

Written by Stephan R.A. Deibel and John P. Ehresman

"""
#########################################################################

import os, sys
import _extensions
import dbgutils

# The name of the module to watch for that indicates presence of Django
kIndicatorModuleName = 'django.template'

# Turn this on to debug this module -- prints diagnostics and disables
# munging of locals and globals in template frames
kDebug = 0

  
########################################################################
class _SubLanguageHook(_extensions._SubLanguageHook):
  """Implementation of debugger hooks for Django templates.
  
  TEMPLATE_DEBUG in the settings.py file must be set to True"""

  #----------------------------------------------------------------------
  def __init__(self, err):
    _extensions._SubLanguageHook.__init__(self, err)
    self.__fExceptionCodeObjects = {}

  #----------------------------------------------------------------------
  def _GetMarkerFrames(self):
    """Get a list of code objects that mark entering sub-language mode,
    usually the top-level template language invocation."""
    
    code_objects = []
    try:
      django_template = sys.modules['django.template']
      code_objects.append(
        django_template.Template.render.func_code
      )
    except:
      if kDebug:
        print("  MARKER FRAMES EMPTY")
        e, v, tb = sys.exc_info()
        import traceback
        print(e, v)
        traceback.print_tb(tb)
      return []

    if kDebug:
      print("  MARKER FRAMES", code_objects)
    return code_objects

  #----------------------------------------------------------------------
  def _GetModulePaths(self):
    """Get a list of paths that define what is and isn't part of the
    sub-language implementation. These are used when in sub-language mode (as
    indicated by call of _GetMarkerFrame() to determine when to stop and when
    not to stop in Python code. Returns a list of tuples (pathname, in_impl)
    where pathname is the full path and in_impl is either 0 or 1, indicating
    whether the Python code at that path is part of the sub-language
    implementation. When in_impl is 1, the debugger does not stop in Python
    code within that directory except if indicated by _GetMarkerFrames() and
    _GetSubLanguageFrames(). The list is traversed in order and first match is
    taken and its in_impl value applied to the debugger's action. The
    pathnames can either be full path directory names or *.py names."""
    
    paths = []
    try:
      django_template = sys.modules['django.template']
      dirname = os.path.dirname(os.path.dirname(django_template.__file__))
      contrib_dir = os.path.join(dirname, 'contrib')
      paths.append((os.path.join(contrib_dir, 'admin', 'templatetags', 'log'), 1))
      paths.append((os.path.join(contrib_dir, 'comments', 'templatetags', 'comments'), 1))
      paths.append((os.path.join(contrib_dir, 'webdesign', 'templatetags', 'webdesign'), 1))
      paths.append((contrib_dir, 0))
      paths.append((dirname, 1))
    except:
      if kDebug:
        print("  MODULE PATHS EMPTY")
        e, v, tb = sys.exc_info()
        import traceback
        print(e, v)
        traceback.print_tb(tb)
      return []
    
    if kDebug:
      print("  MODULE PATHS", paths)
    return paths

  #----------------------------------------------------------------------
  def _GetSubLanguageFrames(self):
    """Get a list of code objects for calls in the sub-language
    implementation where the debugger should call _StopHere() to determine
    if a sub-language-level breakpoint or other stop condition is reached.
    These frames are what defines the unit of stepping in the sub-language.
    This may return a partial list depending on what modules have already
    been loaded."""

    if kDebug:
      print("ENTERING _GetSubLanguageFrames")
      
    try:
      django_template = sys.modules['django.template']
      django_template_debug = sys.modules['django.template.debug']
    except:
      if kDebug:
        print("  SUBLANGUAGE FRAMES EMPTY")
        e, v, tb = sys.exc_info()
        import traceback
        print(e, v)
        traceback.print_tb(tb)
      return []
    
    def add_code_objects(scope, code_objects, django_template=django_template):
      contents = dir(scope)
      for item in contents:
        val = getattr(scope, item, None)
        try:
          if issubclass(val, django_template.Node) and hasattr(val, 'render'):
            method = getattr(val, 'render')
            code_objects.append(method.__func__.func_code)
        except:
          pass
    
    def failure(modname):
      if kDebug:
        print("  SUBLANGUAGE FRAMES MODULE %s NOT YET IMPORTED" % modname)
        e, v, tb = sys.exc_info()
        import traceback
        print(e, v)
        traceback.print_tb(tb)
    
    code_objects = []
    try:
      django_template = sys.modules['django.template']
      add_code_objects(django_template, code_objects)
    except:
      failure('django.template')
    try:
      django_template_debug = sys.modules['django.template.debug']
      add_code_objects(django_template_debug, code_objects)
    except:
      failure('django.template.debug')
    try:
      django_template_defaulttags = sys.modules['django.template.defaulttags']
      add_code_objects(django_template_defaulttags, code_objects)
    except:
      failure('django.template.defaulttags')
    try:
      django_template_loader_tags = sys.modules['django.template.loader_tags']
      add_code_objects(django_template_loader_tags, code_objects)
    except:
      failure('django.template.loader_tags')
    try:
      django_templatetags = sys.modules['django.templatetags']
      add_code_objects(django_templatetags, code_objects)
    except:
      failure('django.templatetags')
    try:
      django_templatetags.i18n = sys.modules['django.templatetags.i18n']
      add_code_objects(django_templatetags_i18n, code_objects)
    except:
      failure('django.templatetags.i18n')
    try:
      django_templatetags_cache = sys.modules['django.templatetags.cache']
      add_code_objects(django_templatetags_cache, code_objects)
    except:
      failure('django.templatetags.cache')
    try:
      django_contrib_admin_templatetags_log = sys.modules['django.contrib.admin.templatetags.log']
      add_code_objects(django_contrib_admin_templatetags_log, code_objects)
    except:
      failure('django.contrib.admin.templatetags.log')
    try:
      django_contrib_comments_templatetags_comments = sys.modules['django.contrib.comments.templatetags.comments']
      add_code_objects(django_contrib_comments_templatetags_comments, code_objects)
    except:
      failure('django.contrib.comments.templatetags.comments')
    try:
      django_contrib_webdesign_templatetags_webdesign = sys.modules['django.contrib.webdesign.templatetags.webdesign']
      add_code_objects(django_contrib_webdesign_templatetags_webdesign, code_objects)
    except:
      failure('django.contrib.webdesign.templatetags.webdesign')
    
    # XXX Note that django.template.Library.inclusion_tag.dec.InclusionNode cannot be
    # XXX accessed to add it but likely we will want to step there; would need to
    # XXX change Django by moving this class to top level
    
    try:
      def get_node_from_node_list(frame):
        try:
          return frame.f_locals['node']
        except:
          return None
      self.__fExceptionCodeObjects[django_template_debug.DebugNodeList.render_node.__func__.func_code] = get_node_from_node_list
    except:
      if kDebug:
        print("  SUBLANGUAGE EXCEPTION CODE OBJECT SETUP FAILED")
        e, v, tb = sys.exc_info()
        import traceback
        print(e, v)
        traceback.print_tb(tb)
    if kDebug:
      print("  EXCEPTION CODE OBJECTS", self.__fExceptionCodeObjects)
      
    code_objects.extend(self.__fExceptionCodeObjects.keys())
    if kDebug:
      print("  SUB_LANGUAGE CODE OBJECTS", code_objects)
      
    return code_objects
  
  #----------------------------------------------------------------------
  def _StopHere(self, frame, event_type, action):
    """Returns True if the debugger should stop in the current stack frame.
    Only called for frames that match one of those designated in
    _GetSubLanguageFrames. Event type is the current debug tracer event: -1
    for exception, 0 for call event, 1 for line event, and 2 for return event.
    Action is the last requested debugger action: -1 to free-run until next
    breakpoint or exception, 0 to step into, 1 to step over, and 2 to step
    out."""
    
    if kDebug:
      print("  STOPHERE", frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name, event_type, action)

    # Stop on exception only in certain places
    if event_type == -1:
      if frame.f_code in self.__fExceptionCodeObjects:
        if kDebug:
          print("    stopping on exception")
        return 1
      else:
        if kDebug:
          print("    not stopping on exception")
        return 0
    
    # Stop on next call event if stepping in or over
    if event_type == 0:
      if frame.f_code in self.__fExceptionCodeObjects:
        if kDebug:
          print("  not stopping in exception code object")
        return 0
      elif action == 0 or action == 1:
        if kDebug:
          print("    stopping")
        return 1
      else:
        if kDebug:
          print("    not stopping")
        return 0
    
    # Never stop on line or return event in the sub-language impl
    if kDebug:
      print("    not stopping (line or return)")
    return 0
  
  #----------------------------------------------------------------------
  def _TranslateFrame(self, frame, use_positions=1):
    """Get the filename, lineno, code_line, code_name, and list of variables
    for the given frame. This is only called for those identified by
    _GetSubLanguageFrames(). When use_positions=1 (the default) then the
    lineno should be (start, end) positions. In other cases, it should be a
    line number."""

    if kDebug:
      print("  _TranslateFrame starting", frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name)

    if frame.f_code in self.__fExceptionCodeObjects:
      if kDebug:
        print("  Exception", self.__fExceptionCodeObjects)
      dbg_node = self.__fExceptionCodeObjects[frame.f_code](frame)
      if kDebug:
        print("  dbg_node", dbg_node)
    else:
      if kDebug:
        print("  Not Exception", self.__fExceptionCodeObjects)
      dbg_node = frame.f_locals['self']
      if kDebug:
        print("  dbg_node", dbg_node)
        e, v, tb = sys.exc_info()
        import traceback
        print(e, v)
        traceback.print_tb(tb)
    
    filename = dbg_node.source[0].name
    start, end = dbg_node.source[1]
    
    if kDebug:
      print("  _TranslateFrame", filename, start, end)
     
    # Note: Need to compensate for Django converting to \n newlines and not
    # adjusting the start, end positions to match actual template file
    
    f = open(filename, mode='rb')
    txt = f.read()
    f.close()

    txtn = txt.replace('\r\n', '\n').replace('\r', '\n')
    while (start < end-1 and txtn[start] == '\n'):
      start += 1
    code_line = txtn[start:end]
    
    code_name = str(dbg_node).replace('\n', '').replace('\r', '')
     
    # XXX Optimize/cache!
    if use_positions:
      fudge = 0
      for i in range(0, start):
        if txt[i] == '\r' and i+1 < start and txt[i+1] == '\n':
          fudge += 1
      lineno = (start+fudge, end+fudge)
    else:
      lineno = 1
      for i in range(0, start):
        if txt[i] == '\n':
          lineno += 1
  
    if kDebug:
      print("  _TranslateFrame result", filename, lineno)
    return (filename, lineno, code_line, code_name, [])
  
  #----------------------------------------------------------------------
  def _VisibleFrame(self, stack, idx):
    """Check whether the frame in given stack index should be visible to the
    user. This allows for sub-languages where recursion on the stack occurs
    within processing of a single sub-language file. _TranslateFrame should
    still translate the frame so that breakpoint can be reached but this call
    is used to remove duplicate stack frames from view. This is only called
    for frames identified by _GetSubLanguageFrames()."""

    frame, lineno = stack[idx]
    
    if frame.f_code in self.__fExceptionCodeObjects:
      dbg_node = self.__fExceptionCodeObjects[frame.f_code](frame)
    else:
      dbg_node = frame.f_locals['self']
    filename = dbg_node.source[0].name

    idx += 1
    while idx < len(stack):
      try:
        f, ln = stack[idx]
        if f.f_code in self.__fExceptionCodeObjects:
          fdbn = self.__fExceptionCodeObjects[f.f_code](f)
        else:
          fdbn = f.f_locals['self']
        ffn = fdbn.source[0].name
        # Prefer innermost frame for template
        if ffn == filename:
          return 0
      except:
        # Stop at call of another template (or possibly same template recursively)
        if f.f_code in self._GetMarkerFrames():
          return 1
      idx += 1
      
    # No frame for same template found further down stack
    return 1

  #----------------------------------------------------------------------
  def _GetStepOutFrame(self, frame):
    """Get the frame at which the debugger should stop if a "step out"
    operation is seen in the given stack frame.  This may be called for
    both sub-language frames and regular Python frames; for the latter,
    the enclosing frame should be returned."""
    
    
    if kDebug:
      print("  GetStepOutFrame starting", frame.f_code.co_filename, frame.f_lineno)
  
    markers = self._GetMarkerFrames()
    slframes = self._GetSubLanguageFrames()
    if frame.f_code in slframes:
      fn, lineno, codeline, codename, v = self._TranslateFrame(frame)
    else:
      fn = None
    
    f = frame.f_back
    last_slframe = frame
    while f is not None:
      if f.f_code in slframes:
        last_slframe = f
        fn2 = self._TranslateFrame(f)[0]
        if fn2 != fn:
          if kDebug:
            print("  GetStepOutFrame no file match", f.f_code.co_filename, f.f_lineno)
          return f
      f = f.f_back
      
    if kDebug:
      print("  GetStepOutFrame file match", last_slframe.f_code.co_filename, last_slframe.f_lineno)
    return last_slframe.f_back
    
  #----------------------------------------------------------------------
  def _GetLocals(self, frame):
    """Get the local variables for given frame.  This is only called for
    those identified by _GetSubLanguageFrames()"""

    if kDebug:
      return frame.f_locals
  
    f_locals = {}
    context = frame.f_locals['context']
    for d in context.dicts:
      try:
        f_locals.update(d)
      except:
        pass
      
    for key, value in f_locals.items():
      try:
        if str(type(value)).find('__proxy__') >= 0 and hasattr(value, 'encode'):
          f_locals[key] = value.encode('utf-8')
      except:
        pass
      
    return f_locals
    
  #----------------------------------------------------------------------
  def _GetGlobals(self, frame):
    """Get the global variables for given frame.  This is only called for
    those identified by _GetSubLanguageFrames()"""

    if kDebug:
      return frame.f_globals
    
    return {}
    
  #----------------------------------------------------------------------
  def _Eval(self, expr, frame):
    """Evaluate the given expression in the given stack frame. This is only
    called when the debugger is paused or at a breakpoint or exception.
    Returns the result of the evaluation."""

    return eval(expr, frame.f_globals, self._GetLocals(frame))
    
  #----------------------------------------------------------------------
  def _Exec(self, expr, frame):
    """Execute the given expression in the given stack frame.  This is only
    called when the debugger is paused or at a breakpoint or exception."""
    
    if expr.strip().find('\n') < 0 and expr.strip().find('\r') < 0:
      mode = 'single'
    else:
      mode = 'exec'
    code = compile(expr + '\n', '<wingdb_compile>', mode, 0, 0)
    exec(code, frame.f_globals, self._GetLocals(frame))
    
  #----------------------------------------------------------------------
  def _GetOutput(self, frame):
    raise NotImplementedError
   
  