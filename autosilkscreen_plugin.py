import os
import pcbnew
import gettext
import wx,math

from pcbnew import ActionPlugin, GetBoard, SHAPE_POLY_SET, VECTOR2I, PCB_VIA

_ = gettext.gettext

__deflate_factor__ = 0.9

step = 0.25
max_offset = 3
IGNORE_ALREADY_VALID = True

# Postponed: handle non-rectangular FP

def isSilkscreen(item):
    return item is not None and (item.IsOnLayer(pcbnew.B_SilkS) or item.IsOnLayer(pcbnew.F_SilkS)) and item.IsVisible()

def BB_in_SHAPE_POLY_SET(bb,poly,all_in=False):
    if all_in:
        return poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetTop())) and poly.Contains(VECTOR2I(bb.GetRight(),bb.GetTop())) and poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetBottom())) and poly.Contains(VECTOR2I(bb.GetRight(),bb.GetBottom()))
    return poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetTop())) or poly.Contains(VECTOR2I(bb.GetRight(),bb.GetTop())) or poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetBottom())) or poly.Contains(VECTOR2I(bb.GetRight(),bb.GetBottom()))

# To consider: other things on SS,
def isPositionValid(item, modules, board_edge, vias):
    bb = item.GetBoundingBox() # BOX2I
    bb.SetSize(int(bb.GetWidth()*__deflate_factor__),int(bb.GetHeight()*__deflate_factor__))

    # Check if ref is inside PCB outline
    if not BB_in_SHAPE_POLY_SET(bb, board_edge,True):
        return False

    # Check if ref is colliding with any FP
    for fp in modules:
        # Collide with Ctyd
        fp_shape = fp.GetCourtyard(item.GetLayer()) # SHAPE_POLY_SET
        if BB_in_SHAPE_POLY_SET(bb, fp_shape):
            return False

        # Collide with Reference TODO: algo improvement nudge it?
        ref = fp.Reference()
        if ref.GetText() != item.GetText() and isSilkscreen(ref) and ref.IsOnLayer(item.GetLayer()) and bb.Intersects(ref.GetBoundingBox()):
            return False

    # Check if ref is colliding with any via
    for via in vias:
        if (via.TopLayer() == pcbnew.F_Cu and item.IsOnLayer(pcbnew.F_SilkS)) or (via.BottomLayer() == pcbnew.B_Cu and item.IsOnLayer(pcbnew.B_SilkS)):
            if bb.Intersects(via.GetBoundingBox()):
                return False

    # Check if via is colliding with any drawing
    # TODO
    return True

def decimal_range(start, stop, increment):
    while start < stop and not math.isclose(start, stop):
        yield start
        start += increment

def log(msg):
    wx.LogMessage(str(msg))

class AutoSilkscreenPlugin(ActionPlugin):
    def defaults(self):
        self.name = _(u"AutoSilkscreen")
        self.category = _(u"Modify PCB")
        self.description = _(u"Moves silkscreen")
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'logo.png')

    def Run(self):
        self.pcb = pcbnew.GetBoard()
        
        # Get unit conversion functions
        units_mode = pcbnew.GetUserUnits()
        if units_mode == 0:
            self.ToUserUnit = pcbnew.ToMils
            self.FromUserUnit = pcbnew.FromMils
        elif units_mode == 1:
            self.ToUserUnit = pcbnew.ToMM
            self.FromUserUnit = pcbnew.FromMM

        # Get the vias
        vias = []
        for via in self.pcb.Tracks():
            if isinstance(via,PCB_VIA):
                if via.TopLayer() == pcbnew.F_Cu or via.BottomLayer() == pcbnew.B_Cu:
                    vias.append(via)

        # Get board outline
        board_edge = SHAPE_POLY_SET()
        self.pcb.GetBoardPolygonOutlines(board_edge)

        # Get footprints
        modules = self.pcb.GetFootprints()
        for fp in modules:
            ref = fp.Reference()

            if not isSilkscreen(ref): continue
            if not IGNORE_ALREADY_VALID and isPositionValid(ref,modules, board_edge, vias): continue

            ref_bb = ref.GetBoundingBox()
            fp_bb = fp.GetBoundingBox(False,False)

            # -----------
            initial_pos = ref.GetPosition()
            try:
                for i in decimal_range(0, max_offset, step):
                    # Sweep x coords: top (left/right from center), bottom (left/right from center)
                    for j in decimal_range(0, self.ToUserUnit(fp_bb.GetWidth()/2) + i, step):
                        ref.SetY(int(fp_bb.GetTop() - ref_bb.GetHeight()/2.0*__deflate_factor__ - self.FromUserUnit(i)))
                        ref.SetX(int(fp_bb.GetCenter().x - self.FromUserUnit(j)))
                        if isPositionValid(ref,modules, board_edge, vias): raise StopIteration 

                        ref.SetX(int(fp_bb.GetCenter().x + self.FromUserUnit(j)))
                        if isPositionValid(ref,modules, board_edge, vias): raise StopIteration 

                        ref.SetY(int(fp_bb.GetBottom() + ref_bb.GetHeight()/2.0*__deflate_factor__ + self.FromUserUnit(i)))
                        ref.SetX(int(fp_bb.GetCenter().x - self.FromUserUnit(j)))
                        if isPositionValid(ref,modules, board_edge, vias): raise StopIteration 

                        ref.SetX(int(fp_bb.GetCenter().x + self.FromUserUnit(j)))
                        if isPositionValid(ref,modules, board_edge, vias): raise StopIteration 

                    # Sweep y coords: left (top/bot from center), right (top/bot from center)
                    for j in decimal_range(0, self.ToUserUnit(fp_bb.GetHeight()/2) + i, step):
                        ref.SetX(int(fp_bb.GetLeft() - ref_bb.GetWidth()/2.0*__deflate_factor__ - self.FromUserUnit(i)))
                        ref.SetY(int(fp_bb.GetCenter().y - self.FromUserUnit(j)))
                        if isPositionValid(ref,modules, board_edge, vias): raise StopIteration 

                        ref.SetY(int(fp_bb.GetCenter().y + self.FromUserUnit(j)))
                        if isPositionValid(ref,modules, board_edge, vias): raise StopIteration 

                        ref.SetX(int(fp_bb.GetRight() + ref_bb.GetWidth()/2.0*__deflate_factor__ + self.FromUserUnit(i)))
                        ref.SetY(int(fp_bb.GetCenter().y - self.FromUserUnit(j)))
                        if isPositionValid(ref,modules, board_edge, vias): raise StopIteration 

                        ref.SetY(int(fp_bb.GetCenter().y + self.FromUserUnit(j)))
                        if isPositionValid(ref,modules, board_edge, vias): raise StopIteration 
                # Resest to default position if not able to be moved
                ref.SetPosition(initial_pos)
                log("{} couldn't be moved".format(str(fp.GetReference())))
            except StopIteration:
                log("{} moved to ({:.2f},{:.2f})".format(str(fp.GetReference()), self.ToUserUnit(ref.GetPosition().x), self.ToUserUnit(ref.GetPosition().y)))
        log('Finished')
            