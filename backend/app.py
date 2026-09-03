from flask import Flask, jsonify, request, session, send_file
from flask_cors import CORS
import uuid
import os
import io
import json
import time
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

app = Flask(__name__)
CORS(app, supports_credentials=True)
load_dotenv()
host = os.getenv("FLASK_HOST", "0.0.0.0")
port = int(os.getenv("FLASK_PORT", 8000))
app.secret_key = os.getenv("FLASK_SECRET_KEY", "local-anaglyph-and-friends")
KERNEL_WIDTH = 15
PREVIEW_MAX_DIMENSION = 1600
SESSION_DATA_FOLDER = "resources/session_data"
os.makedirs(SESSION_DATA_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"bmp", "dib", "jpeg", "jpg", "jpe", "jp2", "png", "webp", "pbm", "pgm", "ppm", "pxm", "pnm", "sr", "ras", "tiff", "tif", "exr", "hdr", "pic"}

@app.route("/")
def hello_world(): return "Anaglyph & Friends backend"
@app.before_request
def assign_session_id():
    if "session_id" not in session: session["session_id"] = str(uuid.uuid4())
def session_path(suffix: str) -> str: return os.path.join(SESSION_DATA_FOLDER, f"{session['session_id']}_{suffix}")
def clear_session_products():
    prefix=f"{session['session_id']}_"
    for filename in os.listdir(SESSION_DATA_FOLDER):
        if filename.startswith(prefix):
            try: os.remove(os.path.join(SESSION_DATA_FOLDER,filename))
            except FileNotFoundError: pass
def clear_stereo_cache():
    for suffix in ("preview_left.png","preview_right.png","preview_stereo.json","full_left.png","full_right.png","full_stereo.json"):
        try: os.remove(session_path(suffix))
        except FileNotFoundError: pass
def clear_old_session_files():
    current_time=time.time(); count=0
    for filename in os.listdir(SESSION_DATA_FOLDER):
        path=os.path.join(SESSION_DATA_FOLDER,filename)
        if os.path.isfile(path) and current_time-os.path.getmtime(path)>3600: os.remove(path); count+=1
    print(f"Session files cleared: {count}")
clean_up_scheduler=BackgroundScheduler(); clean_up_scheduler.add_job(clear_old_session_files,"interval",hours=1); clean_up_scheduler.start()
def parse_render_parameters():
    pop=request.args.get("pop_out","false").lower()=="true"; strength=max(0.0,min(6.0,float(request.args.get("max_disparity_percentage",2)))); return pop,strength
def parse_swap_eyes(): return request.args.get("swap_eyes","false").lower()=="true"
def resize_image_and_depth(image,depth,max_dimension):
    h,w=image.shape[:2]; scale=min(1.0,max_dimension/max(h,w))
    if scale>=1:return image,depth
    nw=max(1,int(round(w*scale))); nh=max(1,int(round(h*scale))); return cv2.resize(image,(nw,nh),interpolation=cv2.INTER_AREA),np.clip(cv2.resize(depth.astype(np.float32),(nw,nh),interpolation=cv2.INTER_CUBIC),0,1).astype(np.float32)
def source_and_depth(scope="preview",max_dimension=PREVIEW_MAX_DIMENSION):
    ensure_depth_maps(); image=cv2.imread(session_path("image.png")); depth=np.load(session_path("depth_map.npy"),allow_pickle=False).astype(np.float32)
    if image is None: raise FileNotFoundError("No uploaded source image is available")
    return resize_image_and_depth(image,depth,max_dimension) if scope=="preview" else (image,depth)
def send_cv_image(image,filename,output_format="png",quality=95,download=False):
    fmt=output_format.lower(); quality=max(40,min(100,int(quality)))
    if fmt in ("jpeg","jpg"): ok,encoded=cv2.imencode(".jpg",image,[int(cv2.IMWRITE_JPEG_QUALITY),quality]); mime="image/jpeg"; ext="jpg"
    else: ok,encoded=cv2.imencode(".png",image); mime="image/png"; ext="png"
    if not ok: raise RuntimeError("Could not encode output image")
    return send_file(io.BytesIO(encoded.tobytes()),mimetype=mime,as_attachment=download,download_name=f"{filename.rsplit('.',1)[0]}.{ext}")
