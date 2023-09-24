import os
import bpy
import math
import shutil
import platform
import json

platform = platform.system()

class RenderSpriteSheet(bpy.types.Operator):
    """Operator used to render sprite sheets for an object"""
    bl_idname = "spritesheets.render"
    bl_label = "Render Sprite Sheets"
    bl_description = "Renders all actions to a single sprite sheet"

    def execute(self, context):
        scene = bpy.context.scene
        props = scene.SpriteSheetPropertyGroup
        progressProps = scene.ProgressPropertyGroup
        progressProps.rendering = True
        progressProps.success = False
        progressProps.actionTotal = len(bpy.data.actions)

        animation_descs = []
        frame_end = 0

        objectToRender = props.target
        for index, action in enumerate(bpy.data.actions):
            progressProps.actionName = action.name
            progressProps.actionIndex = index
            objectToRender.animation_data.action = action

            count, _, _ = frame_count(action.frame_range)
            frame_end += count
            animation_descs.append({
                "name": action.name,
                "end": frame_end,
            })

            self.processAction(action, scene, props,
                               progressProps, objectToRender)

        combine_images(bpy.path.abspath(props.outputPath), bpy.path.abspath(os.path.join(props.outputPath, objectToRender.name + ".png")))

        json_info = {
            "name": objectToRender.name,
            "tileWidth": props.tileSize[0],
            "tileHeight": props.tileSize[1],
            "frameRate": props.fps,
            "animations": animation_descs,
        }

        with open(bpy.path.abspath(os.path.join(props.outputPath, objectToRender.name + ".bss")), "w") as f:
            json.dump(json_info, f, indent='\t')

        progressProps.rendering = False
        progressProps.success = True
        shutil.rmtree(bpy.path.abspath(os.path.join(props.outputPath, "temp")))
        return {'FINISHED'}


    def processAction(self, action, scene, props, progressProps, objectToRender):
        """Processes a single action by iterating through each frame and rendering tiles to a temp folder"""
        frameRange = action.frame_range
        frameCount, frameMin, frameMax = frame_count(frameRange)
        progressProps.tileTotal = frameCount
        actionPoseMarkers = action.pose_markers
        if props.onlyRenderMarkedFrames is True and actionPoseMarkers is not None and len(actionPoseMarkers.keys()) > 0:
            for marker in actionPoseMarkers.values():
                progressProps.tileIndex = marker.frame
                scene.frame_set(marker.frame)
                # TODO: Unfortunately Blender's rendering happens on the same thread as the UI and freezes it while running,
                # eventually they may fix this and then we can leverage some of the progress information we track
                bpy.ops.spritesheets.render_tile('EXEC_DEFAULT')
        else:
            for index in range(frameMin, frameMax + 1):
                progressProps.tileIndex = index
                scene.frame_set(index)
                # TODO: Unfortunately Blender's rendering happens on the same thread as the UI and freezes it while running,
                # eventually they may fix this and then we can leverage some of the progress information we track
                bpy.ops.spritesheets.render_tile('EXEC_DEFAULT')


def frame_count(frame_range):
    frameMin = math.floor(frame_range[0])
    frameMax = math.ceil(frame_range[1])
    return (frameMax - frameMin, frameMin, frameMax)


def combine_images(root, output_path):
    """Combines all images in the temp folder into a single sprite sheet"""
    images_path = os.path.join(root, 'temp')
    images = []
    for file in os.listdir(images_path):
        if file.endswith(".png"):
            images.append(os.path.join(images_path, file))

    images.sort()
    if len(images) == 0:
        return

    first_image = images[0]
    first_image_name = os.path.basename(first_image)
    first_image_name = first_image_name[:first_image_name.rfind("_")]
    first_image_name = first_image_name[:first_image_name.rfind("0")]

    first_image = bpy.data.images.load(first_image)
    first_image.pack()

    width = first_image.size[0]
    height = first_image.size[1]

    sprite_sheet = bpy.data.images.new(
        first_image_name, width=width * len(images), height=height)
    index = 0
    copy_area(first_image, sprite_sheet, index, len(images))

    for index, image in enumerate(images[1:]):
        image = bpy.data.images.load(image)
        image.pack()
        copy_area(image, sprite_sheet, index + 1, len(images))

    sprite_sheet.file_format = 'PNG'
    sprite_sheet.filepath_raw = os.path.join(output_path)
    sprite_sheet.save()

def copy_area(source, destination, index, number_of_images):
    """Copies the contents of one image to another"""
    width = source.size[0]
    height = source.size[1]
    offset_x = index * width
    for row in range(height):
        destination.pixels[row * (number_of_images * width * 4) + offset_x * 4:row * (number_of_images * width * 4) + offset_x * 4 + width * 4] = source.pixels[row * (width * 4):row * (width * 4) + width * 4]
