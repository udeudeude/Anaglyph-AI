import math
import os
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


class TechniqueGenerator:
    """Render presentation formats that sit on top of the shared source/depth pipeline."""

    @staticmethod
    def _fill_holes(image: np.ndarray) -> np.ndarray:
        mask = np.all(image == -1, axis=-1).astype(np.uint8) * 255
        return cv2.inpaint(image.astype(np.uint8), mask, 1, cv2.INPAINT_TELEA)

    def generate_view(self, image: np.ndarray, depth_map: np.ndarray, offset: float, pop_out: bool = False, strength: float = 2.0) -> np.ndarray:
        height, width = image.shape[:2]
        depth = depth_map if pop_out else 1.0 - depth_map
        max_shift = (strength / 100.0 * width) / 2.0
        shifts = np.rint(offset * max_shift * depth).astype(np.int32)
        cols = np.arange(width)
        target_cols = np.clip(cols + shifts, 0, width - 1)
        rows = np.arange(height).reshape(height, 1)
        result = np.full_like(image, -1, dtype=np.int16)
        if offset < 0:
            result[rows, target_cols[:, ::-1]] = image[:, ::-1]
        else:
            result[rows, target_cols] = image
        return self._fill_holes(result)

    @staticmethod
    def _fit_bgr(image: np.ndarray, width: int, height: int, background=(0, 0, 0)) -> np.ndarray:
        canvas = np.full((height, width, 3), background, dtype=np.uint8)
        source_h, source_w = image.shape[:2]
        scale = min(width / source_w, height / source_h)
        new_w = max(1, int(round(source_w * scale))); new_h = max(1, int(round(source_h * scale)))
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
        x = (width - new_w) // 2; y = (height - new_h) // 2
        canvas[y:y + new_h, x:x + new_w] = resized
        return canvas

    @staticmethod
    def _crop_resize_pair(image: np.ndarray, depth: np.ndarray, width: int, height: int):
        source_h, source_w = image.shape[:2]; source_ratio = source_w / source_h; target_ratio = width / height
        if source_ratio > target_ratio:
            crop_w = int(round(source_h * target_ratio)); x0 = (source_w - crop_w) // 2; image = image[:, x0:x0 + crop_w]; depth = depth[:, x0:x0 + crop_w]
        elif source_ratio < target_ratio:
            crop_h = int(round(source_w / target_ratio)); y0 = (source_h - crop_h) // 2; image = image[y0:y0 + crop_h, :]; depth = depth[y0:y0 + crop_h, :]
        image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA); depth = cv2.resize(depth.astype(np.float32), (width, height), interpolation=cv2.INTER_CUBIC)
        return image, np.clip(depth, 0.0, 1.0).astype(np.float32)

    def chromadepth(self, image, depth, color_strength=0.9, reverse=False):
        depth_use = depth if reverse else 1.0 - depth; hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32); target_hue = np.clip(depth_use * 120.0, 0, 120); amount = max(0.0, min(1.0, color_strength)); hsv[:, :, 0] = target_hue; hsv[:, :, 1] = hsv[:, :, 1] * (1.0 - amount) + 255.0 * amount
        return cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)

    def cardboard(self, left, right, output_width=1920, output_height=1080, screen_width_mm=121.0, lens_separation_mm=63.0, image_scale=0.92):
        output_width=max(640,min(5000,int(output_width))); output_height=max(360,min(3000,int(output_height))); screen_width_mm=max(70,min(200,float(screen_width_mm))); lens_separation_mm=max(45,min(80,float(lens_separation_mm))); image_scale=max(.3,min(1,float(image_scale))); canvas=np.zeros((output_height,output_width,3),dtype=np.uint8); px_per_mm=output_width/screen_width_mm; center=output_width/2; centers=(center-lens_separation_mm*px_per_mm/2,center+lens_separation_mm*px_per_mm/2); box_w=max(1,int(output_width*.48*image_scale)); box_h=max(1,int(output_height*.96*image_scale))
        for source,eye_center in ((left,centers[0]),(right,centers[1])):
            fitted=self._fit_bgr(source,box_w,box_h); x0=int(round(eye_center-box_w/2)); y0=(output_height-box_h)//2; src_x0=max(0,-x0); dst_x0=max(0,x0); copy_w=min(box_w-src_x0,output_width-dst_x0)
            if copy_w>0: canvas[y0:y0+box_h,dst_x0:dst_x0+copy_w]=fitted[:,src_x0:src_x0+copy_w]
        return canvas

    @staticmethod
    def _font(size:int,bold=False,serif=False):
        candidates=["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold and serif else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf" if serif else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        for path in candidates:
            if os.path.exists(path):
                try:return ImageFont.truetype(path,max(8,int(size)))
                except OSError:pass
        return ImageFont.load_default()

    def stereoscope_card(self,left,right,dpi=300,card_width_in=7.0,card_height_in=3.5,image_width_in=2.85,image_height_in=2.55,gap_in=.35,arch_in=.22,title="STEREOSCOPIC VIEW",caption="Generated from a single photograph",publisher="Anaglyph & Friends",card_tone="cream"):
        dpi=max(72,min(1200,int(dpi))); cw=int(card_width_in*dpi); ch=int(card_height_in*dpi); iw=int(image_width_in*dpi); ih=int(image_height_in*dpi); gap=int(gap_in*dpi); tones={"cream":(229,213,170),"tan":(194,167,123),"gray":(188,187,179),"black":(28,27,25),"white":(244,241,232)}; bg=tones.get(card_tone,tones["cream"]); card=Image.new("RGB",(cw,ch),bg); total=iw*2+gap; x0=(cw-total)//2; y0=max(4,int(.16*dpi))
        for source,x in ((left,x0),(right,x0+iw+gap)):
            fitted=ImageOps.fit(Image.fromarray(cv2.cvtColor(source,cv2.COLOR_BGR2RGB)),(iw,ih),method=Image.Resampling.LANCZOS); card.paste(fitted,(x,y0))
        draw=ImageDraw.Draw(card); font=self._font(int(.12*dpi),True,True); draw.text((cw//2,text_y:=min(ch-int(.3*dpi),y0+ih+int(.08*dpi))),title[:100],fill=(40,35,28),font=font,anchor="ma")
        return cv2.cvtColor(np.array(card),cv2.COLOR_RGB2BGR)

    @staticmethod
    def _add_fusion_guides(image,separation):
        h,w=image.shape[:2]; guide_h=max(28,int(h*.06)); out=np.full((h+guide_h,w,3),255,dtype=np.uint8); out[guide_h:]=image; cx=w//2; r=max(2,int(min(w,h)*.006)); cv2.circle(out,(cx-separation//2,guide_h//2),r,(0,0,0),-1); cv2.circle(out,(cx+separation//2,guide_h//2),r,(0,0,0),-1); return out

    @staticmethod
    def _default_pattern(height,width,style="houndstooth"):
        yy,xx=np.indices((height,width)); tile=max(4,width//8); v=((xx//tile+yy//tile)%2)*180+50; return np.repeat(v[:,:,None].astype(np.uint8),3,axis=2)

    def autostereogram(self,depth,style="random",separation_percent=8.0,depth_percent=2.3,dot_size=3,viewing="parallel",pattern=None,color=False):
        height,width=depth.shape[:2]; separation=max(16,int(round(width*separation_percent/100))); max_shift=min(max(1,int(round(width*depth_percent/100))),separation-2)
        if style=="pattern": base=self._default_pattern(height,separation) if pattern is None else cv2.resize(pattern,(separation,height))
        else:
            dot_size=max(1,min(12,int(dot_size))); rng=np.random.default_rng(); sh=max(1,math.ceil(height/dot_size)); sw=max(1,math.ceil(separation/dot_size)); seed=rng.integers(0,256,size=(sh,sw,3),dtype=np.uint8) if color else np.repeat((rng.integers(0,2,size=(sh,sw,1),dtype=np.uint8)*255),3,axis=2); base=cv2.resize(seed,(separation,height),interpolation=cv2.INTER_NEAREST)
        output=np.zeros((height,width,3),dtype=np.uint8); output[:,:separation]=base; rows=np.arange(height); depth_use=1-depth if viewing.startswith("cross") else depth
        for x in range(separation,width):
            sep=separation-np.rint(depth_use[:,x]*max_shift).astype(np.int32); source_x=np.clip(x-sep,0,x-1); output[:,x]=output[rows,source_x]
        return self._add_fusion_guides(output,separation) if viewing.endswith("-guides") else output

    def wiggle_frames(self,image,depth,frame_count=7,strength=2.0,pop_out=False):
        frame_count=max(2,min(15,int(frame_count))); frames=[self.generate_view(image,depth,float(o),pop_out,strength) for o in np.linspace(-1,1,frame_count)]; return frames+frames[-2:0:-1] if len(frames)>2 else frames

    def lenticular(self,image,depth,output_width,output_height,dpi=600,lpi=60.0,views=6,slant_degrees=0.0,strength=2.0,pop_out=False):
        output_width=max(300,min(10000,int(output_width))); output_height=max(200,min(10000,int(output_height))); image,depth=self._crop_resize_pair(image,depth,output_width,output_height); pitch=dpi/lpi; yy,xx=np.indices((output_height,output_width),dtype=np.float32); phase=np.mod((xx+yy*math.tan(math.radians(slant_degrees)))/pitch,1); vi=np.minimum(views-1,np.floor(phase*views).astype(np.int16)); out=np.zeros_like(image)
        for i,o in enumerate(np.linspace(-1,1,views)):
            view=self.generate_view(image,depth,float(o),pop_out,strength); out[vi==i]=view[vi==i]
        return out

    def lenticular_calibration(self,dpi=600,nominal_lpi=60.0,span=.5,step=.1,width_in=8.0,band_height_in=.35):
        values=np.arange(nominal_lpi-span,nominal_lpi+span+step/2,step); width=int(width_in*dpi); bh=max(80,int(band_height_in*dpi)); canvas=Image.new("RGB",(width,bh*len(values)),"white"); draw=ImageDraw.Draw(canvas)
        for row,value in enumerate(values):
            pitch=dpi/value; x=np.arange(width); stripes=(np.mod(x,pitch)<pitch/2).astype(np.uint8)*255; rgb=np.repeat(np.repeat(stripes[None,:],bh,axis=0)[:,:,None],3,axis=2); canvas.paste(Image.fromarray(rgb),(0,row*bh)); draw.text((5,row*bh+5),f"{value:.2f} LPI",fill="red")
        return canvas

    def phantogram(self,image,depth,output_width,output_height,view_distance_mm=500.0,eye_height_mm=350.0,eye_separation_mm=63.0,print_width_mm=254.0,print_height_mm=190.5,pop_out=False,strength=2.0):
        """Create a parallel stereo phantogram rectified for a print lying on a horizontal surface."""
        output_width=max(400,min(10000,int(output_width))); output_height=max(300,min(10000,int(output_height))); image,depth=self._crop_resize_pair(image,depth,output_width//2,output_height)
        # Eye-height / forward-distance ratio determines the projective foreshortening of the physical print.
        d=max(100.0,float(view_distance_mm)); h=max(80.0,float(eye_height_mm)); sep=max(45.0,min(80.0,float(eye_separation_mm))); pw=max(50.0,float(print_width_mm)); ph=max(50.0,float(print_height_mm))
        near_scale=max(.12,min(.92,h/math.sqrt(h*h+d*d))); top_inset=(1.0-near_scale)*image.shape[1]/2.0
        src=np.float32([[0,0],[image.shape[1]-1,0],[image.shape[1]-1,image.shape[0]-1],[0,image.shape[0]-1]])
        dst=np.float32([[top_inset,0],[image.shape[1]-1-top_inset,0],[image.shape[1]-1,image.shape[0]-1],[0,image.shape[0]-1]])
        H=cv2.getPerspectiveTransform(src,dst)
        left=self.generate_view(image,depth,-1.0,pop_out,strength); right=self.generate_view(image,depth,1.0,pop_out,strength)
        left=cv2.warpPerspective(left,H,(image.shape[1],image.shape[0]),borderMode=cv2.BORDER_REPLICATE); right=cv2.warpPerspective(right,H,(image.shape[1],image.shape[0]),borderMode=cv2.BORDER_REPLICATE)
        # Small convergence correction derived from physical IPD versus print width.
        convergence=int(round((sep/pw)*image.shape[1]*.05)); left=np.roll(left,-convergence,axis=1); right=np.roll(right,convergence,axis=1)
        return np.hstack((left,right))


technique_generator=TechniqueGenerator()