def send_pil_png(image,filename,dpi,download=True):
    buffer=io.BytesIO(); image.save(buffer,format="PNG",dpi=(dpi,dpi)); buffer.seek(0); return send_file(buffer,mimetype="image/png",as_attachment=download,download_name=filename)
@app.route("/image",methods=["POST"])
def upload_image():
    if "file" not in request.files:return jsonify({"error":"No file part"}),400
    image=request.files["file"]; extension=image.filename.rsplit(".",1)[-1].lower() if "." in image.filename else ""
    if extension not in ALLOWED_EXTENSIONS:return jsonify({"error":"Invalid file type"}),400
    try:
        pillow=ImageOps.exif_transpose(Image.open(image)).convert("RGB"); clear_session_products(); pillow.save(session_path("image.png"),format="PNG",optimize=False); return jsonify({"success":True,"width":pillow.width,"height":pillow.height,"full_resolution":True}),200
    except Exception as e:return jsonify({"error":str(e)+" Note: transparent background not allowed"}),400
@app.route("/pattern",methods=["POST"])
def upload_pattern():
    if "file" not in request.files:return jsonify({"error":"No pattern file"}),400
    try:
        pattern=ImageOps.exif_transpose(Image.open(request.files["file"])).convert("RGB"); pattern.thumbnail((1600,1600),Image.Resampling.LANCZOS); pattern.save(session_path("pattern.png"),format="PNG"); return jsonify({"success":True,"width":pattern.width,"height":pattern.height}),200
    except Exception as e:return jsonify({"error":str(e)}),400
def save_active_depth(depth):
    depth=np.clip(depth,0,1).astype(np.float32); np.save(session_path("depth_map.npy"),depth,allow_pickle=False); colored=depth_map_generator.colour_depth_map(depth); preview,_=resize_image_and_depth(colored,depth,PREVIEW_MAX_DIMENSION); cv2.imwrite(session_path("depth_map_coloured.jpg"),preview,[int(cv2.IMWRITE_JPEG_QUALITY),92]); cv2.imwrite(session_path("depth_map_gray16.png"),np.round(depth*65535).astype(np.uint16)); clear_stereo_cache()
def get_ai_depth():
    path=session_path("depth_map_ai.npy")
    if os.path.exists(path):return np.load(path,allow_pickle=False).astype(np.float32)
    image=cv2.imread(session_path("image.png"));
    if image is None:raise FileNotFoundError("No uploaded source image is available")
    depth=np.clip(depth_map_generator.blur_depth_map(depth_map_generator.generate_depth_map(image),KERNEL_WIDTH),0,1).astype(np.float32); np.save(path,depth,allow_pickle=False); return depth
def ensure_depth_maps():
    if all(os.path.exists(session_path(x)) for x in ("depth_map.npy","depth_map_coloured.jpg","depth_map_gray16.png")):return
    save_active_depth(get_ai_depth())
@app.route("/depth-map",methods=["GET"])
def get_depth_map():
    try:ensure_depth_maps(); return send_from_directory(SESSION_DATA_FOLDER,os.path.basename(session_path("depth_map_coloured.jpg")),request.environ)
    except Exception as e:return jsonify({"error":str(e)}),400
@app.route("/depth-map/import",methods=["POST"])
def import_depth_map():
    if "file" not in request.files:return jsonify({"error":"No depth map file"}),400
    try:
        source=cv2.imread(session_path("image.png")); imported=load_depth_upload(request.files["file"]); np.save(session_path("depth_map_import.npy"),imported,allow_pickle=False); mode=request.form.get("mode","crop").lower(); invert=request.form.get("invert","false").lower()=="true"; aligned=align_depth(imported,source.shape[1],source.shape[0],mode); save_active_depth(1-aligned if invert else aligned); return jsonify({"success":True,"depth_width":int(imported.shape[1]),"depth_height":int(imported.shape[0]),"source_width":int(source.shape[1]),"source_height":int(source.shape[0]),"mode":mode,"invert":invert}),200
    except Exception as e:return jsonify({"error":str(e)}),400
