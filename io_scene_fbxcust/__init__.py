# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8-80 compliant>

bl_info = {
    "name": "Autodesk FBX format Customized",
    "author": "Campbell Barton / modified by isathar",
    "blender": (2, 68, 0),
    "location": "File > Import-Export",
    "description": "Same as 2.68 fbx exporter "
                   "modified to include custom vertex normals and smoothing groups",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"}


if "bpy" in locals():
    import imp
    if "export_fbx" in locals():
        imp.reload(export_fbx)


import bpy
from bpy.props import (StringProperty,
                       BoolProperty,
                       FloatProperty,
                       EnumProperty,
                       )

from bpy_extras.io_utils import (ExportHelper,
                                 path_reference_mode,
                                 axis_conversion,
                                 )


class ExportFBX(bpy.types.Operator, ExportHelper):
    """Selection to an ASCII Autodesk FBX"""
    bl_idname = "export_scene2.fbx"
    bl_label = "Export FBX"
    bl_options = {'PRESET'}

    filename_ext = ".fbx"
    filter_glob = StringProperty(default="*.fbx", options={'HIDDEN'})

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    object_types = EnumProperty(
            name="Object Types",
            options={'ENUM_FLAG'},
            items=(('EMPTY', "Empty", ""),
                   ('CAMERA', "Camera", ""),
                   ('LAMP', "Lamp", ""),
                   ('ARMATURE', "Armature", ""),
                   ('MESH', "Mesh", ""),
                   ),
            default={'ARMATURE', 'MESH'},
            )
    global_scale = FloatProperty(
            name="Scale",
            description=("Scale all data "
                         "(Some importers do not support scaled armatures!)"),
            min=0.01, max=1000.0,
            soft_min=0.01, soft_max=1000.0,
            default=1.0,
            )
    use_selection = BoolProperty(
            name="Selected Objects",
            description="Export selected objects on visible layers",
            default=True,
            )
    use_mesh_modifiers = BoolProperty(
            name="Apply Modifiers",
            description="Apply modifiers to mesh objects",
            default=False,
            )
    axis_setting = EnumProperty(
            name="Axis Flip",
            items=(('SKELMESH', "Skeletal Mesh", "Z Up, Y Forward"),
                   ('STATICMESH', "Static Mesh", "Default (Y Up, -Z Forward)"),
                   ),
            default='STATICMESH',
            )

    mesh_smooth_type = EnumProperty(
            name="Smoothing",
            items=(('OFF', "Off", "Don't write smoothing"),
                   ('GROUPS', "Groups", "Write smoothing groups"),
                   ('FACE', "Face", "Write face smoothing"),
                   ('EDGE', "Edge", "Write edge smoothing"),
                   ),
            default='FACE',
            )
    normals_export_mode = EnumProperty(
            name="Normals",
            items=(('AUTO', "Default", "Let Blender generate normals"),
                   ('EDGES', "Sharp Edges", "Generate split normals from sharp edges (buggy/wip)"),
                   ('SGROUPS', "Smoothing Groups", "Generate normals from smoothing groups"),
                   ('C_ASDN', "asdn's Addon", "write normals from Recalc Vertex Normals script"),
                   ),
            default='AUTO',
            )
    export_tangents = BoolProperty(
            name="Tangents + Binormals",
            description="Calculate and save tangents and binormals",
            default=True,
            )
    use_armature_deform_only = BoolProperty(
            name="Only Deform Bones",
            description="Only write deforming bones",
            default=False,
            )
    use_anim = BoolProperty(
            name="Include Animation",
            description="Export keyframe animation",
            default=False,
            )
    use_anim_action_all = BoolProperty(
            name="All Actions",
            description=("Export all actions for armatures or just the "
                         "currently selected action"),
            default=False,
            )
    use_default_take = BoolProperty(
            name="Include Default Take",
            description=("Export currently assigned object and armature "
                         "animations into a default take from the scene "
                         "start/end frames"),
            default=False
            )
    use_anim_optimize = BoolProperty(
            name="Optimize Keyframes",
            description="Remove double keyframes",
            default=False,
            )
    anim_optimize_precision = FloatProperty(
            name="Precision",
            description=("Tolerance for comparing double keyframes "
                        "(higher for greater accuracy)"),
            min=1, max=16,
            soft_min=1, soft_max=16,
            default=6.0,
            )

    #hidden options
    use_mesh_edges = BoolProperty(
            name="Include Edges",
            description=("Edges may not be necessary, can cause import "
                         "pipeline errors with XNA"),
            default=False,
            options={'HIDDEN'},
            )
    batch_mode = EnumProperty(
            name="Batch Mode",
            items=(('OFF', "Off", "Active scene to file"),
                   ('SCENE', "Scene", "Each scene as a file"),
                   ('GROUP', "Group", "Each group as a file"),
                   ),
            options={'HIDDEN'},
            )
    use_batch_own_dir = BoolProperty(
            name="Batch Own Dir",
            description="Create a dir for each exported file",
            default=True,
            options={'HIDDEN'},
            )
    path_mode = path_reference_mode

    
    @property
    def check_extension(self):
        return self.batch_mode == 'OFF'

    def check(self, context):
        is_def_change = super().check(context)
        return (is_def_change)

    def execute(self, context):
        from mathutils import Matrix
        if not self.filepath:
            raise Exception("filepath not set")

        axis_up = 'Y'
        axis_forward = '-Z'

        if self.axis_setting == 'SKELMESH':
            axis_up = 'Z'
            axis_forward = 'Y'

        global_matrix = Matrix()

        global_matrix[0][0] = \
        global_matrix[1][1] = \
        global_matrix[2][2] = self.global_scale

        global_matrix = (global_matrix *
                         axis_conversion(to_forward=axis_forward,
                                         to_up=axis_up,
                                         ).to_4x4())

        keywords = self.as_keywords(ignore=("global_scale",
                                            "check_existing",
                                            "filter_glob",
                                            ))

        keywords["global_matrix"] = global_matrix

        from . import export_fbx
        return export_fbx.save(self, context, **keywords)


def menu_func(self, context):
    self.layout.operator(ExportFBX.bl_idname, text="Autodesk FBX Custom (.fbx)")


def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_export.append(menu_func)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()
