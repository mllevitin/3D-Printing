#!/usr/bin/env python3
"""Three dimensioned orthographic views of the actual STEP model."""
import json
from pathlib import Path
import re

import cadquery as cq
from cadquery.occ_impl.exporters.svg import makeSVGedge
from OCP.gp import gp_Ax2,gp_Pnt,gp_Dir
from OCP.BRepLib import BRepLib
from OCP.HLRBRep import HLRBRep_Algo,HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

ROOT=Path(__file__).resolve().parents[1]
INK='#18232c';DIM='#17455b'
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none'})


def linework(shape,normal,x_direction):
    algorithm=HLRBRep_Algo();algorithm.Add(shape.wrapped)
    axes=gp_Ax2(gp_Pnt(),gp_Dir(*normal),gp_Dir(*x_direction))
    algorithm.Projector(HLRAlgo_Projector(axes));algorithm.Update();algorithm.Hide()
    result=HLRBRep_HLRToShape(algorithm)
    groups=[]
    for compounds in ((result.HCompound(),result.OutLineHCompound()),
                      (result.VCompound(),result.Rg1LineVCompound(),result.OutLineVCompound())):
        segments=[]
        for compound in compounds:
            if compound.IsNull():
                continue
            BRepLib.BuildCurves3d_s(compound,1e-6)
            for edge in cq.Shape(compound).Edges():
                path=makeSVGedge(edge)
                points=[(float(x),float(y)) for x,y in re.findall(r'[ML]([^, ]+),([^ ]+)',path)]
                segments.extend(zip(points,points[1:]))
        groups.append(segments)
    return groups


def view(ax,shape,normal,x_direction,title,xlim,ylim):
    hidden,visible=linework(shape,normal,x_direction)
    ax.add_collection(LineCollection(hidden,colors='#9a9fa4',linewidths=.65,linestyles=(0,(5,4))))
    ax.add_collection(LineCollection(visible,colors=INK,linewidths=1.25))
    ax.set_xlim(*xlim);ax.set_ylim(*ylim);ax.set_aspect('equal');ax.set_axis_off()
    ax.set_title(title,size=16,color=INK,pad=10)


def dim(ax,a,b,offset,text,horizontal=True,size=12):
    if horizontal:
        p=(a[0],offset);q=(b[0],offset)
        ax.plot([a[0],a[0]],[a[1],offset],color=DIM,lw=.65)
        ax.plot([b[0],b[0]],[b[1],offset],color=DIM,lw=.65)
        ax.annotate('',xy=p,xytext=q,arrowprops={'arrowstyle':'<->','color':DIM,'lw':.9})
        ax.text((a[0]+b[0])/2,offset+2,text,ha='center',va='bottom',size=size,color=DIM)
    else:
        p=(offset,a[1]);q=(offset,b[1])
        ax.plot([a[0],offset],[a[1],a[1]],color=DIM,lw=.65)
        ax.plot([b[0],offset],[b[1],b[1]],color=DIM,lw=.65)
        ax.annotate('',xy=p,xytext=q,arrowprops={'arrowstyle':'<->','color':DIM,'lw':.9})
        ax.text(offset+2,(a[1]+b[1])/2,text,ha='left',va='center',rotation=90,size=size,color=DIM)