@app.route("/depth-map/source",methods=["POST"])
def set_depth_source():
    try:
        payload=request.get_json(silent=True) or request.form; source_name=str(payload.get("source","ai")).lower(); mode=str(payload.get("mode","crop")).lower(); invert=str(payload.get("invert","false")).lower()=="true"; source=cv2.imread(session_path("image.png"))
        if source_name=="ai":depth=get_ai_depth()
        elif source_name=="imported":depth=align_depth(np.load(session_path("depth_map_import.npy"),allow_pickle=False).astype(np.float32),source.shape[1],source.shape[0],mode)
        else:return jsonify({"error":"source must be ai or imported"}),400
        save_active_depth(1-depth if invert else depth); return jsonify({"success":True,"source":source_name,"mode":mode,"invert":invert}),200
    except Exception as e:return jsonify({"error":str(e)}),400
@app.route("/depth-map/download",methods=["GET"])
def download_depth_map():
    try:
        ensure_depth_maps(); kind=request.args.get("kind","gray16").lower()
        if kind=="gray16":return send_file(session_path("depth_map_gray16.png"),as_attachment=True,download_name="depth-map-16bit.png",mimetype="image/png")
        if kind=="npy":return send_file(session_path("depth_map.npy"),as_attachment=True,download_name="depth-map-float32.npy",mimetype="application/octet-stream")
        if kind=="color":return send_cv_image(depth_map_generator.colour_depth_map(np.load(session_path("depth_map.npy"))),"depth-map-color","png",100,True)
        return jsonify({"error":"kind must be gray16, color, or npy"}),400
    except Exception as e:return jsonify({"error":str(e)}),400
def cache_paths(scope):
    if scope not in ("preview","full"):raise ValueError("scope must be preview or full")
    return {"left":session_path(f"{scope}_left.png"),"right":session_path(f"{scope}_right.png"),"meta":session_path(f"{scope}_stereo.json")}
def cache_matches(meta_path,pop,strength):
    try:
        with open(meta_path,"r",encoding="utf-8") as handle:meta=json.load(handle)
        return bool(meta.get("pop_out"))==bool(pop) and abs(float(meta.get("max_disparity_percentage"))-float(strength))<1e-9
    except (OSError,ValueError,TypeError,json.JSONDecodeError):return False
def ensure_stereo_pair(scope,pop,strength):
    ensure_depth_maps(); paths=cache_paths(scope)
    if os.path.exists(paths["left"]) and os.path.exists(paths["right"]) and cache_matches(paths["meta"],pop,strength):return paths
    image=cv2.imread(session_path("image.png")); depth=np.load(session_path("depth_map.npy"),allow_pickle=False).astype(np.float32)
    if scope=="preview":image,depth=resize_image_and_depth(image,depth,PREVIEW_MAX_DIMENSION)
    left,right=anaglyph_generator.generate_stereo_images(image,depth,pop,strength); cv2.imwrite(paths["left"],left); cv2.imwrite(paths["right"],right)
    with open(paths["meta"],"w",encoding="utf-8") as handle:json.dump({"pop_out":pop,"max_disparity_percentage":strength,"width":int(image.shape[1]),"height":int(image.shape[0])},handle)
    return paths
def stereo_arrays(scope,pop,strength,swap=False):
    paths=ensure_stereo_pair(scope,pop,strength); left=cv2.imread(paths["left"]); right=cv2.imread(paths["right"]); return (right,left) if swap else (left,right)
@app.route("/render",methods=["GET"])
def render_preview_stereo():
    try:
        pop,strength=parse_render_parameters(); paths=ensure_stereo_pair("preview",pop,strength)
        with open(paths["meta"],"r") as handle:meta=json.load(handle)
        return jsonify({"success":True,"scope":"preview",**meta})
    except Exception as e:return jsonify({"error":str(e)}),400
@app.route("/prepare-full",methods=["GET"])
def prepare_full_stereo():
    try:
        pop,strength=parse_render_parameters(); paths=ensure_stereo_pair("full",pop,strength)
        with open(paths["meta"],"r") as handle:meta=json.load(handle)
        return jsonify({"success":True,"scope":"full",**meta})
    except Exception as e:return jsonify({"error":str(e)}),400
def build_output(kind,scope,pop,strength,optimised,swap=False,atype="red-cyan",acolor="full"):
    left,right=stereo_arrays(scope,pop,strength,swap)
    if kind=="left":return left
    if kind=="right":return right
    if kind=="parallel":return np.hstack((left,right))
    if kind=="cross":return np.hstack((right,left))
    if kind=="anaglyph":return anaglyph_generator.generate_optimised_RR_anaglyph(left,right) if optimised and atype=="red-cyan" and acolor=="full" else make_anaglyph(left,right,atype,acolor)
    if kind in {"topbottom","halfsbs","rowinterlaced","columninterlaced","checkerboard"}:return compatibility_stereo(left,right,kind)
    raise ValueError("Unknown stereo output kind")
