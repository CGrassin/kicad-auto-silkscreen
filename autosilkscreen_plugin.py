import os
import pcbnew
import gettext
import wx, math

from pcbnew import ActionPlugin, GetBoard, SHAPE_POLY_SET, VECTOR2I, PCB_VIA

from . import auto_silkscreen_dialog

__deflate_factor__ = 0.9

IGNORE_ALREADY_VALID = False

def isSilkscreen(item):
    if item is None:
        return False
    elif not (item.IsOnLayer(pcbnew.B_SilkS) or item.IsOnLayer(pcbnew.F_SilkS)):    
        return False
    elif hasattr(item, 'IsVisible'):
        if not item.IsVisible():
            return False
    return True

def BB_in_SHAPE_POLY_SET(bb,poly,all_in=False):
    if all_in:
        return poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetTop())) and poly.Contains(VECTOR2I(bb.GetRight(),bb.GetTop())) and poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetBottom())) and poly.Contains(VECTOR2I(bb.GetRight(),bb.GetBottom())) and poly.Contains(VECTOR2I(bb.GetCenter().x,bb.GetCenter().y))
    return poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetTop())) or poly.Contains(VECTOR2I(bb.GetRight(),bb.GetTop())) or poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetBottom())) or poly.Contains(VECTOR2I(bb.GetRight(),bb.GetBottom())) or poly.Contains(VECTOR2I(bb.GetCenter().x,bb.GetCenter().y))

def isPositionValid(item, modules, board_edge, vias, tht_pads):
    bb = item.GetBoundingBox() # BOX2I
    bb.SetSize(int(bb.GetWidth()*__deflate_factor__),int(bb.GetHeight()*__deflate_factor__))

    # Check if ref is inside PCB outline
    if not BB_in_SHAPE_POLY_SET(bb, board_edge, True):
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

    # Check if ref is colliding with any hole
    for pad in tht_pads:
        if bb.Intersects(pad.GetBoundingBox()):
            return False

    # TODO Check if via is colliding with any drawing
    # TODO Check if via is colliding with any solder mask


    return True

def decimal_range(start, stop, increment):
    while start < stop and not math.isclose(start, stop):
        yield start
        start += increment

def log(msg):
    wx.LogMessage(str(msg))

