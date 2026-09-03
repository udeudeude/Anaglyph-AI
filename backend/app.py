from flask import Flask, jsonify, request, session, send_file
from flask_cors import CORS
import uuid, os, io, json, time
from PIL import Image, ImageOps
import cv2
import numpy as np
from depth_map_generator import depth_map_generator
from anaglyph_generator import anaglyph_generator
from technique_generator import technique_generator
from depth_sources import align_depth, load_depth_upload
from stereo_formats import compatibility_stereo, make_anaglyph
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from werkzeug.utils import send_from_directory

app=Flask(__name__); CORS(app,supports_credentials=True); load_dotenv(); host=os.getenv('FLASK_HOST','0.0.0.0'); port=int(os.getenv('FLASK_PORT',8000)); app.secret_key=os.getenv('FLASK_SECRET_KEY','local-anaglyph-and-friends'); KERNEL_WIDTH=15; PREVIEW_MAX_DIMENSION=1600; SESSION_DATA_FOLDER='resources/session_data'; os.makedirs(SESSION_DATA_FOLDER,exist_ok=True)
ALLOWED_EXTENSIONS={'bmp','dib','jpeg','jpg','jpe','jp2','png','webp','pbm','pgm','ppm','pxm','pnm','sr','ras','tiff','tif','exr','hdr','pic'}
@app.route('/')
def hello_world(): return 'Anaglyph & Friends backend'
@app.before_request
def assign_session_id():
    if 'session_id' not in session: session['session_id']=str(uuid.uuid4())
def session_path(suffix): return os.path.join(SESSION_DATA_FOLDER,f"{session['session_id']}_{suffix}")
def clear_session_products():
    prefix=f"{session['session_id']}_"
    for filename in os.listdir(SESSION_DATA_FOLDER):
        if filename.startswith(prefix):
            try: os.remove(os.path.join(SESSION_DATA_FOLDER,filename))
            except FileNotFoundError: pass
def clear_stereo_cache():
    for suffix in ('preview_left.png','preview_right.png','preview_stereo.json','full_left.png','full_right.png','full_stereo.json'):
        try: os.remove(session_path(suffix))
        except FileNotFoundError: pass
def clear_old_session_files():
    now=time.time()
    for filename in os.listdir(SESSION_DATA_FOLDER):
        path=os.path.join(SESSION_DATA_FOLDER,filename)
        if os.path.isfile(path) and now-os.path.getmtime(path)>3600: os.remove(path)
clean_up_scheduler=BackgroundScheduler(); clean_up_scheduler.add_job(clear_old_session_files,'interval',hours=1); clean_up_scheduler.start()
def parse_render_parameters(): return request.args.get('pop_out','false').lower()=='true', max(0,min(6,float(request.args.get('max_disparity_percentage',2))))
def parse_swap_eyes(): return request.args.get('swap_eyes','false').lower()=='true'
def resize_image_and_depth(image,depth,max_dimension):
    h,w=image.shape[:2]; scale=min(1,max_dimension/max(h,w))
    if scale>=1:return image,depth
    nw,nh=max(1,round(w*scale)),max(1,round(h*scale)); return cv2.resize(image,(nw,nh),interpolation=cv2.INTER_AREA),np.clip(cv2.resize(depth.astype(np.float32),(nw,nh),interpolation=cv2.INTER_CUBIC),0,1).astype(np.float32)
def source_and_depth(scope='preview',max_dimension=PREVIEW_MAX_DIMENSION):
    ensure_depth_maps(); image=cv2.imread(session_path('image.png')); depth=np.load(session_path('depth_map.npy'),allow_pickle=False).astype(np.float32)
    if image is None: raise FileNotFoundError('No uploaded source image is available')
    return resize_image_and_depth(image,depth,max_dimension) if scope=='preview' else (image,depth)
