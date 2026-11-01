"""Opt-in union-of-rectangles clip of exact original bitmap mathematical atoms.

This wraps the frozen original raster replay; it does not modify an image,
recognize/retype mathematics, change scale, or modify that common helper.
Every source rectangle still passes its strict 4x original RGB recipe check.
The caller manually verifies the whole original symbol, including scripts and
gray fringes, within the declared partition. No automatic mask/erase inference.
"""
import math
import pymupdf as fitz
from pdf_original_raster_math import replay

def expand_rectangular_clip_partitions(atoms):
    expanded=[];groups=[];seen=set()
    for atom in atoms:
        if atom['id']in seen:raise ValueError('Duplicate original atom identity')
        seen.add(atom['id']);pieces=atom.get('clip_rects')
        if not pieces:expanded.append(atom);continue
        if atom.get('reviewed')is not True or not atom.get('clip_partition_evidence'):raise ValueError('Partition requires explicit whole-math/source-prose review')
        bounds=fitz.Rect(atom['rect']);parsed=[]
        for i,coords in enumerate(pieces):
            rect=fitz.Rect(coords)
            if rect.is_empty or not bounds.contains(rect):raise ValueError('Partition escapes whole source atom')
            if any(not math.isfinite(float(v))for v in rect):raise ValueError('Nonfinite clip')
            if any(abs(float(v)*4-round(float(v)*4))>1e-7 for v in rect):raise ValueError('Reviewed source clip edges must align to the 4x witness pixel grid')
            if any((rect&r).get_area()>1e-8 for r in parsed):raise ValueError('Partition rectangles must be disjoint; opaque image padding must not repaint another partition')
            parsed.append(rect)
            item={k:v for k,v in atom.items()if k not in ['clip_rects','clip_partition_evidence']};item.update(id=atom['id']+f'/part{i+1:02d}',rect=list(rect),reason=atom['reason']+'; '+atom['clip_partition_evidence']);expanded.append(item)
        groups.append(dict(id=atom['id'],source_bounding_rect=list(bounds),clip_rects=[list(r)for r in parsed],dx=float(atom['dx']),same_dx_y_and_1x_scale_for_every_piece=True,reason=atom['clip_partition_evidence']))
    return expanded,groups

def replay_partitioned(source,number,base,atoms):
    pieces,groups=expand_rectangular_clip_partitions(atoms)
    raw,journal=replay(source,number,base,pieces)
    journal['manually_reviewed_rectangular_clip_partitions']=groups
    return raw,journal
