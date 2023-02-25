import os
import pcbnew
import gettext
import wx, math

from pcbnew import VECTOR2I

from . import auto_silkscreen_dialog

# TODO
# * Handle Solder Mask collision
# * Handle Drawings collision
# * Optimization: sort items in quads, only look for neighboring quads.
# * Value on the SS instead of Fab layers
# * Reduce text size

# This factor reduces the size of the effective bounding box of the silkscreen to determine collision.
__deflate_factor__ = 0.9

IGNORE_ALREADY_VALID = False

def isSilkscreen(item):
    """Checks if an item is a visible silkscreen item."""
    if item is None:
        return False
    elif not (item.IsOnLayer(pcbnew.B_SilkS) or item.IsOnLayer(pcbnew.F_SilkS)):    
        return False
    elif hasattr(item, 'IsVisible'):
        if not item.IsVisible():
            return False
    return True

def log_debug(msg):
    wx.LogMessage(str(msg))

def distance(a, b):
    """Compute the distance between two points."""
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

def BB_in_SHAPE_POLY_SET(bb,poly,all_in=False):
    """Checks if a BOX2I is contained in a SHAPE_POLY_SET."""
    if all_in:
        return poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetTop())) and poly.Contains(VECTOR2I(bb.GetRight(),bb.GetTop())) and poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetBottom())) and poly.Contains(VECTOR2I(bb.GetRight(),bb.GetBottom())) and poly.Contains(VECTOR2I(bb.GetCenter().x,bb.GetCenter().y))
    return poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetTop())) or poly.Contains(VECTOR2I(bb.GetRight(),bb.GetTop())) or poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetBottom())) or poly.Contains(VECTOR2I(bb.GetRight(),bb.GetBottom())) or poly.Contains(VECTOR2I(bb.GetCenter().x,bb.GetCenter().y))

class AutoSilkscreen:
    def __init__(self):
        self.pcb(pcbnew.GetBoard())
        self.max_offset_units = self.set_max_offset_units(3)
        self.step_units = self.set_step_units(0.25)
        self.debug = False

    def set_max_offset_units(self, max_offset_units : float):
        self.max_offset_units = pcbnew.FromMM(max_offset_units)

    def set_step_units(self, step_units : float):
        self.step_units = pcbnew.FromMM(step_units)

    def set_only_process_selection(self, only_process_selection : bool):
        self.only_process_selection = only_process_selection

    def set_debug(self, debug : bool):
        self.debug = debug


def isPositionValid(item, fp_item, modules, board_edge, vias, tht_pads, isReference=True):
    """Checks if a reference position is valid, based on:
    * Contained within board edges
    * Not colliding with any via
    * Not colliding with any hole
    * Not colliding with the courtyard of any component on the same side
    """
    bb = item.GetBoundingBox() # BOX2I
    bb.SetSize(int(bb.GetWidth()*__deflate_factor__),int(bb.GetHeight()*__deflate_factor__))

    # Check if ref is inside PCB outline
    if not BB_in_SHAPE_POLY_SET(bb, board_edge, True):
        return False

    # Check if ref is colliding with any FP
    for fp in modules:
        # Collides with Ctyd
        fp_shape = fp.GetCourtyard(item.GetLayer()) # SHAPE_POLY_SET
        if BB_in_SHAPE_POLY_SET(bb, fp_shape):
            return False

        # Collides with Reference TODO: algo improvement nudge it?
        ref = fp.Reference()
        if ((isReference and fp_item != fp) or not isReference) and isSilkscreen(ref) and ref.IsOnLayer(item.GetLayer()) and bb.Intersects(ref.GetBoundingBox()):
            return False

        # Collides with value field (if it is on the silkscreen)
        value = fp.Value()
        if isSilkscreen(value) and ((not isReference and fp_item != fp) or isReference) and value.IsOnLayer(item.GetLayer()) and bb.Intersects(value.GetBoundingBox()):
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

    # TODO Check if ref is colliding with any drawings
    # TODO Check if ref is colliding with any solder mask
    return True

