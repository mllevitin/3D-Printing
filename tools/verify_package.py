"""Verify released CAD, complete meshes, and both print packages."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import re
import zipfile
import xml.etree.ElementTree as ET

import cadquery as cq
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
PPATH = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}path'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matrix(text):
    result = np.eye(4)
    if text:
        result[:3, :4] = np.array([float(n) for n in text.split()]).reshape(4, 3).T
    if not np.allclose(result[:3, :3].T @ result[:3, :3], np.eye(3), atol=1e-7) or not np.isclose(np.linalg.det(result[:3, :3]), 1, atol=1e-7):
        raise RuntimeError('3MF contains scaling or reflection')
    return result


def mesh_data(obj):
    vertices = np.array([[float(v.attrib[k]) for k in ('x', 'y', 'z')]
        for v in obj.findall('.//m:mesh/m:vertices/m:vertex', NS)])
    faces = np.array([[int(f.attrib[k]) for k in ('v1', 'v2', 'v3')]
        for f in obj.findall('.//m:mesh/m:triangles/m:triangle', NS)])
    return vertices, faces


def archive_instances(path):
    with zipfile.ZipFile(path) as archive:
        documents = {}
        instances = []
        def document(member):
            if member not in documents:
                documents[member] = ET.fromstring(archive.read(member))
                if documents[member].attrib.get('unit') != 'millimeter':
                    raise RuntimeError('3MF units must be millimeters')
            return documents[member]
        def collect(member, object_id, transform):
            obj = document(member).find(f'./m:resources/m:object[@id="{object_id}"]', NS)
            if obj is None:
                raise RuntimeError(f'Object not found {member}:{object_id}')
            if obj.find('m:mesh', NS) is not None:
                instances.append((*mesh_data(obj), transform))
            else:
                for child in obj.findall('./m:components/m:component', NS):
                    collect(child.attrib.get(PPATH, member).lstrip('/'), child.attrib['objectid'],
                        transform @ matrix(child.attrib.get('transform')))
        for item in document('3D/3dmodel.model').findall('./m:build/m:item', NS):
            collect('3D/3dmodel.model', item.attrib['objectid'], matrix(item.attrib.get('transform')))
        return instances


def verify_variant(info):
    root = ROOT / info['directory']
    p = json.loads((root / 'data/parameters.json').read_text())
    report = json.loads((root / 'models/validation_report.json').read_text())
    print_settings = json.loads((root / 'printing/print_settings.json').read_text())
    if sha(root / 'data/parameters.json') != report['source_parameter_sha256']:
        raise RuntimeError('Parameters and report refer to different models')
    dimensions = np.array(info['dimensions_mm'])
    shape = cq.importers.importStep(str(root / 'models' / report['source_files']['step'])).val()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise RuntimeError('STEP must contain one valid solid')
    bbox = shape.BoundingBox()
    actual = np.array([bbox.xlen, bbox.ylen, bbox.zlen])
    if not np.allclose(actual, dimensions, atol=1e-7):
        raise RuntimeError('STEP dimensions changed')
    mesh = trimesh.load_mesh(root / 'models' / report['source_files']['stl'], process=True)
    if not mesh.is_watertight or not mesh.is_volume or len(mesh.split(only_watertight=False)) != 1:
        raise RuntimeError('STL must be one watertight positive-volume mesh')
    if not np.allclose(mesh.extents, dimensions, atol=.001):
        raise RuntimeError('STL dimensions changed')
    inner_faces = []
    for face in shape.Faces():
        fb = face.BoundingBox()
        if fb.xlen < 1e-6 and fb.zlen > dimensions[2] - p['body']['sole_thickness_mm'] - 1e-6:
            inner_faces.append(fb.xmin)
    left, right = report['left_inner_face_x_mm'], report['right_inner_face_x_mm']
    if not all(any(abs(x - target) < 1e-6 for x in inner_faces) for target in (left, right)):
        raise RuntimeError('Required inner retaining-wall faces are missing from STEP')
    if not math.isclose(right - left, info['gap_mm'], abs_tol=1e-7):
        raise RuntimeError('Case slot width changed')
    spec = importlib.util.spec_from_file_location('build_' + info['revision'].replace('.', ''), root / 'source/build_model.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    rebuilt, _, _ = builder.make_model(p)
    rebuilt_shape = rebuilt.val()
    if not rebuilt_shape.isValid() or len(rebuilt_shape.Solids()) != 1:
        raise RuntimeError('Source did not produce a valid solid')
    added = rebuilt_shape.cut(shape).Volume()
    removed = shape.cut(rebuilt_shape).Volume()
    if max(added, removed) > 1e-5:
        raise RuntimeError('Source does not reproduce the released STEP')
    single = archive_instances(root / 'models' / report['source_files']['single_3mf'])
    if len(single) != 1:
        raise RuntimeError('Single-stand 3MF contains an incorrect number of objects')
    vertices, faces, single_transform = single[0]
    if not np.allclose(single_transform, np.eye(4), atol=1e-9):
        raise RuntimeError('Single-stand 3MF contains a hidden translation')
    expected = [np.array(t) for t in report['placement']['transforms']]
    centers = [(vertices @ t[:3, :3].T + t[:3, 3]).mean(0) for t in expected]
    packet = root / 'printing' / print_settings['print_package']
    if sha(packet) != print_settings['package_sha256']:
        raise RuntimeError('Printed package changed')
    raw_gcode = packet.with_suffix('')
    if sha(raw_gcode) != print_settings['gcode_sha256']:
        raise RuntimeError('Separate G-code changed')
    errors = []
    for path in (root / 'models' / report['source_files']['two_3mf'], packet):
        instances = archive_instances(path)
        if len(instances) != 2:
            raise RuntimeError('Package must contain two stands')
        used = set()
        for actual_vertices, actual_faces, transform in instances:
            if actual_vertices.shape != vertices.shape or not np.array_equal(actual_faces, faces):
                raise RuntimeError('Mesh vertices or triangles changed')
            world = actual_vertices @ transform[:3, :3].T + transform[:3, 3]
            index = int(np.argmin([np.linalg.norm(world.mean(0) - c) for c in centers]))
            if index in used:
                raise RuntimeError('Two instances occupy the same position')
            used.add(index)
            inverse = np.linalg.inv(expected[index])
            recovered = world @ inverse[:3, :3].T + inverse[:3, 3]
            error = float(np.max(np.abs(recovered - vertices)))
            if error > 8e-5:
                raise RuntimeError('Mesh or layout changed')
            bounds = np.array([world.min(0), world.max(0)])
            if np.any(bounds[0, :2] < 3) or np.any(bounds[1, :2] > 267) or abs(bounds[0, 2]) > 8e-5:
                raise RuntimeError('Stands exceed the bed bounds or are raised above Z=0')
            errors.append(error)
    with zipfile.ZipFile(packet) as archive:
        raw = archive.read('Metadata/plate_1.gcode')
        if raw != raw_gcode.read_bytes():
            raise RuntimeError('Separate G-code does not match the package')
        if archive.read('Metadata/plate_1.gcode.md5').decode().lower() != hashlib.md5(raw).hexdigest():
            raise RuntimeError('G-code MD5 mismatch')
        if re.search(rb'^\s*M624\b', raw, re.M):
            raise RuntimeError('Package still contains unsupported M624 commands')
        if b'PRINT_START BED=55 HOTEND=230 CHAMBER=0 EXTRUDER=0' not in raw:
            raise RuntimeError('Start parameters differ from the saved profile')
        settings = json.loads(archive.read('Metadata/project_settings.config'))
        if settings != json.loads((root / 'printing/profiles/effective_settings.json').read_text()):
            raise RuntimeError('Effective settings do not match the package')
        if settings['nozzle_temperature'] != ['230'] or settings['layer_height'] != '0.28':
            raise RuntimeError('Temperature or layer height differs from the specified values')
        if not info['physical_print_completed']:
            raise RuntimeError('Completed print record is missing')
    for name in ('three_projections.png', 'three_projections.svg'):
        if not (root / 'drawings' / name).is_file():
            raise RuntimeError('Dimensioned drawing is missing')
    return dict(revision=info['revision'], status='passed', dimensions_mm=actual.tolist(), gap_mm=right-left,
        brep_valid=True, connected_solid_count=1, mesh_watertight=True,
        source_matches_step=True, source_added_volume_mm3=added, source_removed_volume_mm3=removed,
        two_instances_per_packet=True, full_mesh_matches=True, rigid_scale_one=True,
        max_vertex_difference_mm=max(errors), package_sha256=sha(packet), print_completed=True)


def verify_language():
    checked = 0
    text_suffixes = {'.md', '.py', '.json', '.svg', '.txt', '.gcode', '.step'}
    for path in ROOT.rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts:
            continue
        contents = []
        if path.suffix == '.3mf':
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if name.endswith(('.model', '.xml', '.config', '.json', '.gcode')):
                        raw = archive.read(name)
                        contents.append((str(path.relative_to(ROOT)) + ':' + name, raw))
                        if name.endswith('.model'):
                            language = ET.fromstring(raw).get('{http://www.w3.org/XML/1998/namespace}lang')
                            if language is not None and language not in ('en', 'en-US', 'en-GB'):
                                raise RuntimeError('Non-English 3MF language metadata: ' + name)
        elif path.suffix in text_suffixes or path.name in ('.gitignore', '.gitattributes'):
            contents.append((str(path.relative_to(ROOT)), path.read_bytes()))
        for name, raw in contents:
            text = raw.decode('utf-8')
            if any(0x0400 <= ord(character) <= 0x052F for character in text):
                raise RuntimeError('Non-English Cyrillic text remains: ' + name)
            checked += 1
    return {'status': 'passed', 'language': 'en', 'text_files_and_archive_members_checked': checked,
            'cyrillic_text_found': False, 'three_mf_language_metadata': 'English'}


def main():
    manifest = json.loads((ROOT / 'MANIFEST.json').read_text())
    results = [verify_variant(info) for info in manifest['variants']]
    result = {'status': 'passed', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'language_review': verify_language(), 'variants': results}
    (ROOT / 'VALIDATION.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