def send_cv_image(image,filename,output_format='png',quality=95,download=False):
    fmt=output_format.lower(); ext='.jpg' if fmt in ('jpeg','jpg') else '.png'; args=[int(cv2.IMWRITE_JPEG_QUALITY),max(40,min(100,int(quality)))] if ext=='.jpg' else []; ok,encoded=cv2.imencode(ext,image,args)
    if not ok: raise RuntimeError('Could not encode output image')
    return send_file(io.BytesIO(encoded.tobytes()),mimetype='image/jpeg' if ext=='.jpg' else 'image/png',as_attachment=download,download_name=f"{filename.rsplit('.',1)[0]}{ext}")
def send_pil_png(image,filename,dpi,download=True):
    b=io.BytesIO(); image.save(b,format='PNG',dpi=(dpi,dpi)); b.seek(0); return send_file(b,mimetype='image/png',as_attachment=download,download_name=filename)
@app.route('/image',methods=['POST'])
def upload_image():
    if 'file' not in request.files:return jsonify({'error':'No file part'}),400
    f=request.files['file']; ext=f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else ''
    if ext not in ALLOWED_EXTENSIONS:return jsonify({'error':'Invalid file type'}),400
    try:
        im=ImageOps.exif_transpose(Image.open(f)).convert('RGB'); clear_session_products(); im.save(session_path('image.png'),format='PNG',optimize=False); return jsonify({'success':True,'width':im.width,'height':im.height,'full_resolution':True}),200
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/pattern',methods=['POST'])
def upload_pattern():
    try:
        p=ImageOps.exif_transpose(Image.open(request.files['file'])).convert('RGB'); p.thumbnail((1600,1600)); p.save(session_path('pattern.png')); return jsonify({'success':True}),200
    except Exception as e:return jsonify({'error':str(e)}),400
def save_active_depth(depth):
    depth=np.clip(depth,0,1).astype(np.float32); np.save(session_path('depth_map.npy'),depth,allow_pickle=False); colored=depth_map_generator.colour_depth_map(depth); preview,_=resize_image_and_depth(colored,depth,PREVIEW_MAX_DIMENSION); cv2.imwrite(session_path('depth_map_coloured.jpg'),preview); cv2.imwrite(session_path('depth_map_gray16.png'),np.round(depth*65535).astype(np.uint16)); clear_stereo_cache()
def get_ai_depth():
    p=session_path('depth_map_ai.npy')
    if os.path.exists(p):return np.load(p,allow_pickle=False).astype(np.float32)
    image=cv2.imread(session_path('image.png')); depth=np.clip(depth_map_generator.blur_depth_map(depth_map_generator.generate_depth_map(image),KERNEL_WIDTH),0,1).astype(np.float32); np.save(p,depth,allow_pickle=False); return depth
def ensure_depth_maps():
    if not os.path.exists(session_path('depth_map.npy')):save_active_depth(get_ai_depth())
@app.route('/depth-map')
def get_depth_map():
    try: ensure_depth_maps(); return send_from_directory(SESSION_DATA_FOLDER,os.path.basename(session_path('depth_map_coloured.jpg')),request.environ)
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/depth-map/import',methods=['POST'])
def import_depth_map():
    try:
        source=cv2.imread(session_path('image.png')); imported=load_depth_upload(request.files['file']); np.save(session_path('depth_map_import.npy'),imported,allow_pickle=False); mode=request.form.get('mode','crop'); invert=request.form.get('invert','false')=='true'; aligned=align_depth(imported,source.shape[1],source.shape[0],mode); save_active_depth(1-aligned if invert else aligned); return jsonify({'success':True}),200
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/depth-map/source',methods=['POST'])
def set_depth_source():
    try:
        p=request.get_json(silent=True) or request.form; source=cv2.imread(session_path('image.png')); name=str(p.get('source','ai')); depth=get_ai_depth() if name=='ai' else align_depth(np.load(session_path('depth_map_import.npy')),source.shape[1],source.shape[0],str(p.get('mode','crop'))); depth=1-depth if str(p.get('invert','false')).lower()=='true' else depth; save_active_depth(depth); return jsonify({'success':True}),200
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/depth-map/download')
def download_depth_map():
    ensure_depth_maps(); kind=request.args.get('kind','gray16')
    if kind=='gray16':return send_file(session_path('depth_map_gray16.png'),as_attachment=True,download_name='depth-map-16bit.png')
    if kind=='npy':return send_file(session_path('depth_map.npy'),as_attachment=True,download_name='depth-map-float32.npy')
    depth=np.load(session_path('depth_map.npy')); return send_cv_image(depth_map_generator.colour_depth_map(depth),'depth-map-color','png',100,True)