def filter_distance(item_center, max_d, list_items):
    """Filters a list of items based on the distance to a point."""
    filtered_items = []
    for i in list_items:
        max_i_size = math.hypot(i.GetBoundingBox().GetHeight(), i.GetBoundingBox().GetWidth())
        if distance(item_center,i.GetBoundingBox().GetCenter()) < max_d + max_i_size:
            filtered_items.append(i)
    return filtered_items

def sweep(isReference, fp, max_offset_units, step_units, modules, board_edge, vias, tht_pads,debug=False):
    if isReference:
        item = fp.Reference()
    else:
        item = fp.Value()

    initial_pos = item.GetPosition()
    fp_bb = fp.GetBoundingBox(False,False)
    item_bb = item.GetBoundingBox()
    # if not IGNORE_ALREADY_VALID and isPositionValid(item, fp, modules, board_edge, vias, tht_pads, isReference): return 0

    try:
        for i in range(0, max_offset_units, step_units):
            # Sweep x coords: top (left/right from center), bottom (left/right from center)
            for j in range(0, int(fp_bb.GetWidth()/2 + i), step_units):
                item.SetY(int(fp_bb.GetTop() - item_bb.GetHeight()/2.0*__deflate_factor__ - i))
                item.SetX(int(fp_bb.GetCenter().x - j))
                if isPositionValid(item, fp, modules, board_edge, vias, tht_pads, isReference): raise StopIteration 

                item.SetX(int(fp_bb.GetCenter().x + j))
                if isPositionValid(item, fp, modules, board_edge, vias, tht_pads, isReference): raise StopIteration 

                item.SetY(int(fp_bb.GetBottom() + item_bb.GetHeight()/2.0*__deflate_factor__ + i))
                item.SetX(int(fp_bb.GetCenter().x - j))
                if isPositionValid(item, fp, modules, board_edge, vias, tht_pads, isReference): raise StopIteration 

                item.SetX(int(fp_bb.GetCenter().x + j))
                if isPositionValid(item, fp, modules, board_edge, vias, tht_pads, isReference): raise StopIteration 

            # Sweep y coords: left (top/bot from center), right (top/bot from center)
            for j in range(0, int(fp_bb.GetHeight()/2 + i), step_units):
                item.SetX(int(fp_bb.GetLeft() - item_bb.GetWidth()/2.0*__deflate_factor__ - i))
                item.SetY(int(fp_bb.GetCenter().y - j))
                if isPositionValid(item, fp, modules, board_edge, vias, tht_pads, isReference): raise StopIteration 

                item.SetY(int(fp_bb.GetCenter().y + j))
                if isPositionValid(item, fp, modules, board_edge, vias, tht_pads, isReference): raise StopIteration 

                item.SetX(int(fp_bb.GetRight() + item_bb.GetWidth()/2.0*__deflate_factor__ + i))
                item.SetY(int(fp_bb.GetCenter().y - j))
                if isPositionValid(item, fp, modules, board_edge, vias, tht_pads, isReference): raise StopIteration 

                item.SetY(int(fp_bb.GetCenter().y + j))
                if isPositionValid(item, fp, modules, board_edge, vias, tht_pads, isReference): raise StopIteration 
        # Reset to initial position if not able to be moved
        item.SetPosition(initial_pos)
        if debug:
            log_debug("{} couldn't be moved".format(str(fp.GetReference())))
        return 0
    except StopIteration:
        if debug:
            log_debug("{} moved to ({:.2f},{:.2f})".format(str(fp.GetReference()), pcbnew.ToMM(item.GetPosition().x), pcbnew.ToMM(item.GetPosition().y)))
        return 1

