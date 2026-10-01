"""Blender-only primitives; imports stay lazy so application tests need no bpy."""
import math

PALETTE = {'red': (.95,.07,.12,1), 'blue': (.02,.38,.88,1), 'yellow': (1,.72,.02,1),
           'green': (.08,.7,.3,1), 'orange': (1,.25,.04,1), 'coral': (1,.2,.25,1),
           'gold': (1,.65,.06,1), 'mint': (.16,.83,.64,1), 'violet': (.46,.18,.85,1),
           'metal': (.22,.3,.36,1), 'tire': (.025,.035,.05,1), 'white': (.92,.94,1,1),
           'track': (.13,.22,.29,1), 'floor': (.72,.85,.86,1), 'glass': (.05,.19,.28,1)}


def material(color):
    import bpy
    name = 'Toy_' + color
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = PALETTE[color]
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = PALETTE[color]
    shader.inputs['Roughness'].default_value = .32 if color != 'tire' else .7
    shader.inputs['Metallic'].default_value = .5 if color == 'metal' else .05
    return mat


def finish(obj, name, color, bevel=.07):
    obj.name = name
    obj.data.materials.append(material(color))
    if bevel:
        modifier = obj.modifiers.new('Soft toy edges', 'BEVEL')
        modifier.width, modifier.segments = bevel, 3
        obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj


def box(name, location, dimensions, color):
    import bpy
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, color)


def cylinder(name, location, radius, depth, color, rotation=(0,0,0)):
    import bpy
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=depth, location=location, rotation=rotation)
    return finish(bpy.context.object, name, color, .03)


def wedge(name, start, length, width, height, color):
    import bpy
    vertices = [(start,y,0) for y in (-width/2,width/2)] + [(start+length,y,z) for z in (0,height) for y in (-width/2,width/2)]
    faces = [(0,2,3,1), (0,1,5,4), (2,4,5,3), (0,4,2), (1,3,5)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, color)


def rigid_body(obj, animated=False, mass=1):
    import bpy
    bpy.context.view_layer.objects.active = obj
    bpy.ops.rigidbody.object_add()
    body = obj.rigid_body
    body.type = 'ACTIVE' if animated else 'PASSIVE'
    body.kinematic = animated
    body.mass, body.friction, body.restitution = mass, .8, .05
    body.collision_shape = 'CONVEX_HULL'
    body.use_margin, body.collision_margin = True, .01
