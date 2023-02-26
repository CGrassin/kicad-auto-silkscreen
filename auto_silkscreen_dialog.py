# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 3.10.1-0-g8feb16b)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class AutoSilkscreenDialog
###########################################################################

class AutoSilkscreenDialog ( wx.Dialog ):

	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Auto Silkscreen Parameters", pos = wx.DefaultPosition, size = wx.Size( 300,350 ), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		bSizer13 = wx.BoxSizer( wx.VERTICAL )

		self.m_staticText3 = wx.StaticText( self, wx.ID_ANY, u"This plugin optimizes the position of the silkscreen reference indicators . \nThe processing may take a few minutes.", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText3.Wrap( 300 )

		bSizer13.Add( self.m_staticText3, 0, wx.ALL, 5 )

		self.m_staticline2 = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
		bSizer13.Add( self.m_staticline2, 0, wx.EXPAND |wx.ALL, 5 )

		fgSizer1 = wx.FlexGridSizer( 0, 2, 0, 0 )
		fgSizer1.AddGrowableCol( 1 )
		fgSizer1.SetFlexibleDirection( wx.BOTH )
		fgSizer1.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_staticText4 = wx.StaticText( self, wx.ID_ANY, u"Max. distance (mm)", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText4.Wrap( -1 )

		fgSizer1.Add( self.m_staticText4, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_maxDistance = wx.TextCtrl( self, wx.ID_ANY, u"3", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_maxDistance.SetToolTip( u"Maximum allowed distance from footprint to reference. Higher values decrease performance." )

		fgSizer1.Add( self.m_maxDistance, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_staticText41 = wx.StaticText( self, wx.ID_ANY, u"Step size (mm)", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText41.Wrap( -1 )

		fgSizer1.Add( self.m_staticText41, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_stepSize = wx.TextCtrl( self, wx.ID_ANY, u"0.25", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_stepSize.SetToolTip( u"Amount the silkscreen is moved for each iteration. Lower values decrease performance." )

		fgSizer1.Add( self.m_stepSize, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_staticText101 = wx.StaticText( self, wx.ID_ANY, u"Allow silkscreen on via", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText101.Wrap( -1 )

		fgSizer1.Add( self.m_staticText101, 0, wx.ALL, 5 )

		self.m_silkscreenOnVia = wx.CheckBox( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_silkscreenOnVia.SetValue(True)
		self.m_silkscreenOnVia.SetToolTip( u"Check to allow the plugin to put silkscreen on top of vias." )

		fgSizer1.Add( self.m_silkscreenOnVia, 0, wx.ALL, 5 )

		self.m_staticText10 = wx.StaticText( self, wx.ID_ANY, u"Only process selection", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText10.Wrap( -1 )

		fgSizer1.Add( self.m_staticText10, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_onlyProcessSelection = wx.CheckBox( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_onlyProcessSelection.SetToolTip( u"Check to only move the silkscreen of the selected footprints." )

		fgSizer1.Add( self.m_onlyProcessSelection, 1, wx.ALL|wx.EXPAND, 5 )


		bSizer13.Add( fgSizer1, 1, wx.EXPAND, 5 )

		bSizer16 = wx.BoxSizer( wx.HORIZONTAL )

		self.m_Launch = wx.Button( self, wx.ID_OK, u"Run", wx.DefaultPosition, wx.DefaultSize, 0 )

		self.m_Launch.SetDefault()
		bSizer16.Add( self.m_Launch, 0, wx.ALL, 5 )

		self.m_button3 = wx.Button( self, wx.ID_CANCEL, u"Cancel", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer16.Add( self.m_button3, 0, wx.ALL, 5 )


		bSizer13.Add( bSizer16, 0, wx.ALIGN_RIGHT|wx.EXPAND, 5 )


		self.SetSizer( bSizer13 )
		self.Layout()

		self.Centre( wx.BOTH )

	def __del__( self ):
		pass


