from maya import mel, cmds
from functools import wraps

# Logging setup ====================================================== #

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.WARNING)

# Decorators ========================================================= #

def viewport_off(func):
    """
    Decorator - turn off Maya display while func is running. 
    If func fails, the error will be raised after.
    """
    @wraps(func)
    def wrap( *args, **kwargs ):
        
        parallel = False
        maya_version = mel.eval("$mayaVersion = `getApplicationVersionAsFloat`")
        if maya_version >= 2016:
            if 'parallel' in cmds.evaluationManager(q=True, mode=True):
                cmds.evaluationManager(mode='off')
                parallel = True
                log.info("Turning off Parallel evaluation...")
        # Turn $gMainPane Off:
        mel.eval("paneLayout -e -manage false $gMainPane")
        cmds.refresh(suspend=True)
        # THIS IS THE CULPRIT - Hide this Timeslider!
        mel.eval("setTimeSliderVisible 0;")


        # Decorator will try/except running the function.
        # But it will always turn on the viewport at the end.
        # In case the function failed, it will prevent leaving maya viewport off.
        try:
            return func( *args, **kwargs )
        except Exception:
            raise # will raise original error
        finally:
            cmds.refresh(suspend=False)
            mel.eval("setTimeSliderVisible 1;")
            if parallel:
                cmds.evaluationManager(mode='parallel')
                log.info("Turning on Parallel evaluation...")
            mel.eval("paneLayout -e -manage true $gMainPane")
            cmds.refresh()

    return wrap


# Private methods ===================================================== #

def _get_animLayers_from_nodes(nodes):
    '''
    return all animLayers associated with the given nodes
    '''
    if not isinstance(nodes, list):
        # This is a hack as the cmds.animLayer call is CRAP. It doesn't mention
        # anywhere in the docs that you can even pass in Maya nodes, yet alone
        # that it has to take a list of nodes and fails with invalid flag if not
        nodes = [nodes]
    return cmds.animLayer(nodes, q=True, affectedLayers=True)


# Public methods ====================================================== #

@viewport_off
def merge_animLayers(delete_baked=True):
    '''
    from the given nodes find, merge and remove any animLayers found
    '''
    root_layer = cmds.animLayer(query=True, root=True) or []
    if not root_layer:
        log.warning("BaseAnimation not found!")
        return

    # Check to see if any layers are selected directly
    animLayers = cmds.treeView("AnimLayerTabanimLayerEditor", q=True, selectItem=True) or []
    
    # Based on selection
    if not animLayers:
        animLayers = _get_animLayers_from_nodes(cmds.ls(sl=1))
    
    if len(animLayers) == 1 and root_layer not in animLayers:
        animLayers.insert(0, root_layer)

    if animLayers:
        try:
            # deal with Maya's optVars for animLayers as the call that sets the defaults
            # for these, via the UI call, is a local proc to the performAnimLayerMerge.
            delete_merged = True
            if cmds.optionVar(exists='animLayerMergeDeleteLayers'):
                delete_merged = cmds.optionVar(query='animLayerMergeDeleteLayers')
            cmds.optionVar(intValue=('animLayerMergeDeleteLayers', delete_baked))

            if not cmds.optionVar(exists='animLayerMergeByTime'):
                cmds.optionVar(floatValue=('animLayerMergeByTime', 1.0))
            
            # Use the maya built-in magic
            mel.eval('animLayerMerge {"%s"}' % '","'.join(animLayers))

        except:
            log.warning('animLayer Merge failed!')
        finally:
            cmds.optionVar(intValue=('animLayerMergeDeleteLayers', delete_merged))
    return 'Merged_Layer'

# Public call ========================================================= #

def run():
    merge_animLayers()