def distance(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

def filter_distance(item_center, max_d, list_items):
    filtered_items = []
    for i in list_items:
        max_i_size = max(i.GetBoundingBox().GetHeight(), i.GetBoundingBox().GetWidth())
        if distance(item_center,i.GetBoundingBox().GetCenter()) < max_d + max_i_size:
            filtered_items.append(i)
    return filtered_items

def optimize(max_offset,step,only_process_selection,debug=False):
    pcb = pcbnew.GetBoard()

    # units_mode = pcbnew.GetUserUnits()
    # if units_mode == 0:
    #     self.ToUserUnit = pcbnew.ToMils
    #     self.FromUserUnit = pcbnew.FromMils
    # elif units_mode == 1:
    ToUserUnit = pcbnew.ToMM
    FromUserUnit = pcbnew.FromMM
    step_units = FromUserUnit(step)
    max_offset_units = FromUserUnit(max_offset)

    # Get PCB collision items
    # Get the vias (except buried vias)
    vias_all = [trk for trk in pcb.Tracks() if  isinstance(trk,PCB_VIA) and (trk.TopLayer() == pcbnew.F_Cu or trk.BottomLayer() == pcbnew.B_Cu)]
    # Get the PTH/NPTH pads
    tht_pads_all = [pad for pad in pcb.GetPads() if pad.HasHole()]
    # Get the silkscreen drawings
    dwgs_all = [dwg for dwg in pcb.GetDrawings() if isSilkscreen(dwg)]
    # Get solder mask
    mask_all = [dwg for dwg in pcb.GetDrawings() if dwg.IsOnLayer(pcbnew.F_Mask) or dwg.IsOnLayer(pcbnew.B_Mask)]
    # Get footprints
    fp_all = [fp for fp in pcb.GetFootprints()]
    # Get board outline
    board_edge = SHAPE_POLY_SET()
    pcb.GetBoardPolygonOutlines(board_edge)

    if debug:
        import timeit
        starttime = timeit.default_timer()

    nb_total = 0
    nb_moved = 0

    # Loop over each component of the PCB
    for fp in fp_all:
        if only_process_selection and not fp.IsSelected():
            continue

        ref = fp.Reference()
        if not isSilkscreen(ref): continue

        ref_bb = ref.GetBoundingBox()
        fp_bb = fp.GetBoundingBox(False,False)
        nb_total += 1

        max_fp_size = max(fp_bb.GetWidth(),fp_bb.GetHeight()) + max(ref_bb.GetWidth(),ref_bb.GetHeight()) + max_offset_units

        # Filter the vias
        vias = filter_distance(ref_bb.GetCenter(), max_fp_size, vias_all)

        # Filter footprints
        modules =  filter_distance(ref_bb.GetCenter(), max_fp_size, fp_all)

        # Filter THT pads
        tht_pads =  filter_distance(ref_bb.GetCenter(), max_fp_size, tht_pads_all)

        # if not IGNORE_ALREADY_VALID and isPositionValid(ref, modules, board_edge, vias, tht_pads): continue

        # Sweep positions
        initial_pos = ref.GetPosition()
        try:
            for i in decimal_range(0, max_offset_units, step_units):
                # Sweep x coords: top (left/right from center), bottom (left/right from center)
                for j in decimal_range(0, fp_bb.GetWidth()/2 + i, step_units):
                    ref.SetY(int(fp_bb.GetTop() - ref_bb.GetHeight()/2.0*__deflate_factor__ - i))
                    ref.SetX(int(fp_bb.GetCenter().x - j))
                    if isPositionValid(ref, modules, board_edge, vias, tht_pads): raise StopIteration 

                    ref.SetX(int(fp_bb.GetCenter().x + j))
                    if isPositionValid(ref, modules, board_edge, vias, tht_pads): raise StopIteration 

                    ref.SetY(int(fp_bb.GetBottom() + ref_bb.GetHeight()/2.0*__deflate_factor__ + i))
                    ref.SetX(int(fp_bb.GetCenter().x - j))
                    if isPositionValid(ref, modules, board_edge, vias, tht_pads): raise StopIteration 

                    ref.SetX(int(fp_bb.GetCenter().x + j))
                    if isPositionValid(ref, modules, board_edge, vias, tht_pads): raise StopIteration 

                # Sweep y coords: left (top/bot from center), right (top/bot from center)
                for j in decimal_range(0, fp_bb.GetHeight()/2 + i, step_units):
                    ref.SetX(int(fp_bb.GetLeft() - ref_bb.GetWidth()/2.0*__deflate_factor__ - i))
                    ref.SetY(int(fp_bb.GetCenter().y - j))
                    if isPositionValid(ref, modules, board_edge, vias, tht_pads): raise StopIteration 

                    ref.SetY(int(fp_bb.GetCenter().y + j))
                    if isPositionValid(ref, modules, board_edge, vias, tht_pads): raise StopIteration 

                    ref.SetX(int(fp_bb.GetRight() + ref_bb.GetWidth()/2.0*__deflate_factor__ + i))
                    ref.SetY(int(fp_bb.GetCenter().y - j))
                    if isPositionValid(ref, modules, board_edge, vias, tht_pads): raise StopIteration 

                    ref.SetY(int(fp_bb.GetCenter().y + j))
                    if isPositionValid(ref, modules, board_edge, vias, tht_pads): raise StopIteration 
            # Reset to initial position if not able to be moved
            ref.SetPosition(initial_pos)
            log("{} couldn't be moved".format(str(fp.GetReference())))
        except StopIteration:
            log("{} moved to ({:.2f},{:.2f})".format(str(fp.GetReference()), ToUserUnit(ref.GetPosition().x), ToUserUnit(ref.GetPosition().y)))
            nb_moved += 1

    if debug:
        log("Execution time is {:.2f}s".format(timeit.default_timer() - starttime))
    log('Finished ({}/{} moved)'.format(nb_moved,nb_total))

class AutoSilkscreenPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = u"AutoSilkscreen"
        self.category = u"Modify PCB"
        self.description = u"Moves silkscreen"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'logo.png')

    def Run(self):
        dialog = auto_silkscreen_dialog.AutoSilkscreenDialog(None)
        modal_result = dialog.ShowModal()
        if modal_result == wx.ID_OK:
            try:
                max_d = float(dialog.m_maxDistance.GetValue().replace(',', '.'))
                step_size = float(dialog.m_stepSize.GetValue().replace(',', '.'))
                if max_d <= 0 or step_size <= 0:
                    raise ValueError
                optimize(max_d, step_size, dialog.m_onlyProcessSelection.IsChecked())
            except ValueError:
                wx.MessageBox("Invalid value entered.")
        dialog.Destroy()
            