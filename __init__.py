bl_info = {
    "name": "Display Volume Meter",
    "author": "SNU, tintwotin",
    "version": (1, 0),
    "blender": (3, 40, 0),
    "location": "Time Editor > Header",
    "description": "Displays the current volume of the VSE sequence at the current frame",
    "category": "Sequencer"
}

import bpy
# source: https://github.com/snuq/VSEQF/
# The main functions are made by SNU for his VSEQF, this is just a simple implementation of a volume meter which shows up in the Timeline editor.

def get_fade_curve(context, sequence, create=False):
    #Returns the fade curve for a given sequence.  If create is True, a curve will always be returned, if False, None will be returned if no curve is found.
    if sequence.type == 'SOUND':
        fade_variable = 'volume'
    else:
        fade_variable = 'blend_alpha'

    #Search through all curves and find the fade curve
    animation_data = context.scene.animation_data
    if not animation_data:
        if create:
            context.scene.animation_data_create()
            animation_data = context.scene.animation_data
        else:
            return None
    action = animation_data.action
    if not action:
        if create:
            action = bpy.data.actions.new(sequence.name+'Action')
            animation_data.action = action
        else:
            return None

    all_curves = action.fcurves
    fade_curve = None  #curve for the fades
    for curve in all_curves:
        if curve.data_path == 'sequence_editor.sequences_all["'+sequence.name+'"].'+fade_variable:
            #keyframes found
            fade_curve = curve
            break

    #Create curve if needed
    if fade_curve is None and create:
        fade_curve = all_curves.new(data_path=sequence.path_from_id(fade_variable))

        #add a single keyframe to prevent blender from making the waveform invisible (bug)
        if sequence.type == 'SOUND':
            value = sequence.volume
        else:
            value = sequence.blend_alpha
        fade_curve.keyframe_points.add(1)
        point = fade_curve.keyframe_points[0]
        point.co = (sequence.frame_final_start, value)

    return fade_curve


def get_sequence_volume(frame=None):
    
    total = 0

    if bpy.context.scene.sequence_editor is None:
        return 0
    
    sequences = bpy.context.scene.sequence_editor.sequences_all
    depsgraph = bpy.context.evaluated_depsgraph_get()
    
    if frame is None:
        frame = bpy.context.scene.frame_current
        evaluate_volume = False
    else:
        evaluate_volume = True

    fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base

    for sequence in sequences:

        if (sequence.type=="SOUND" and sequence.frame_final_start<frame and sequence.frame_final_end>frame and not sequence.mute):
           
            time_from = (frame - 1 - sequence.frame_start) / fps
            time_to = (frame - sequence.frame_start) / fps

            audio = sequence.sound.evaluated_get(depsgraph).factory

            chunk = audio.limit(time_from, time_to).data()
            #sometimes the chunks cannot be read properly, try to read 2 frames instead
            if (len(chunk)==0):
                time_from_temp = (frame - 2 - sequence.frame_start) / fps
                chunk = audio.limit(time_from_temp, time_to).data()
            #chunk still couldnt be read... just give up :\
            if (len(chunk)==0):
                average = 0

            else:
                cmax = abs(chunk.max())
                cmin = abs(chunk.min())
                if cmax > cmin:
                    average = cmax
                else:
                    average = cmin

            if evaluate_volume:
                fcurve = get_fade_curve(bpy.context, sequence, create=False)
                if fcurve:
                    volume = fcurve.evaluate(frame)
                else:
                    volume = sequence.volume
            else:
                volume = sequence.volume

            total = total + (average * volume)
        
        continue 

    return total



def update_volume(self, context):

    scene = context.scene
    if scene.old_frame != scene.frame_current:
        scene.volume = get_sequence_volume(scene.frame_current)
        scene.old_frame = scene.frame_current


def draw_volume_slider(self, context):
    layout = self.layout
    scene = context.scene
    if scene.volume > 1:
        vu_icon = "OUTLINER_OB_SPEAKER"
    else: 
        vu_icon = "OUTLINER_DATA_SPEAKER"
    layout.separator()
    layout = layout.box()
    layout.scale_y = 1.2
    layout.scale_x = 1.2
    row = layout.row(align=True)
    row.label(text="", icon= vu_icon)
    row.scale_y = .8
    row.prop(scene, "volume", text="                          ", slider=True, icon = vu_icon)


def register():
    bpy.types.Scene.old_frame = bpy.props.IntProperty( name="Old Frame", default=0, min=0, max=100000000)
    bpy.types.Scene.volume = bpy.props.FloatProperty(
        name="Volume", default=0.0, min=-0.0, max=2.0, precision = 2)
    bpy.types.TIME_MT_editor_menus.append(draw_volume_slider)
    bpy.app.handlers.frame_change_post.append(update_volume)


def unregister():
    bpy.types.TIME_MT_editor_menus.remove(draw_volume_slider)
    bpy.app.handlers.frame_change_post.remove(update_volume)
    del bpy.types.Scene.volume
    del bpy.types.Scene.old_frame


if __name__ == "__main__":
    register()