@app.route("/output/<kind>",methods=["GET"])
def get_output(kind):
    try:
        scope=request.args.get("scope","preview").lower(); pop,strength=parse_render_parameters(); out=build_output(kind.lower(),scope,pop,strength,request.args.get("optimised_RR_anaglyph","false").lower()=="true",parse_swap_eyes(),request.args.get("anaglyph_type","red-cyan").lower(),request.args.get("anaglyph_color","full").lower()); return send_cv_image(out,kind,request.args.get("format","jpeg"),request.args.get("quality",95),request.args.get("download","false").lower()=="true")
    except Exception as e:return jsonify({"error":str(e)}),400
@app.route("/special/chromadepth",methods=["GET"])
def special_chromadepth():
    try:
        image,depth=source_and_depth(request.args.get("scope","preview").lower()); out=technique_generator.chromadepth(image,depth,float(request.args.get("color_strength",90))/100,request.args.get("reverse","false").lower()=="true"); return send_cv_image(out,"chromadepth",request.args.get("format","png"),request.args.get("quality",95),request.args.get("download","false").lower()=="true")
    except Exception as e:return jsonify({"error":str(e)}),400
@app.route("/special/cardboard",methods=["GET"])
def special_cardboard():
    try:
        pop,strength=parse_render_parameters(); left,right=stereo_arrays(request.args.get("scope","preview"),pop,strength,parse_swap_eyes()); out=technique_generator.cardboard(left,right,int(request.args.get("width",1920)),int(request.args.get("height",1080)),float(request.args.get("screen_width_mm",121)),float(request.args.get("lens_separation_mm",63)),float(request.args.get("image_scale",92))/100); return send_cv_image(out,"cardboard-stereo",request.args.get("format","png"),request.args.get("quality",95),request.args.get("download","false").lower()=="true")
    except Exception as e:return jsonify({"error":str(e)}),400
@app.route("/special/stereoscope",methods=["GET"])
def special_stereoscope():
    try:
        pop,strength=parse_render_parameters(); scope=request.args.get("scope","preview"); dpi=int(request.args.get("dpi",300)); render_dpi=min(dpi,180) if scope=="preview" else dpi; left,right=stereo_arrays("preview" if scope=="preview" else "full",pop,strength,parse_swap_eyes()); out=technique_generator.stereoscope_card(left,right,dpi=render_dpi,card_width_in=float(request.args.get("card_width",7)),card_height_in=float(request.args.get("card_height",3.5)),image_width_in=float(request.args.get("image_width",2.85)),image_height_in=float(request.args.get("image_height",2.55)),gap_in=float(request.args.get("gap",.35)),arch_in=float(request.args.get("arch",.22)),title=request.args.get("title","STEREOSCOPIC VIEW"),caption=request.args.get("caption","Generated from a single photograph"),publisher=request.args.get("publisher","Anaglyph & Friends"),card_tone=request.args.get("card_tone","cream")); return send_cv_image(out,"stereoscope-card","png",100,request.args.get("download","false").lower()=="true")
    except Exception as e:return jsonify({"error":str(e)}),400
@app.route("/special/autostereogram",methods=["GET"])
def special_autostereogram():
    try:
        scope=request.args.get("scope","preview"); style=request.args.get("style","random"); image,depth=source_and_depth(scope); pattern=cv2.imread(session_path("pattern.png")) if style=="pattern" and os.path.exists(session_path("pattern.png")) else None; out=technique_generator.autostereogram(depth,style=style,separation_percent=float(request.args.get("separation",8)),depth_percent=float(request.args.get("depth_strength",2.3)),dot_size=int(request.args.get("dot_size",3)),viewing=request.args.get("viewing","parallel")+("-guides" if request.args.get("guides","true")=="true" else ""),pattern=pattern,color=request.args.get("color","false")=="true"); return send_cv_image(out,f"{style}-stereogram",request.args.get("format","png"),request.args.get("quality",95),request.args.get("download","false")=="true")
    except Exception as e:return jsonify({"error":str(e)}),400