def cache_paths(scope):return {'left':session_path(f'{scope}_left.png'),'right':session_path(f'{scope}_right.png'),'meta':session_path(f'{scope}_stereo.json')}
def ensure_stereo_pair(scope,pop_out,strength):
    ensure_depth_maps(); paths=cache_paths(scope); image=cv2.imread(session_path('image.png')); depth=np.load(session_path('depth_map.npy'))
    if scope=='preview':image,depth=resize_image_and_depth(image,depth,PREVIEW_MAX_DIMENSION)
    left,right=anaglyph_generator.generate_stereo_images(image,depth,pop_out,strength); cv2.imwrite(paths['left'],left); cv2.imwrite(paths['right'],right); json.dump({'pop_out':pop_out,'max_disparity_percentage':strength,'width':image.shape[1],'height':image.shape[0]},open(paths['meta'],'w')); return paths
def stereo_arrays(scope,pop_out,strength,swap=False):
    p=ensure_stereo_pair(scope,pop_out,strength); l,r=cv2.imread(p['left']),cv2.imread(p['right']); return (r,l) if swap else (l,r)
@app.route('/render')
def render_preview_stereo():
    try: pop,strength=parse_render_parameters(); p=ensure_stereo_pair('preview',pop,strength); return jsonify({'success':True})
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/prepare-full')
def prepare_full_stereo():
    try: pop,strength=parse_render_parameters(); ensure_stereo_pair('full',pop,strength); return jsonify({'success':True})
    except Exception as e:return jsonify({'error':str(e)}),400
def build_output(kind,scope,pop,strength,optimised,swap=False,atype='red-cyan',acolor='full'):
    l,r=stereo_arrays(scope,pop,strength,swap)
    if kind=='left':return l
    if kind=='right':return r
    if kind=='parallel':return np.hstack((l,r))
    if kind=='cross':return np.hstack((r,l))
    if kind=='anaglyph':return anaglyph_generator.generate_optimised_RR_anaglyph(l,r) if optimised and atype=='red-cyan' and acolor=='full' else make_anaglyph(l,r,atype,acolor)
    return compatibility_stereo(l,r,kind)
