import os
import pcbnew
import gettext
import wx, math

from pcbnew import VECTOR2I

from . import auto_silkscreen_dialog

# TODO
# * Handle Drawings collision
# * Optimization: sort items in quads, only look for neighboring quads.
# * Reduce text size option

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

def log(msg):
    wx.LogMessage(str(msg))

def BB_in_SHAPE_POLY_SET(bb,poly,all_in=False):
    """Checks if a BOX2I is contained in a SHAPE_POLY_SET."""
    if all_in:
        return poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetTop())) and poly.Contains(VECTOR2I(bb.GetRight(),bb.GetTop())) and poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetBottom())) and poly.Contains(VECTOR2I(bb.GetRight(),bb.GetBottom())) and poly.Contains(VECTOR2I(bb.GetCenter().x,bb.GetCenter().y))
    return poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetTop())) or poly.Contains(VECTOR2I(bb.GetRight(),bb.GetTop())) or poly.Contains(VECTOR2I(bb.GetLeft(),bb.GetBottom())) or poly.Contains(VECTOR2I(bb.GetRight(),bb.GetBottom())) or poly.Contains(VECTOR2I(bb.GetCenter().x,bb.GetCenter().y))

def distance(a, b):
    """Compute the distance between two points."""
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

def filter_distance(item_center, max_d, list_items):
    """Filters a list of items based on the distance to a point."""
    filtered_items = []
    for i in list_items:
        max_i_size = math.hypot(i.GetBoundingBox().GetHeight(), i.GetBoundingBox().GetWidth())
        if distance(item_center,i.GetBoundingBox().GetCenter()) < max_d + max_i_size:
            filtered_items.append(i)
    return filtered_items