def optimize(max_offset,step,only_process_selection,debug=False):
    pcb = pcbnew.GetBoard()

    step_units = pcbnew.FromMM(step)
    max_offset_units = pcbnew.FromMM(max_offset)

    # Get PCB collision items
    # Get the vias (except buried vias)
    vias_all = [trk for trk in pcb.Tracks() if  isinstance(trk,pcbnew.PCB_VIA) and (trk.TopLayer() == pcbnew.F_Cu or trk.BottomLayer() == pcbnew.B_Cu)]
    # Get the PTH/NPTH pads
    tht_pads_all = [pad for pad in pcb.GetPads() if pad.HasHole()]
    # Get the silkscreen drawings
    dwgs_all = [dwg for dwg in pcb.GetDrawings() if isSilkscreen(dwg)]
    # Get solder mask
    mask_all = [dwg for dwg in pcb.GetDrawings() if dwg.IsOnLayer(pcbnew.F_Mask) or dwg.IsOnLayer(pcbnew.B_Mask)]
    # Get footprints
    fp_all = [fp for fp in pcb.GetFootprints()]
    # Get board outline
    board_edge = pcbnew.SHAPE_POLY_SET()
    pcb.GetBoardPolygonOutlines(board_edge)

    if debug:
        import timeit
        starttime = timeit.default_timer()

    nb_total = 0
    nb_moved = 0

    # Loop over each component of the PCB
    for fp in fp_all:
        # Check if the FP should processed
        if only_process_selection and not fp.IsSelected(): continue

        value = fp.Value()
        ref = fp.Reference()

        # Check if there is anything to move
        if not isSilkscreen(ref) and not isSilkscreen(value): continue

        fp_bb = fp.GetBoundingBox(False,False)
        ref_bb = ref.GetBoundingBox()
        value_bb = value.GetBoundingBox()        
        
        max_fp_size = math.hypot(fp_bb.GetWidth(), fp_bb.GetHeight())/2 + max_offset_units
        if isSilkscreen(ref) and isSilkscreen(value):
            max_fp_size += max(math.hypot(ref_bb.GetWidth(),ref_bb.GetHeight()), math.hypot(value_bb.GetWidth(),value_bb.GetHeight()))/2
        elif isSilkscreen(ref):
            max_fp_size += math.hypot(ref_bb.GetWidth(),ref_bb.GetHeight())/2
        elif isSilkscreen(value):
            max_fp_size += math.hypot(value_bb.GetWidth(),value_bb.GetHeight())/2

        # Filter the vias
        vias = filter_distance(fp_bb.GetCenter(), max_fp_size, vias_all)

        # Filter footprints
        # FIXME does not account for REF/VALUE size!
        modules =  filter_distance(fp_bb.GetCenter(), max_fp_size*2, fp_all)

        # Filter THT pads
        tht_pads =  filter_distance(fp_bb.GetCenter(), max_fp_size, tht_pads_all)

        # Sweep positions
        if isSilkscreen(ref):
            nb_total += 1
            nb_moved += sweep(True, fp, max_offset_units, step_units, modules, board_edge, vias, tht_pads)
        if isSilkscreen(value):
            nb_total += 1
            nb_moved += sweep(False, fp, max_offset_units, step_units, modules, board_edge, vias, tht_pads)

    if debug:
        log_debug("Execution time is {:.2f}s".format(timeit.default_timer() - starttime))
        log_debug('Finished ({}/{} moved)'.format(nb_moved,nb_total))

    return nb_moved, nb_total

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
                nb_moved, nb_total = optimize(max_d, step_size, dialog.m_onlyProcessSelection.IsChecked())
                wx.MessageBox('Successfully moved {}/{} items!'.format(nb_moved,nb_total), 'AutoSilkscreen completed', wx.OK)
            except ValueError:
                wx.MessageBox("Invalid value entered.",'AutoSilkscreen error',wx.ICON_ERROR | wx.OK)
        dialog.Destroy()
            