@app.route('/output/<kind>')
def get_output(kind):
    try:
        pop,strength=parse_render_parameters(); out=build_output(kind,request.args.get('scope','preview'),pop,strength,request.args.get('optimised_RR_anaglyph','false')=='true',parse_swap_eyes(),request.args.get('anaglyph_type','red-cyan'),request.args.get('anaglyph_color','full')); return send_cv_image(out,kind,request.args.get('format','jpeg'),request.args.get('quality',95),request.args.get('download','false')=='true')
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/special/chromadepth')
def special_chromadepth():
    try: image,depth=source_and_depth(request.args.get('scope','preview')); return send_cv_image(technique_generator.chromadepth(image,depth,float(request.args.get('color_strength',90))/100,request.args.get('reverse','false')=='true'),'chromadepth',request.args.get('format','png'),95,request.args.get('download','false')=='true')
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/special/cardboard')
def special_cardboard():
    try: pop,s=parse_render_parameters(); l,r=stereo_arrays(request.args.get('scope','preview'),pop,s,parse_swap_eyes()); out=technique_generator.cardboard(l,r,int(request.args.get('width',1920)),int(request.args.get('height',1080)),float(request.args.get('screen_width_mm',121)),float(request.args.get('lens_separation_mm',63)),float(request.args.get('image_scale',92))/100); return send_cv_image(out,'cardboard-stereo','png',100,request.args.get('download','false')=='true')
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/special/stereoscope')
def special_stereoscope():
    try: pop,s=parse_render_parameters(); scope=request.args.get('scope','preview'); l,r=stereo_arrays(scope,pop,s,parse_swap_eyes()); out=technique_generator.stereoscope_card(l,r,dpi=int(request.args.get('dpi',300))); return send_cv_image(out,'stereoscope-card','png',100,request.args.get('download','false')=='true')
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/special/autostereogram')
def special_autostereogram():
    try: image,depth=source_and_depth(request.args.get('scope','preview')); style=request.args.get('style','random'); pattern=cv2.imread(session_path('pattern.png')) if style=='pattern' and os.path.exists(session_path('pattern.png')) else None; out=technique_generator.autostereogram(depth,style,float(request.args.get('separation',8)),float(request.args.get('depth_strength',2.3)),int(request.args.get('dot_size',3)),request.args.get('viewing','parallel')+('-guides' if request.args.get('guides','true')=='true' else ''),pattern,request.args.get('color','false')=='true'); return send_cv_image(out,f'{style}-stereogram','png',100,request.args.get('download','false')=='true')
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/special/wiggle')
def special_wiggle():
    try:
        pop,s=parse_render_parameters(); image,depth=source_and_depth('preview',1100); frames=technique_generator.wiggle_frames(image,depth,int(request.args.get('frames',7)),s,pop); pil=[Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB)) for f in frames]; b=io.BytesIO(); pil[0].save(b,format='GIF',save_all=True,append_images=pil[1:],duration=int(request.args.get('duration',75)),loop=0); b.seek(0); return send_file(b,mimetype='image/gif',as_attachment=request.args.get('download','false')=='true',download_name='wiggle-gram.gif')
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/special/lenticular')
def special_lenticular():
    try:
        scope=request.args.get('scope','preview'); pop,s=parse_render_parameters(); dpi=int(request.args.get('dpi',600)); wi=float(request.args.get('width_in',6)); hi=float(request.args.get('height_in',4)); fw,fh=int(wi*dpi),int(hi*dpi); image,depth=source_and_depth('full'); scale=min(1,1200/max(fw,fh)) if scope=='preview' else 1; out=technique_generator.lenticular(image,depth,int(fw*scale),int(fh*scale),int(dpi*scale),float(request.args.get('lpi',60)),int(request.args.get('views',6)),float(request.args.get('slant',0)),s,pop); return send_cv_image(out,'lenticular-interlaced','png',100,request.args.get('download','false')=='true')
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/special/phantogram')
def special_phantogram():
    try:
        scope=request.args.get('scope','preview'); pop,strength=parse_render_parameters(); dpi=int(request.args.get('dpi',300)); wi=float(request.args.get('print_width_in',10)); hi=float(request.args.get('print_height_in',7.5)); fw=max(600,int(wi*dpi*2)); fh=max(400,int(hi*dpi)); scale=min(1,1400/max(fw,fh)) if scope=='preview' else 1; image,depth=source_and_depth('full'); out=technique_generator.phantogram(image,depth,int(fw*scale),int(fh*scale),float(request.args.get('viewing_distance_in',20))*25.4,float(request.args.get('eye_height_in',14))*25.4,float(request.args.get('eye_separation_mm',63)),wi*25.4,hi*25.4,pop,strength); return send_cv_image(out,'phantogram','png',100,request.args.get('download','false')=='true')
    except Exception as e:return jsonify({'error':str(e)}),400
@app.route('/lenticular/calibration')
def lenticular_calibration(): return send_pil_png(technique_generator.lenticular_calibration(),'lenticular-calibration.png',600,True)
@app.route('/anaglyph')
def legacy_anaglyph():return get_output('anaglyph')
@app.route('/stereo-pair')
def legacy_stereo_pair():return get_output(request.args.get('mode','parallel'))
if __name__=='__main__':app.run(debug=os.getenv('FLASK_DEBUG','false')=='true',host=host,port=port)
