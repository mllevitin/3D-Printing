#!/usr/bin/env python3
"""Two identical one-piece DS10 stands from one parametric BREP model.

The case measurement is kept separate from design clearance. SGI is a
general structural reference; its mesh and specific mounting features are unchanged.
"""
from pathlib import Path
import datetime
import hashlib
import json
import math
import zipfile

import cadquery as cq
import numpy as np
import trimesh
from scipy.spatial import ConvexHull
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
NS = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def box_at(x, y, z, dx, dy, dz):
    return cq.Workplane('XY').box(dx, dy, dz, centered=(False, False, False)).translate((x, y, z))


def validate_parameters(p):
    if p['units'] != 'mm' or p['quantity'] != 2:
        raise ValueError('Millimeter units and two identical stands are required')
    if p['case']['external_thickness_mm'] != 130.5:
        raise ValueError('The measured 130.5 mm case thickness must be preserved')
    if p['fit']['shrinkage_scale'] != 1.0 or p['fit']['xy_compensation_mm'] != 0.0:
        raise ValueError('Hidden compensation is not allowed')
    b = p['body']
    for key, value in b.items():
        if isinstance(value, (int,float)) and (not math.isfinite(value) or value <= 0):
            raise ValueError(f'Invalid design dimension {key}: {value}')
    gap = p['case']['external_thickness_mm'] + p['fit']['total_clearance_mm']
    if p['fit']['total_clearance_mm'] < 0 or gap + 2*b['jaw_thickness_mm'] >= b['sole_length_mm']:
        raise ValueError('The slot and retaining walls must fit on the base')
    if b['total_height_mm'] <= b['sole_thickness_mm']:
        raise ValueError('Retaining walls must extend above the base')
    if b['gusset_profile_height_mm'] < b['total_height_mm']:
        raise ValueError('Original gusset profile must reach the trimming plane')
    if b['gusset_overlap_into_jaw_mm'] > b['jaw_thickness_mm']:
        raise ValueError('Gusset profile apex must remain inside the wall')
    return gap


def make_model(p):
    gap = validate_parameters(p)
    b = p['body']; length, depth = b['sole_length_mm'], b['sole_depth_mm']
    floor, height, jaw = b['sole_thickness_mm'], b['total_height_mm'], b['jaw_thickness_mm']
    left, right = (length-gap)/2, (length+gap)/2
    profile_peak_x = left-jaw+b['gusset_overlap_into_jaw_mm']
    profile_height = b['gusset_profile_height_mm']
    top_limit = box_at(0,0,0,length,depth,height)
    base = cq.Workplane('XY').center(length/2,depth/2).slot2D(length,depth).extrude(floor)
    footprint = cq.Workplane('XY').center(length/2,depth/2).slot2D(length,depth).extrude(height)
    parts = {'E01':base,
        'E02':box_at(left-jaw,0,floor,jaw,depth,height-floor).intersect(footprint),
        'E03':box_at(right,0,floor,jaw,depth,height-floor).intersect(footprint)}
    gussets = []
    thickness = b['outer_gusset_thickness_mm']
    mid = b['middle_gusset_thickness_mm']
    toe = b['outer_gusset_toe_mm']
    if toe >= left-jaw:
        toe = (left-jaw)/2
    radius = depth/2
    inset = radius-math.sqrt(radius**2-(radius-toe)**2) if toe < radius else 0.
    if inset+thickness >= (depth-mid)/2:
        raise ValueError('Outer gussets do not fit between the end and the middle gusset')
    if b['middle_gusset_toe_mm'] >= left-jaw:
        raise ValueError('Middle gusset must remain outside the retaining wall')
    profiles = [(inset,thickness,toe),
                ((depth-mid)/2,mid,b['middle_gusset_toe_mm']),
                (depth-inset-thickness,thickness,toe)]
    for side in ('left','right'):
        for index,(y,thick,toe) in enumerate(profiles):
            points = [(toe,floor),(profile_peak_x,floor),(profile_peak_x,profile_height)]
            if side == 'right':
                points = [(length-x,z) for x,z in points][::-1]
            plane = cq.Plane(origin=(0,y+thick,0),xDir=(1,0,0),normal=(0,-1,0))
            gusset = cq.Workplane(plane).polyline(points).close().extrude(thick).intersect(top_limit)
            parts[f'{side}_gusset_{index+1}'] = gusset
            gussets.append(gusset)
    model = base
    for name, part in parts.items():
        if name != 'E01':
            model = model.union(part)
    model = model.clean()
    return model, parts, dict(gap_mm=gap,left_inner_face_x_mm=left,right_inner_face_x_mm=right,
        outer_gusset_toe_derived_mm=profiles[0][2],outer_gusset_y_inset_derived_mm=inset,
        gusset_profile_peak_x_mm=profile_peak_x,
        gusset_profile_height_mm=profile_height,
        left_outer_face_x_mm=left-jaw,right_outer_face_x_mm=right+jaw,
        middle_gusset_join_height_mm=floor+(profile_height-floor)*
            (left-jaw-b['middle_gusset_toe_mm'])/(profile_peak_x-b['middle_gusset_toe_mm']),
        jaws_trimmed_to_stadium_footprint=True)


