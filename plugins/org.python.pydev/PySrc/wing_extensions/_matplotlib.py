""" _matplotlib.py -- Plugin for working w/ matplotlib and pylab

Copyright (c) 1999-2011, Archaeopteryx Software, Inc.  All rights reserved.

Written by Stephan R.A. Deibel and John P. Ehresman

"""

import sys
import _extensions

kIndicatorModuleName = ('pylab', 'matplotlib')

kDebug = 0

def get_wx_core():
  import wx
  try:
    return wx._core_
  except:
    pass
  try:
    return wx._core
  except:
    return None

class _ExecHelper(_extensions._ExecHelper):

  def __init__(self):

    if kDebug:
      print("Activating matplotlib helper")

    import matplotlib
    if not hasattr(matplotlib, 'use') or not hasattr(matplotlib, 'get_backend'):
      raise RuntimeError()
    self.__fMatplotlib = matplotlib

    self.__fOriginalUse = matplotlib.use
    def wrap_use(*args, **kw):
      self.__fOriginalUse(*args, **kw)
      self.__ChangeBackend()
    matplotlib.use = wrap_use

    self.__fPendingCleanup = None
    self.__fInitialShow = 0

    self.__ChangeBackend()

  def __ChangeBackend(self):

    if kDebug:
      print("__ChangeBackend")

    if self.__fPendingCleanup:
      self.__fPendingCleanup()
      self.__fPendingCleanup = None

    self.__fBackend = self.__fMatplotlib.get_backend()
    if kDebug:
      print("Backend: ", self.__fBackend)

    self.Prepare = self.__Noop
    self.Cleanup = self.__Noop
    self.Update = self.__Noop

    if self.__fBackend == 'TkAgg':
      try:
        import Tkinter
      except ImportError:
        pass
      else:
        self.__fTkinter = Tkinter
        self.__fSavedMainloop = Tkinter.mainloop
        self.__fSavedMiscMainloop = Tkinter.Misc.mainloop
        self.Prepare = self.__TkPrepare
        self.Cleanup = self.__TkCleanup
        self.Update = self.__TkUpdate

    elif self.__fBackend == 'Qt4Agg':
      try:
        from PyQt4 import QtGui
        from PyQt4 import QtCore
      except ImportError:
        pass
      else:
        self.__fQtGui = QtGui
        self.__fQtCore = QtCore
        self.__fSavedqAppMainloop = QtGui.qApp.exec_
        self.__fSavedQApplicationMainloop = QtGui.QApplication.exec_
        self.__fSavedQCoreMainloop = QtCore.QCoreApplication.exec_
        self.Prepare = self.__Qt4Prepare
        self.Cleanup = self.__Qt4Cleanup
        self.Update = self.__Qt4Update

    elif self.__fBackend == 'GTKAgg' or self.__fBackend == 'GTKCairo':
      try:
        import gtk
      except ImportError:
        pass
      else:
        self.__fGTK = gtk
        self.__fSavedGTKMainloop = gtk.mainloop
        self.__fSavedGTKMain = gtk.main
        self.Prepare = self.__GtkPrepare
        self.Cleanup = self.__GtkCleanup
        self.Update = self.__GtkUpdate

    elif self.__fBackend == 'WXAgg':
      try:
        import wx
      except ImportError:
        pass
      else:
        self.__fWX = wx
        self.__fWXCore = get_wx_core()
        if self.__fWXCore is not None:
          self.__fWxEventloop = wx.EventLoop()
          self.Prepare = self.__WxPrepare
          self.Cleanup = self.__WxCleanup
          self.Update = self.__WxUpdate

  def __TkPrepare(self):
    if kDebug:
      print("__TkPrepare")
    self.__fTkinter.mainloop = self.__Noop
    self.__fTkinter.Misc.mainloop = self.__Noop
    self.__fWasInteractive = self.__fMatplotlib.is_interactive()
    self.__fMatplotlib.interactive(True)
    self.__fPendingCleanup = self.__TkCleanup

  def __TkUpdate(self):
    if kDebug:
      print("__TkUpdate")
    # This only works in the main thread in Tk
    top = None
    try:
      try:
        top = self.__fTkinter.Tk()
        top.withdraw()
      except:
        if kDebug:
          import traceback
          traceback.print_exc()
        try:
          top.destroy()
          top = None
        except:
          top = None
      if top is not None:
        top.update()
        top.destroy()
    except:
      if kDebug:
        import traceback
        traceback.print_exc()

  def __TkCleanup(self):
    if kDebug:
      print("__TkCleanup")
    self.__fPendingCleanup = None
    self.__fTkinter.mainloop = self.__fSavedMainloop
    self.__fTkinter.Misc.mainloop = self.__fSavedMiscMainloop
    self.__fMatplotlib.interactive(self.__fWasInteractive)

  def __Qt4Prepare(self):
    if kDebug:
      print ("__Qt4Prepare")
    self.__fQtGui.qApp.exec_ = self.__Noop
    self.__fQtGui.QApplication.exec_ = self.__Noop
    self.__fQtCore.QCoreApplication.exec_ = self.__Noop
    try:
      self.__fQtCore.pyqtRemoveInputHook()
    except:
      pass
    self.__fWasInteractive = self.__fMatplotlib.is_interactive()
    self.__fMatplotlib.interactive(True)
    self.__fPendingCleanup = self.__Qt4Cleanup

  def __Qt4Cleanup(self):
    if kDebug:
      print ("__Qt4Cleanup")
    self.__fPendingCleanup = None
    self.__fQtGui.qApp.exec_ = self.__fSavedqAppMainloop
    self.__fQtGui.QApplication.exec_ = self.__fSavedQApplicationMainloop
    self.__fQtCore.QCoreApplication.exec_ = self.__fSavedQCoreMainloop
    try:
      self.__fQtCore.pyqtRestoreInputHook()
    except:
      pass
    self.__fMatplotlib.interactive(self.__fWasInteractive)

  def __Qt4Update(self):
    if kDebug:
      print("__Qt4Update")
    self.__fQtGui.QApplication.processEvents()

  def __GtkPrepare(self):
    if kDebug:
      print ("__GtkPrepare")
    self.__fGTK.mainloop = self.__Noop
    self.__fGTK.main = self.__Noop
    self.__fWasInteractive = self.__fMatplotlib.is_interactive()
    self.__fMatplotlib.interactive(True)
    self.__fPendingCleanup = self.__GtkCleanup

  def __GtkCleanup(self):
    if kDebug:
      print ("__GtkCleanup")
    self.__fPendingCleanup = None
    self.__fGTK.mainloop = self.__fSavedGTKMainloop
    self.__fGTK.main = self.__fSavedGTKMain
    self.__fMatplotlib.interactive(self.__fWasInteractive)

  def __GtkUpdate(self):
    if kDebug:
      print("__GtkUpdate")
    import time
    start_time = time.time()
    while self.__fGTK.events_pending() and time.time() < start_time + 0.1:
      self.__fGTK.main_iteration()

  def __WxPrepare(self):
    if kDebug:
      print ("__WxPrepare")
      pass
    self.__fWXCore.PyApp_MainLoop = self.__Noop
    self.__fPendingCleanup = self.__WxCleanup

  def __WxCleanup(self):
    if kDebug:
      print ("__WxCleanup")
    self.__fPendingCleanup = None
    if self.__fMatplotlib.is_interactive() and not self.__fInitialShow and 'pylab' in sys.modules:
      sys.modules['pylab'].show()
      self.__fInitialShow = 1

  def __WxUpdate(self):
    if kDebug:
      print("__WxUpdate")

    app = self.__fWX.GetApp()
    if app is not None:
      import time
      start_time = time.time()
      self.__fWXEventLoopActivator = self.__fWX.EventLoopActivator(self.__fWxEventloop)
      try:
        while self.__fWxEventloop.Pending() and time.time() < start_time + 0.1:
          try:
            self.__fWxEventloop.Dispatch()
          except:
            if kDebug:
              print("dispatch failed")
            break
          app.ProcessIdle()
      finally:
        self.__fWXEventLoopActivator = None
    elif kDebug:
      print("app is none")

  def __Noop(self, *args, **kw):
    pass

