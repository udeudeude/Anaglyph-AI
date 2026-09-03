import numpy as np
from depth_sources import align_depth, normalise_depth
from stereo_formats import compatibility_stereo, make_anaglyph
from technique_generator import technique_generator

def sample_data(width=96,height=64):
    x=np.linspace(0,255,width,dtype=np.uint8); y=np.linspace(0,255,height,dtype=np.uint8)[:,None]; image=np.zeros((height,width,3),dtype=np.uint8); image[:,:,0]=x; image[:,:,1]=y; image[:,:,2]=180; depth=np.tile(np.linspace(0,1,width,dtype=np.float32),(height,1)); return image,depth
def main():
    image,depth=sample_data(); view=technique_generator.generate_view(image,depth,.5,False,2); assert view.shape==image.shape
    assert technique_generator.chromadepth(image,depth).shape==image.shape
    assert make_anaglyph(image,view,'red-cyan','full').shape==image.shape
    for mode in ('topbottom','halfsbs','rowinterlaced','columninterlaced','checkerboard'): assert compatibility_stereo(image,view,mode).ndim==3
    normalised=normalise_depth(np.arange(24,dtype=np.uint16).reshape(4,6)); assert normalised.dtype==np.float32
    for mode in ('crop','fit','stretch'): assert align_depth(normalised,image.shape[1],image.shape[0],mode).shape==image.shape[:2]
    assert technique_generator.cardboard(view,view,640,360).shape==(360,640,3)
    assert technique_generator.stereoscope_card(view,view,dpi=72).ndim==3
    parallel=technique_generator.autostereogram(depth,style='random',separation_percent=10,depth_percent=2,dot_size=2,viewing='parallel'); cross=technique_generator.autostereogram(depth,style='random',separation_percent=10,depth_percent=2,dot_size=2,viewing='cross'); assert parallel.shape==image.shape and cross.shape==image.shape
    frames=technique_generator.wiggle_frames(image,depth,5,2); assert len(frames)==8
    assert technique_generator.lenticular(image,depth,300,200,dpi=150,lpi=60,views=3).shape==(200,300,3)
    assert technique_generator.lenticular_calibration(dpi=150,nominal_lpi=60,span=.2,step=.1,width_in=2).width==300
    ph=technique_generator.phantogram(image,depth,600,300,view_distance_mm=508,eye_height_mm=355.6,eye_separation_mm=63,print_width_mm=254,print_height_mm=190.5); assert ph.shape==(300,600,3); assert ph.dtype==np.uint8
    print('Technique renderer smoke tests passed')
if __name__=='__main__':main()
