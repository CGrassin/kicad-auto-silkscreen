import os
import pcbnew
import gettext
import wx,math

from pcbnew import ActionPlugin, GetBoard

_ = gettext.gettext

__deflate_factor__ = 0.9

step = 0.25
max_offset = 5

def isSilkscreen(item):
    return item is not None and (item.IsOnLayer(pcbnew.B_SilkS) or item.IsOnLayer(pcbnew.F_SilkS)) and item.IsVisible()

def isPositionValid(item,modules):

    bb = item.GetBoundingBox()
    bb.SetSize(int(bb.GetWidth()*__deflate_factor__),int(bb.GetHeight()*__deflate_factor__))
    for fp in modules:
        if fp.GetBoundingBox(False,False).Intersects(bb):
            return False
    return True

def decimal_range(start, stop, increment):
    while start < stop and not math.isclose(start, stop):
        yield start
        start += increment

class AutoSilkscreenPlugin(ActionPlugin):
    def defaults(self):
        self.name = _(u"AutoSilkscreen")
        self.category = _(u"Modify PCB")
        self.description = _(u"Moves silkscreen")
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'logo.png')

    def Run(self):
        self.board = pcbnew.GetBoard()
        
        units_mode = pcbnew.GetUserUnits()
        if units_mode == 0:
            self.ToUserUnit = pcbnew.ToMils
            self.FromUserUnit = pcbnew.FromMils
        elif units_mode == 1:
            self.ToUserUnit = pcbnew.ToMM
            self.FromUserUnit = pcbnew.FromMM

        if hasattr(self.board, 'GetModules'):

            modules = self.board.GetModules()
        else:
            modules = self.board.GetFootprints()
        txt=""
        for fp in modules:
            ref = fp.Reference()
            if not isSilkscreen(ref): continue

            # WORKS but only detects vertect colision
            # fp_shape = fp.GetEffectiveShape(pcbnew.F_CrtYd)
            # ref_shape = ref.GetEffectiveShape(pcbnew.F_SilkS)
            # txt += str(ref.GetShownText())+ " -> "+str(fp_shape.Collide(ref_shape)) + "\n"

            # ref.SetX(ref.GetX()+self.FromUserUnit(float(1)))
            if isPositionValid(ref,modules): continue

            # initial_x, initial_y = ref.GetX(),ref.GetY()
            initial_x, initial_y = fp.GetPosition()
            for i in decimal_range(step, max_offset, step):
                ref.SetX(initial_x-self.FromUserUnit(float(i)))
                ref.SetY(initial_y)
                if isPositionValid(ref,modules): break
                ref.SetX(initial_x) #cent-bot
                ref.SetY(initial_y+self.FromUserUnit(float(i)))
                if isPositionValid(ref,modules): break
                ref.SetX(initial_x+self.FromUserUnit(float(i)))
                ref.SetY(initial_y) #right
                if isPositionValid(ref,modules): break 
                ref.SetX(initial_x)
                ref.SetY(initial_y-self.FromUserUnit(float(i))) #cent-top
                if isPositionValid(ref,modules): break
                ref.SetX(initial_x-self.FromUserUnit(float(i)))
                ref.SetY(initial_y-self.FromUserUnit(float(i))) #left-top
                if isPositionValid(ref,modules): break 
                ref.SetX(initial_x-self.FromUserUnit(float(i)))
                ref.SetY(initial_y+self.FromUserUnit(float(i))) #left-bot
                if isPositionValid(ref,modules): break
                ref.SetX(initial_x+self.FromUserUnit(float(i)))
                ref.SetX(initial_x+self.FromUserUnit(float(i))) #right-top
                if isPositionValid(ref,modules): break
                ref.SetX(initial_x+self.FromUserUnit(float(i)))
                ref.SetY(initial_y+self.FromUserUnit(float(i))) #right-bot
                if isPositionValid(ref,modules): break
                #fix me: don't move if fail

            txt += str(ref.GetShownText())+ " -> "+str(isPositionValid(ref,modules)) + "\n"
            

        # wx.MessageBox(txt)
            