class AutoSilkscreen:
    def __init__(self):
        self.pcb = pcbnew.GetBoard()
        self.set_max_allowed_distance(3)
        self.set_step_size(0.25)
        self.set_only_process_selection(False)
        self.set_debug(False)
        self.set_ignore_vias(False)
        self.__deflate_factor__ = 1

    # Setters
    def set_max_allowed_distance(self, max_allowed_distance : float):
        if max_allowed_distance <= 0:
            raise ValueError
        self.max_allowed_distance = pcbnew.FromMM(max_allowed_distance)
        return self
    def set_step_size(self, step_size : float):
        if step_size <= 0:
            raise ValueError
        self.step_size = pcbnew.FromMM(step_size)
        return self
    def set_only_process_selection(self, only_process_selection : bool):
        self.only_process_selection = only_process_selection
        return self
    def set_debug(self, debug : bool):
        self.debug = debug
        return self
    def set_ignore_vias(self, ignore_via : bool):
        self.ignore_via = ignore_via
        return self

    def __isPositionValid(self, item, fp_item, modules, board_edge, vias, tht_pads, masks, drawings, isReference=True):
        """Checks if a reference position is valid, based on:
        * Contained within board edges
        * Not colliding with any via
        * Not colliding with any hole
        * Not colliding with the courtyard of any component
        * Not colliding with the reference of any component
        * Not colliding with the value of any component
        * Not colliding with solder mask
        """
        bb_item = item.GetBoundingBox() # BOX2I
        bb_item.SetSize(int(bb_item.GetWidth()*self.__deflate_factor__),int(bb_item.GetHeight()*self.__deflate_factor__))
        item_shape = item.GetEffectiveShape()

        # Check if ref is inside PCB outline
        if not BB_in_SHAPE_POLY_SET(bb_item, board_edge, True):
            return False

        # Check if ref is colliding with any FP
        for fp in modules:
            # Collides with Ctyd
            fp_shape = fp.GetCourtyard(item.GetLayer()) # SHAPE_POLY_SET
            # if BB_in_SHAPE_POLY_SET(bb_item, fp_shape):
            #     return False
            if fp_shape.Collide(item_shape):
                return False

            # Collides with Reference TODO: algo improvement to nudge it?
            ref_fp = fp.Reference()
            if ((isReference and fp_item != fp) or not isReference) and isSilkscreen(ref_fp) and ref_fp.IsOnLayer(item.GetLayer()) and bb_item.Intersects(ref_fp.GetBoundingBox()):
                return False

            # Collides with value field (if it is on the silkscreen)
            value_fp = fp.Value()
            if isSilkscreen(value_fp) and ((not isReference and fp_item != fp) or isReference) and value_fp.IsOnLayer(item.GetLayer()) and bb_item.Intersects(value_fp.GetBoundingBox()):
                return False

        # Check if ref is colliding with any via
        for via in vias:
            if (via.TopLayer() == pcbnew.F_Cu and item.IsOnLayer(pcbnew.F_SilkS)) or (via.BottomLayer() == pcbnew.B_Cu and item.IsOnLayer(pcbnew.B_SilkS)):
                if bb_item.Intersects(via.GetBoundingBox()):
                    return False

        # Check if ref is colliding with any hole
        for pad in tht_pads:
            if bb_item.Intersects(pad.GetBoundingBox()):
                return False

        # Check if ref is colliding with solder mask
        for mask in masks:
            if (mask.IsOnLayer(pcbnew.F_Mask) and item.IsOnLayer(pcbnew.F_SilkS)) or (mask.IsOnLayer(pcbnew.B_Mask) and item.IsOnLayer(pcbnew.B_SilkS)) and mask.GetEffectiveShape().Collide(item_shape):
                return False

        # Check if ref is colliding with drawings
        for drawing in drawings:
            if drawing.IsOnLayer(item.GetLayer()) and drawing.GetEffectiveShape(item.GetLayer()).Collide(item_shape):
                return False
        return True

    def __search_valid_position(self, isReference, fp, modules, board_edge, vias, tht_pads, masks, dwgs):
        if isReference:
            item = fp.Reference()
        else:
            item = fp.Value()

        initial_pos = item.GetPosition()
        fp_bb = fp.GetBoundingBox(False,False)
        item_bb = item.GetBoundingBox()
        # if self.__isPositionValid(item, fp, modules, board_edge, vias, tht_pads, masks, dwgs, isReference): return 0

        try:
            for i in range(0, self.max_allowed_distance, self.step_size):
                # Sweep x coords: top (left/right from center), bottom (left/right from center)
                for j in range(0, int(fp_bb.GetWidth()/2 + i), self.step_size):
                    item.SetY(int(fp_bb.GetTop() - item_bb.GetHeight()/2.0*self.__deflate_factor__ - i))
                    item.SetX(int(fp_bb.GetCenter().x - j))
                    if self.__isPositionValid(item, fp, modules, board_edge, vias, tht_pads, masks, dwgs, isReference): raise StopIteration 

                    item.SetX(int(fp_bb.GetCenter().x + j))
                    if self.__isPositionValid(item, fp, modules, board_edge, vias, tht_pads, masks, dwgs, isReference): raise StopIteration 

                    item.SetY(int(fp_bb.GetBottom() + item_bb.GetHeight()/2.0*self.__deflate_factor__ + i))
                    item.SetX(int(fp_bb.GetCenter().x - j))
                    if self.__isPositionValid(item, fp, modules, board_edge, vias, tht_pads, masks, dwgs, isReference): raise StopIteration 

                    item.SetX(int(fp_bb.GetCenter().x + j))
                    if self.__isPositionValid(item, fp, modules, board_edge, vias, tht_pads, masks, dwgs, isReference): raise StopIteration 

                # Sweep y coords: left (top/bot from center), right (top/bot from center)
                for j in range(0, int(fp_bb.GetHeight()/2 + i), self.step_size):
                    item.SetX(int(fp_bb.GetLeft() - item_bb.GetWidth()/2.0*self.__deflate_factor__ - i))
                    item.SetY(int(fp_bb.GetCenter().y - j))
                    if self.__isPositionValid(item, fp, modules, board_edge, vias, tht_pads, masks, dwgs, isReference): raise StopIteration 

                    item.SetY(int(fp_bb.GetCenter().y + j))
                    if self.__isPositionValid(item, fp, modules, board_edge, vias, tht_pads, masks, dwgs, isReference): raise StopIteration 

                    item.SetX(int(fp_bb.GetRight() + item_bb.GetWidth()/2.0*self.__deflate_factor__ + i))
                    item.SetY(int(fp_bb.GetCenter().y - j))
                    if self.__isPositionValid(item, fp, modules, board_edge, vias, tht_pads, masks, dwgs, isReference): raise StopIteration 

                    item.SetY(int(fp_bb.GetCenter().y + j))
                    if self.__isPositionValid(item, fp, modules, board_edge, vias, tht_pads, masks, dwgs, isReference): raise StopIteration 
            # Reset to initial position if not able to be moved
            item.SetPosition(initial_pos)
            if self.debug:
                log("{} couldn't be moved".format(str(fp.GetReference())))
            return 0
        except StopIteration:
            if self.debug:
                log("{} moved to ({:.2f},{:.2f})".format(str(fp.GetReference()), pcbnew.ToMM(item.GetPosition().x), pcbnew.ToMM(item.GetPosition().y)))
            return 1

    def run(self):
        # Get PCB collision items
        # Get the vias (except buried vias)
        vias_all = [trk for trk in self.pcb.Tracks() if not self.ignore_via and isinstance(trk,pcbnew.PCB_VIA) and (trk.TopLayer() == pcbnew.F_Cu or trk.BottomLayer() == pcbnew.B_Cu)]
        # Get the PTH/NPTH pads
        tht_pads_all = [pad for pad in self.pcb.GetPads() if pad.HasHole()]
        # Get the silkscreen drawings
        try:
            dwgs_all = [dwg for dwg in self.pcb.GetDrawings() if isSilkscreen(dwg)]
        except:
            dwgs_all = []
        # Get solder mask
        try:
            mask_all = [dwg for dwg in self.pcb.GetDrawings() if dwg.IsOnLayer(pcbnew.F_Mask) or dwg.IsOnLayer(pcbnew.B_Mask)]
        except:
            mask_all = []
        # Get footprints
        fp_all = [fp for fp in self.pcb.GetFootprints()]
        # Get board outline
        board_edge = pcbnew.SHAPE_POLY_SET()
        self.pcb.GetBoardPolygonOutlines(board_edge)

        if self.debug:
            import timeit
            starttime = timeit.default_timer()

        nb_total = 0
        nb_moved = 0

        # Loop over each component of the PCB
        for fp in fp_all:
            # Check if the FP should processed
            if self.only_process_selection and not fp.IsSelected(): continue

            value = fp.Value()
            ref = fp.Reference()

            # Check if there is anything to move
            if not isSilkscreen(ref) and not isSilkscreen(value): continue

            fp_bb = fp.GetBoundingBox(False,False)
            ref_bb = ref.GetBoundingBox()
            value_bb = value.GetBoundingBox()        
            
            max_fp_size = math.hypot(fp_bb.GetWidth(), fp_bb.GetHeight())/2 + self.max_allowed_distance
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
            modules =  filter_distance(fp_bb.GetCenter(), max_fp_size, fp_all)
            # Filter THT pads
            tht_pads =  filter_distance(fp_bb.GetCenter(), max_fp_size, tht_pads_all)
            # Filter solder mask
            masks = filter_distance(fp_bb.GetCenter(), max_fp_size, mask_all)
            # Filter drawings
            dwgs = filter_distance(fp_bb.GetCenter(), max_fp_size, dwgs_all)

            # Sweep positions
            if isSilkscreen(ref):
                nb_total += 1
                nb_moved += self.__search_valid_position(True, fp, modules, board_edge, vias, tht_pads, masks, dwgs)
            if isSilkscreen(value):
                nb_total += 1
                nb_moved += self.__search_valid_position(False, fp, modules, board_edge, vias, tht_pads, masks, dwgs)

        if self.debug:
            log("Execution time is {:.2f}s".format(timeit.default_timer() - starttime))
            log('Finished ({}/{} moved)'.format(nb_moved,nb_total))

        return nb_moved, nb_total

class AutoSilkscreenPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = u"AutoSilkscreen"
        self.category = u"Modify PCB"
        self.description = u"Automatically moves the silkscreen reference designators to prevent overlap"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'logo.png')

    def Run(self):
        dialog = auto_silkscreen_dialog.AutoSilkscreenDialog(None)
        modal_result = dialog.ShowModal()
        if modal_result == wx.ID_OK:
            try:
                a = AutoSilkscreen()
                a.set_step_size(float(dialog.m_stepSize.GetValue().replace(',', '.')))
                a.set_max_allowed_distance(float(dialog.m_maxDistance.GetValue().replace(',', '.')))
                a.set_only_process_selection(dialog.m_onlyProcessSelection.IsChecked())
                a.set_ignore_vias(dialog.m_silkscreenOnVia.IsChecked())
                
                nb_moved, nb_total = a.run()
                wx.MessageBox('Successfully moved {}/{} items!'.format(nb_moved,nb_total), 'AutoSilkscreen completed', wx.OK)
            except ValueError:
                wx.MessageBox("Invalid value entered.",'AutoSilkscreen error',wx.ICON_ERROR | wx.OK)
        dialog.Destroy()
            