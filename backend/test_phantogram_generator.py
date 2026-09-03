import numpy as np
from phantogram_generator import project_relief, render_phantogram

def main():
    h,w=80,120
    image=np.zeros((h,w,3),dtype=np.uint8); image[:,:,0]=np.arange(w,dtype=np.uint8); image[:,:,1]=140; image[:,:,2]=220
    flat=np.zeros((h,w),dtype=np.float32)
    # Zero relief must map identically to the print plane for either eye.
    left=project_relief(image,flat,254,190.5,508,355.6,-31.5,35)
    right=project_relief(image,flat,254,190.5,508,355.6,31.5,35)
    assert np.array_equal(left,image)
    assert np.array_equal(right,image)
    depth=np.tile(np.linspace(0,1,w,dtype=np.float32),(h,1))
    anaglyph,l,r=render_phantogram(image,depth,relief_mm=35)
    assert anaglyph.shape==image.shape and l.shape==image.shape and r.shape==image.shape
    assert not np.array_equal(l,r)
    assert np.all(anaglyph[:,:,2]==l[:,:,2])
    print('Phantogram projection tests passed')
if __name__=='__main__': main()