@app.route("/special/wiggle",methods=["GET"])
def special_wiggle():
    try:
        pop,strength=parse_render_parameters(); strength=-strength if parse_swap_eyes() else strength; image,depth=source_and_depth("preview",1100); frames=technique_generator.wiggle_frames(image,depth,int(request.args.get("frames",7)),strength,pop); pil=[Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)) for frame in frames]; buffer=io.BytesIO(); pil[0].save(buffer,format="GIF",save_all=True,append_images=pil[1:],duration=max(40,min(1000,int(request.args.get("duration",75)))),loop=0,disposal=2,optimize=False); buffer.seek(0); return send_file(buffer,mimetype="image/gif",as_attachment=request.args.get("download","false")=="true",download_name="wiggle-gram.gif")
    except Exception as e:return jsonify({"error":str(e)}),400
@app.route("/special/lenticular",methods=["GET"])
def special_lenticular():
    try:
        scope=request.args.get("scope","preview"); pop,strength=parse_render_parameters(); strength=-strength if parse_swap_eyes() else strength; dpi=int(request.args.get("dpi",600)); lpi=float(request.args.get("lpi",60)); wi=float(request.args.get("width_in",6)); hi=float(request.args.get("height_in",4)); views=int(request.args.get("views",6)); slant=float(request.args.get("slant",0)); fw=max(300,int(round(wi*dpi))); fh=max(200,int(round(hi*dpi))); image,depth=source_and_depth("full"); scale=min(1,1200/max(fw,fh)) if scope=="preview" else 1; out=technique_generator.lenticular(image,depth,max(300,int(round(fw*scale))),max(200,int(round(fh*scale))),max(72,int(round(dpi*scale))),lpi,views,slant,strength,pop); return send_cv_image(out,"lenticular-interlaced","png",100,request.args.get("download","false")=="true")
    except Exception as e:return jsonify({"error":str(e)}),400

@app.route("/special/phantogram",methods=["GET"])
def special_phantogram():
    try:
        scope=request.args.get("scope","preview").lower(); pop,strength=parse_render_parameters(); dpi=max(72,min(1200,int(request.args.get("dpi",300)))); width_in=max(2.0,min(20.0,float(request.args.get("print_width_in",10)))); height_in=max(2.0,min(20.0,float(request.args.get("print_height_in",7.5)))); full_eye_w=max(300,int(round(width_in*dpi))); full_h=max(300,int(round(height_in*dpi))); scale=min(1.0,700.0/max(full_eye_w,full_h)) if scope=="preview" else 1.0; eye_w=max(300,int(round(full_eye_w*scale))); out_h=max(300,int(round(full_h*scale))); image,depth=source_and_depth("full"); output=technique_generator.phantogram(image,depth,eye_w*2,out_h,view_distance_mm=float(request.args.get("viewing_distance_in",20))*25.4,eye_height_mm=float(request.args.get("eye_height_in",14))*25.4,eye_separation_mm=float(request.args.get("eye_separation_mm",63)),print_width_mm=width_in*25.4,print_height_mm=height_in*25.4,pop_out=pop,strength=strength); return send_cv_image(output,"phantogram","png",100,request.args.get("download","false").lower()=="true")
    except Exception as e:return jsonify({"error":str(e)}),400

@app.route("/lenticular/calibration",methods=["GET"])
def lenticular_calibration():
    try:
        dpi=int(request.args.get("dpi",600)); image=technique_generator.lenticular_calibration(dpi=dpi,nominal_lpi=float(request.args.get("lpi",60)),span=float(request.args.get("span",.5)),step=float(request.args.get("step",.1)),width_in=float(request.args.get("width_in",8))); return send_pil_png(image,"lenticular-calibration.png",dpi,True)
    except Exception as e:return jsonify({"error":str(e)}),400
@app.route("/anaglyph",methods=["GET"])
def legacy_anaglyph():return get_output("anaglyph")
@app.route("/stereo-pair",methods=["GET"])
def legacy_stereo_pair():
    mode=request.args.get("mode","parallel").lower()
    if mode not in ("parallel","cross"):return jsonify({"error":"mode must be parallel or cross"}),400
    return get_output(mode)
if __name__=="__main__": app.run(debug=os.getenv("FLASK_DEBUG","false").lower()=="true",host=host,port=port)
