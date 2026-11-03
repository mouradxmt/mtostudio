#!/usr/bin/env python3
"""Original 1024 × 500 Play feature graphic, drawn from geometric paths without fonts."""
from pathlib import Path
import struct
import zlib

W,H=1024,500
pixels=bytearray(bytes([20,40,56])*W*H)
def stroke(points,color,width):
    radius=width/2
    for (a,b),(c,d) in zip(points,points[1:]):
        for y in range(max(0,int(min(b,d)-radius-1)),min(H,int(max(b,d)+radius+2))):
            for x in range(max(0,int(min(a,c)-radius-1)),min(W,int(max(a,c)+radius+2))):
                den=(c-a)**2+(d-b)**2
                t=max(0,min(1,((x+.5-a)*(c-a)+(y+.5-b)*(d-b))/den)) if den else 0
                if (x+.5-a-t*(c-a))**2+(y+.5-b-t*(d-b))**2<=radius**2:
                    offset=(y*W+x)*3;pixels[offset:offset+3]=bytes(color)
teal=(104,225,203);gold=(255,196,107);white=(238,247,250)
for x in [376,956]:stroke([(x,66),(x,434)],(30,57,73),1)
stroke([(58,402),(966,402)],(30,57,73),1)
stroke([(105,322),(105,174),(198,262),(291,174),(291,322)],teal,32)
stroke([(198,311),(198,344)],gold,26)
glyphs={
 'M':[[(0,40),(0,0),(13,22),(26,0),(26,40)]],
 'T':[[(0,0),(26,0)],[(13,0),(13,40)]],
 'O':[[(4,0),(22,0),(26,4),(26,36),(22,40),(4,40),(0,36),(0,4),(4,0)]],
 'U':[[(0,0),(0,36),(4,40),(22,40),(26,36),(26,0)]],
 'A':[[(0,40),(13,0),(26,40)],[(5,27),(21,27)]],
 'S':[[(26,0),(4,0),(0,4),(0,16),(4,20),(22,20),(26,24),(26,36),(22,40),(0,40)]],
 'D':[[(0,0),(18,0),(26,8),(26,32),(18,40),(0,40),(0,0)]],
 'I':[[(0,0),(26,0)],[(13,0),(13,40)],[(0,40),(26,40)]]}
def text(word,x,y,scale,color):
    for letter in word:
        for path in glyphs[letter]:stroke([(x+a*scale,y+b*scale) for a,b in path],color,2.5*scale)
        x+=38*scale
text('MTOUAA',420,170,2.15,white)
text('STUDIO',420,298,1.15,gold)
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
def write_png(name,alpha=False):
    rows=[]
    for y in range(H):
        row=bytes(pixels[y*W*3:(y+1)*W*3])
        if alpha:row=b''.join(row[i:i+3]+b'\xff' for i in range(0,len(row),3))
        rows.append(b'\0'+row)
    out=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,6 if alpha else 2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows),9))+chunk(b'IEND',b'')
    path=Path(__file__).resolve().parent.parent/'release/store'/name;path.write_bytes(out)
write_png('feature-graphic-1024x500.png')
# Play applies its own mask: the listing icon must be a full square, without
# pre-rounded transparent corners. Keep the same original M and accent strokes.
W=H=512;pixels=bytearray(bytes([20,40,56])*W*H)
stroke([(120,364),(120,148),(256,276),(392,148),(392,364)],teal,48)
stroke([(256,348),(256,396)],gold,40)
write_png('icon-512.png',alpha=True)
print('Generated full-square Play icon and feature graphic.')
