"""Compare released STL models at the same scale."""
from pathlib import Path
import json
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parents[1]


def main():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none'})
    fig = plt.figure(figsize=(14, 7), dpi=180, facecolor='white')
    fig.text(.04, .945, 'AlphaServer DS10 · two stand designs', fontsize=23, weight='bold', color='#18232c')
    fig.text(.04, .885, 'Actual STL models · same scale · dimensions in mm · two stands required per case', fontsize=12, color='#18232c')
    for i, (dirname, tag, title) in enumerate([
        ('v03-high', 'v03', 'Tall v0.3'), ('v04-low', 'v04', 'Short v0.4')]):
        variant = ROOT / 'variants' / dirname
        data = json.loads((variant / 'data/parameters.json').read_text())
        mesh = trimesh.load_mesh(variant / 'models' / f'ds10_stand_{tag}.stl', process=True)
        light = np.array([-.3, -.8, 1.]); light /= np.linalg.norm(light)
        shade = .45 + .55 * np.clip(mesh.face_normals @ light, 0, 1)
        colors = np.column_stack([.15 + .25 * shade, .36 + .38 * shade, .41 + .42 * shade, np.ones(len(shade))])
        ax = fig.add_axes([.025 + i * .50, .25, .47, .58], projection='3d')
        ax.add_collection3d(Poly3DCollection(mesh.triangles, facecolors=colors, edgecolors='none', rasterized=True))
        ax.set_xlim(0, 200); ax.set_ylim(0, 50); ax.set_zlim(0, 100)
        ax.set_box_aspect((200, 50, 100)); ax.set_proj_type('ortho')
        ax.view_init(elev=25, azim=-63); ax.set_axis_off()
        ax.set_title(title, fontsize=17, color='#18232c', weight='bold')
        height = data['body']['total_height_mm']
        gap = data['case']['external_thickness_mm'] + data['fit']['total_clearance_mm']
        fig.text(.10 + i * .50, .18, f'200 × 50 × {height:.2f} mm', fontsize=16, color='#18232c')
        fig.text(.10 + i * .50, .12, f'Clear slot between walls: {gap:.1f} mm', fontsize=12, color='#17647b')
    fig.text(.04, .035, 'Base and gusset slopes preserved; v0.4 is shorter, with a nominal 130.5 mm slot.', fontsize=11, color='#18232c')
    fig.savefig(ROOT / 'docs/variants_comparison.png')
    fig.savefig(ROOT / 'docs/variants_comparison.svg')
    plt.close(fig)


if __name__ == '__main__':
    main()