def main():
    p=json.loads((ROOT/'data/parameters.json').read_text())
    r=json.loads((ROOT/'models/validation_report.json').read_text())
    shape=cq.importers.importStep(str(ROOT/'models'/r['source_files']['step'])).val()
    L,W,H=r['dimensions_mm'];floor=p['body']['sole_thickness_mm'];wall=p['body']['jaw_thickness_mm']
    left,right=r['left_inner_face_x_mm'],r['right_inner_face_x_mm']
    gap=r['gap_mm'];case=p['case']['external_thickness_mm'];clearance=p['fit']['total_clearance_mm']
    fig=plt.figure(figsize=(16,9),dpi=180,facecolor='white')
    fig.text(.037,.965,f'AlphaServer DS10 · stand {r["revision"]} · three orthographic views',color=INK,size=22,weight='bold')
    fig.text(.037,.928,'All dimensions in mm. Solid lines: visible CAD edges; dashed lines: hidden edges.',color=INK,size=12)
    scale=min(16*.58/(L+49),9*.455/(H+53),9*.31/(W+36))
    front_height=(H+53)*scale/9
    front=fig.add_axes([.037,.425,(L+49)*scale/16,front_height])
    top=fig.add_axes([.037,.025,(L+49)*scale/16,(W+36)*scale/9])
    side=fig.add_axes([.735,.425,(W+36)*scale/16,front_height])
    view(front,shape,(0,-1,0),(1,0,0),'FRONT · XZ',(-12,L+37),(-23,H+30))
    view(top,shape,(0,0,1),(1,0,0),'TOP · XY',(-12,L+37),(-25,W+11))
    view(side,shape,(1,0,0),(0,1,0),'RIGHT · YZ',(-8,W+28),(-23,H+30))
    dim(front,(0,0),(L,0),-17,f'{L:g} · M01.01')
    dim(front,(L,0),(right+wall,H),L+18,f'{H:.2f}'+' · M01.05',False)
    dim(front,(left,H),(right,H),H+18,f'{gap:.1f}'+' · M02-03.01')
    dim(front,(left-wall,H),(left,H),H+6,f'{wall:g}'+' · M02.01',size=10)
    dim(front,(right,H),(right+wall,H),H+6,f'{wall:g}'+' · M03.01',size=10)
    front.annotate('Cut at middle gusset',xy=(left-wall,H),xytext=(L/2,H-12),
        ha='center',color='#357b52',size=11,
        arrowprops={'arrowstyle':'->','color':'#357b52','lw':.9})
    # Base thickness has its own callout and is included in the overall height.
    front.annotate('Base 6 · M01.03',xy=(L/2,floor/2),xytext=(L/2,35),ha='center',color=DIM,size=12,
        arrowprops={'arrowstyle':'->','color':DIM,'lw':.9})
    dim(top,(0,W/2),(L,W/2),-18,f'{L:g} · M01.01')
    dim(top,(L-W/2,0),(L-W/2,W),L+18,f'{W:g} · M01.02',False)
    top.annotate(f'R{W/2:g} · M01.04',xy=(W/2-W/2/2**.5,W/2-W/2/2**.5),xytext=(0,W+8),color=DIM,size=12,
        arrowprops={'arrowstyle':'->','color':DIM,'lw':.9})
    dim(side,(0,0),(W,0),-17,f'{W:g} · M01.02')
    dim(side,(W,0),(W,H),W+16,f'{H:.2f}'+' · M01.05',False)
    side.annotate('Base 6 · M01.03',xy=(W/2,3),xytext=(W/2,24),ha='center',color=DIM,size=12,
        arrowprops={'arrowstyle':'->','color':DIM,'lw':.9})
    legend=[
        ('M01.01','Overall base width',L),
        ('M01.02','Base depth',W),
        ('M01.03','Base thickness',floor),
        ('M01.04','End radius',W/2),
        ('M01.05','Overall stand height',H),
        ('M02.01','Left wall thickness',wall),
        ('M03.01','Right wall thickness',wall),
        ('M00.01','External case thickness',case),
        ('M02-03.01','Clear slot between walls',gap),
        ('M00-02.01','Nominal clearance, left',clearance/2),
        ('M00-03.01','Nominal clearance, right',clearance/2),
    ]
    fig.text(.54,.375,'DIMENSION IDS · consistent across all views',size=12,weight='bold',color=INK)
    for index,(code,meaning,value) in enumerate(legend):
        number=(f'{value:.2f}' if code=='M01.05' else f'{value:g}')
        fig.text(.54,.342-index*.0285,f'{code}  —  {meaning}: {number} mm',size=11,color=INK)
    fig.text(.037,.007,'Slot matches case thickness. Gussets preserved; top cut at the middle gusset junction. Fit feedback pending.',size=10,color=INK)
    out=ROOT/'drawings/three_projections.png'
    fig.savefig(out);fig.savefig(out.with_suffix('.svg'));plt.close(fig)
    print(out,flush=True)


if __name__=='__main__':
    main()