def write_scene(mesh, transforms, path, revision):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        archive.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        archive.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" Target="/3D/3dmodel.model"/>'
            '</Relationships>')
        with archive.open('3D/3dmodel.model','w') as stream:
            stream.write((f'<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="{NS}">'
                f'<resources><object id="1" type="model" name="AlphaServer DS10 stand {revision}"><mesh><vertices>').encode())
            for v in mesh.vertices:
                stream.write(('<vertex x="%.9f" y="%.9f" z="%.9f"/>' % tuple(v)).encode())
            stream.write(b'</vertices><triangles>')
            for f in mesh.faces:
                stream.write(('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f)).encode())
            stream.write(b'</triangles></mesh></object></resources><build>')
            for transform in transforms:
                values = ' '.join('%.12f' % v for v in transform[:3,:4].T.ravel())
                stream.write((f'<item objectid="1" transform="{values}"/>').encode())
            stream.write(b'</build></model>')


def make_placement(mesh,p):
    b = p['body']; layout = p['printer_layout']
    hull = mesh.vertices[ConvexHull(mesh.vertices[:,:2]).vertices,:2]
    offset = np.array([layout['second_shift_along_long_axis_mm'], b['sole_depth_mm']+layout['part_separation_mm'],0.])
    best = None
    angles = [layout['fixed_rotation_about_bed_z_deg']] if 'fixed_rotation_about_bed_z_deg' in layout else np.linspace(0,90,901)
    for angle in angles:
        rad = np.deg2rad(angle)
        rotation = np.array([[np.cos(rad),-np.sin(rad),0],[np.sin(rad),np.cos(rad),0],[0,0,1.]])
        points = np.vstack([hull,hull+offset[:2]])@rotation[:2,:2].T
        bounds = np.array([points.min(0),points.max(0)])
        score = np.ptp(points,axis=0).max()
        if best is None or score < best[0]:
            best = (score,float(angle),rotation,bounds)
    translation = np.array(layout['bed_mm'])/2 - best[3].mean(0)
    transforms = []
    for delta in (np.zeros(3),offset):
        t = np.eye(4);t[:3,:3] = best[2];t[:3,3] = best[2]@delta+[*translation,0.]
        points = trimesh.transform_points(mesh.vertices,t)
        if not np.all(points[:,:2].min(0)>3) or not np.all(points[:,:2].max(0)<np.array(layout['bed_mm'])-3):
            raise ValueError('Two stands do not fit on the bed with a 3 mm margin')
        transforms.append(t)
    return transforms,dict(angle_z_deg=best[1],second_shift_local_mm=offset.tolist(),
        placement_revision=layout.get('placement_revision','initial_diagonal'),
        separation_mm=layout['part_separation_mm'],scale=1,mirror=False,
        transforms=[t.tolist() for t in transforms],bed_mm=layout['bed_mm'],
        bounds_mm=[[trimesh.transform_points(mesh.vertices,t).min(0).tolist(),
                    trimesh.transform_points(mesh.vertices,t).max(0).tolist()] for t in transforms])


def main():
    p = json.loads((ROOT/'data/parameters.json').read_text())
    model,parts,derived = make_model(p)
    shape = model.val();b=p['body']
    if not shape.isValid() or len(shape.Solids())!=1:
        raise RuntimeError('Stand must be one valid connected BREP solid')
    bb = shape.BoundingBox()
    bounds = np.array([[bb.xmin,bb.ymin,bb.zmin],[bb.xmax,bb.ymax,bb.zmax]])
    expected = np.array([b['sole_length_mm'],b['sole_depth_mm'],b['total_height_mm']])
    if not np.allclose(bounds[0],0,atol=1e-7) or not np.allclose(bounds[1]-bounds[0],expected,atol=1e-7):
        raise RuntimeError('BREP dimensions do not match the parameters')
    test_case = box_at(derived['left_inner_face_x_mm']+p['fit']['total_clearance_mm']/2,
        0,b['sole_thickness_mm'],p['case']['external_thickness_mm'],b['sole_depth_mm'],
        b['total_height_mm']-b['sole_thickness_mm']).val()
    interference = shape.intersect(test_case).Volume()
    if interference > 1e-7:
        raise RuntimeError('Stand material intersects the nominal DS10 case')
    out=ROOT/'models';out.mkdir(exist_ok=True)
    tag=p['revision'].replace('.','')
    step=out/f'ds10_stand_{tag}.step';stl=out/f'ds10_stand_{tag}.stl'
    cq.exporters.export(model,str(step))
    cq.exporters.export(model,str(stl),tolerance=p['export']['mesh_linear_tolerance_mm'],
        angularTolerance=p['export']['mesh_angular_tolerance_rad'])
    mesh=trimesh.load_mesh(stl,process=True)
    if not mesh.is_watertight or not mesh.is_volume or len(mesh.split(only_watertight=False))!=1:
        raise RuntimeError('STL must be one watertight positive-volume body')
    if not np.allclose(mesh.extents,expected,atol=.001):
        raise RuntimeError('STL dimensions changed during export')
    transforms,placement=make_placement(mesh,p)
    write_scene(mesh,transforms,out/f'ds10_two_stands_{tag}.3mf',p['revision'])
    write_scene(mesh,[np.eye(4)],out/f'ds10_stand_{tag}.3mf',p['revision'])
    roundtrip=cq.importers.importStep(str(step)).val()
    if not roundtrip.isValid() or len(roundtrip.Solids())!=1 or not math.isclose(roundtrip.Volume(),shape.Volume(),abs_tol=.001):
        raise RuntimeError('STEP failed round-trip import or volume verification')
    inner_faces=[]
    for face in roundtrip.Faces():
        bounds_face=face.BoundingBox()
        if bounds_face.xlen < 1e-6 and bounds_face.zlen > b['total_height_mm']-b['sole_thickness_mm']-1e-6:
            inner_faces.append(bounds_face.xmin)
    if not all(any(abs(x-required)<1e-6 for x in inner_faces) for required in (derived['left_inner_face_x_mm'],derived['right_inner_face_x_mm'])):
        raise RuntimeError('Both inner wall faces were not found at the specified STEP coordinates')
    with zipfile.ZipFile(out/f'ds10_two_stands_{tag}.3mf') as archive:
        doc=etree.fromstring(archive.read('3D/3dmodel.model'))
    ns={'m':NS}
    items=doc.findall('./m:build/m:item',ns)
    if doc.attrib['unit']!='millimeter' or len(items)!=2 or len({i.attrib['objectid'] for i in items})!=1:
        raise RuntimeError('3MF must contain two identical instances in millimeters')
    report=dict(status='passed_geometry_pending_physical_fit',revision=p['revision'],
        source_parameter_sha256=hashlib.sha256((ROOT/'data/parameters.json').read_bytes()).hexdigest(),
        units='mm',brep_valid=True,solid_count=1,mesh_watertight=True,mesh_connected=True,
        case_external_thickness_user_mm=p['case']['external_thickness_mm'],
        total_clearance_mm=p['fit']['total_clearance_mm'],
        maximum_total_clearance_user_mm=p['fit']['maximum_total_clearance_user_mm'],
        side_clearance_mm=p['fit']['total_clearance_mm']/2,**derived,
        dimensions_mm=expected.tolist(),brep_volume_mm3=shape.Volume(),stl_volume_mm3=mesh.volume,
        nominal_case_interference_mm3=interference,mesh_vertices=len(mesh.vertices),mesh_triangles=len(mesh.faces),
        copies_share_same_3mf_mesh=True,quantity=2,placement=placement,
        step_roundtrip_valid=True,step_gap_between_actual_planes_mm=derived['gap_mm'],
        source_files={'step':step.name,'stl':stl.name,'single_3mf':f'ds10_stand_{tag}.3mf','two_3mf':f'ds10_two_stands_{tag}.3mf'},
        physical_fit_verified=False,
        physical_strength_verified=False,print_authorized=False,
        created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    save(out/'validation_report.json',report)
    save(ROOT/'printing/placement_review.json',placement)
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    main()
