UDK/UE4 Blender FBX Exporter  
  
Standalone exporter from my old normals editor.  
based on the fbx exporter included in Blender 2.68  
  
--------------------------------------  
  
_ Additions + fixes _
  
- supports Blender's split normals, normals created by adsn's Rcalc Vertex Normals addon and my old FBX Normals Tools
- exports Blender's tangents (Mikk TSpace) for custom normals
- custom export UI panel
- uses the root bone as root instead of creating its own
  - includes some modifications to armature rotations to allow this
- combine vertex color channels on export  
  
--------------------------------------  
  
_Changelog_

*v1.0.0* (current):
- updated to match final FBX Tools version  
  