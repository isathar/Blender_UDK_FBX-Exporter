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

# NOTES:
#
# based on the fbx export script included in < v2.68 
# original script created by and copyright (c) Campbell Barton
#
# Changes:
# - tangent + binormal calculation based on Lengyel's Method with support for quads
# - custom normals and smoothing groups support
# - Normals are exported as PerPolyVertex
# - list lookup speed optimizations
# - XNA tweaks disabled for now
# - optional support for asdn's Recalc Vertex Normals addon
#
#  UDK-specific:
# - uses b_root as root bone instead of creating another one
# - axis conversion options altered
# - tangent space very close to UDK's and xNormal's


bl_info = {
	"name": "FBX Custom Exporter UE",
	"author": "Andreas Wiehn (isathar)",
	"version": (1, 0, 0),
	"blender": (2, 70, 0),
	"location": "View3D > Toolbar",
	"description": "Modified FBX 6.1 ASCII exporter from v2.68 tweaked for UDK/UE",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": "Import/Export"}


if "bpy" in locals():
	import imp
	if "export_fbx" in locals():
		imp.reload(export_fbx)

import bpy
from bpy.props import (StringProperty,BoolProperty,IntProperty,FloatProperty,EnumProperty,)
from bpy_extras.io_utils import (ExportHelper,path_reference_mode,axis_conversion,)


class cust_ExportFBX(bpy.types.Operator, ExportHelper):
	bl_idname = "export_scene.fbx_custom"
	bl_label = "Export FBX Custom"
	bl_options = {'PRESET'}
	bl_description = 'Export selection as a .fbx file with customized exporter'
	
	filename_ext = ".fbx"
	filter_glob = StringProperty(default="*.fbx", options={'HIDDEN'})
	
	
	object_types = EnumProperty(
			name="Object Types",
			options={'ENUM_FLAG','HIDDEN'},
			items=(('EMPTY', "Empty", ""),
					('CAMERA', "Camera", ""),
					('LAMP', "Lamp", ""),
					('ARMATURE', "Armature", ""),
					('MESH', "Mesh", "")
					),
			default={'EMPTY','ARMATURE','MESH'}
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
	axis_forward = EnumProperty(
			name="Forward",
			items=(('-Z', "* -Z", ""),
					('-Y', "  -Y", ""),
					('-X', "  -X", ""),
					('Z', "   Z", ""),
					('Y', "   Y", ""),
					('X', "   X", "")
					),
			default='-Z',
			description="Forward Axis"
			)
	axis_up = EnumProperty(
			name="Up",
			items=(('-Z', "  -Z", ""),
					('-Y', "  -Y", ""),
					('-X', "  -X", ""),
					('Z', "   Z", ""),
					('Y', " * Y", ""),
					('X', "   X", "")
					),
			default='Y',
			description="Up Axis"
			)
	mesh_smooth_type = EnumProperty(
			name="Smoothing",
			items=(('OFF', "Off", "Don't write smoothing"),
					('FACE', "Face", "Write face smoothing"),
					('EDGE', "Edge", "Write edge smoothing"),
					),
			default='FACE',
			description="Smoothing type"
			)
	normals_export_mode = EnumProperty(
			name="Normals",
			items=(('BLEND', "Default", "Use Blender's default split normals method."),
					('RECALCVN', "adsn's Recalc Vertex Normals", "Write normals from Recalc Vertex Normals script"),
					('NORMEDIT', "FBX Tools", "Write normals from the included Vertex Normals Addon"),
					('AUTO', "Automatic", "Automatically detect normals editor or use default normals")
				),
			default='BLEND',
			description="Normals export mode"
			)
	export_tangentspace_base = EnumProperty(
			name="Tangents",
			items=(('DEFAULT', "Default", "Blender default (Mikk TSpace)"),
					('LENGYEL', "Custom", "Custom implementation of Lengyel's method"),
					('NONE', " None ", "No tangents will be exported")
					),
			default='DEFAULT'
			)
	tangentspace_uvlnum = IntProperty(
			name="UV Layer",
			description=("Index of the UV layer to use for tangents"),
			min=0, max=16,
			default=0,
			)
	merge_vertexcollayers = BoolProperty(
			name="Merge Vertex Colors",
			description="Combine vertex color layers r, g, b into rgb",
			default=False,
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
	batch_mode = EnumProperty(
			name="Batch Mode",
			items=(('OFF', "Off", "Active scene to file"),
					('SCENE', "Scene", "Each scene as a file"),
					('GROUP', "Group", "Each group as a file")
					),
			options={'HIDDEN'}
			)
	use_batch_own_dir = BoolProperty(
			name="Batch Own Dir",
			description="Create a dir for each exported file",
			default=True,
			options={'HIDDEN'},
			)
	
	@property
	def check_extension(self):
		return self.batch_mode == 'OFF'
	
	def check(self, context):
		is_def_change = super().check(context)
		return (is_def_change)
	
	# new UI tab
	def draw(self, context):
		layout = self.layout
		
		box = layout.box()
		box.row().prop(self, 'object_types')
		
		box.row().prop(self, 'use_selection')
		
		row = box.row()
		row.column().label("Axis:")
		row.column().prop(self, 'axis_forward', text = '')
		row.column().prop(self, 'axis_up', text = '')
		box.row().prop(self, 'global_scale')
		
		if 'MESH' in self.object_types:
			box = layout.box()
			box.label("Mesh:")
			box.row().prop(self, 'use_mesh_modifiers')
			box.row().prop(self, 'use_armature_deform_only')
			box.row().prop(self, 'merge_vertexcollayers')
			
			box = layout.box()
			box.label("Shading:")
			box.row().prop(self, 'mesh_smooth_type')
			box.row().prop(self, 'normals_export_mode')
			box.row().prop(self, 'export_tangentspace_base')
			if self.export_tangentspace_base != 'NONE':	
				showtanuv = True
				if self.export_tangentspace_base == 'DEFAULT':
					if self.normals_export_mode != 'BLEND':
						box.row().label("*** Default normals required!")
						showtanuv = False
				if showtanuv and self.use_selection:
					box.row().prop(self, 'tangentspace_uvlnum')
		
		box = layout.box()
		box.label("Animations:")
		box.row().prop(self, 'use_anim')
		if self.use_anim:
			box.row().prop(self, 'use_anim_action_all')
			box.row().prop(self, 'use_default_take')
			box.row().prop(self, 'use_anim_optimize')
			if self.use_anim_optimize:
				box.row().prop(self, 'anim_optimize_precision')
		
	
	def execute(self, context):
		from mathutils import Matrix
		if not self.filepath:
			raise Exception("filepath not set")
		
		global_matrix = Matrix()
		global_matrix[0][0] = \
		global_matrix[1][1] = \
		global_matrix[2][2] = self.global_scale
		
		global_matrix = (global_matrix * axis_conversion(to_forward=self.axis_forward,to_up=self.axis_up,).to_4x4())
		
		keywords = self.as_keywords(ignore=("check_existing","filter_glob","axis_forward","axis_up"))
		keywords["global_matrix"] = global_matrix
		
		from . import export_fbx
		return export_fbx.save(self, context, **keywords)




#############################
# init:

def exportmenu_func(self, context):
	self.layout.operator(cust_ExportFBX.bl_idname,text="FBX Custom (.fbx)")


def register():
	bpy.utils.register_class(cust_ExportFBX)
	bpy.types.INFO_MT_file_export.append(exportmenu_func)


def unregister():
	bpy.types.INFO_MT_file_export.remove(exportmenu_func)
	bpy.utils.unregister_class(cust_ExportFBX)


if __name__ == '__main__':
	register()

