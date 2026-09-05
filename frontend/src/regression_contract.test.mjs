import fs from 'node:fs';
const read=(p)=>fs.readFileSync(new URL(p,import.meta.url),'utf8');
const editor=read('./AnaglyphEditor.tsx');
const controls=read('./TechniqueControls.tsx');
const app=read('./App.tsx');
const main=read('./main.tsx');
const phantogram=read('./PhantogramBuilder.tsx');
const viewMaster=read('./ViewMasterBuilder.tsx');
const viewMasterPdf=read('./viewMasterPdf.ts');
const feedbackCss=read('./styles/FeedbackFixes.css');
const required=[
 [editor,'downloadEye','eye downloads'],[editor,'requestFullscreen','fullscreen'],[editor,"event.key.toLowerCase()",'keyboard shortcuts'],[editor,'optimiseRRAnaglyph','retinal rivalry'],[editor,'jpegQuality','JPEG quality'],[editor,'randomdot','random-dot'],[editor,'lenticular','lenticular'],[editor,'cardboard','Cardboard'],[editor,'stereoscope','stereoscope'],
 [controls,'Build a new random-dot pattern','random-dot rebuild'],[controls,'Download black/white calibration bars','lenticular calibration'],[controls,'Custom repeating pattern','pattern upload'],[controls,'Color rendering','anaglyph color slider'],[controls,'Black text on white','stereoscope light card'],[controls,'White text on black','stereoscope dark card'],
 [app,'ViewMasterBuilder','View-Master workspace'],[app,'PhantogramBuilder','Phantogram workspace'],[app,'sidebarCollapsed','collapsible sidebar'],[main,'scheduleTechniqueAutoApply','automatic discrete setting apply'],[main,'FeedbackFixes.css','feedback polish stylesheet'],
 [feedbackCss,'position: sticky','sticky output preview'],[feedbackCss,'repeat(2, minmax(0, 1fr))','equal stereoscope treatment buttons'],
 [phantogram,'100 mm ruler','phantogram print calibration'],[phantogram,'reverseDepth','phantogram depth reversal'],[phantogram,'scope=full','phantogram full-resolution export'],
 [viewMaster,'const rotation = scene * SCENE_STEP_DEG + imageRotation','View-Master pair-level rotation'],[viewMaster,"0° · upright at 3/9 o'clock",'View-Master upright reference pair'],[viewMaster,'Download PDF print master','View-Master PDF primary export'],[viewMaster,'Download SVG (secondary)','View-Master SVG secondary export'],[viewMaster,'fill="#fff"','View-Master pure-white cardstock'],[viewMaster,'prototype geometry','View-Master prototype labeling'],
 [viewMasterPdf,'PT_PER_MM = 72 / 25.4','View-Master physical PDF scale'],[viewMasterPdf,'/Subtype /Image','View-Master embedded PDF raster images'],[viewMasterPdf,"type: 'application/pdf'",'View-Master PDF output'],[viewMasterPdf,'const rotation = scene * SCENE_STEP_DEG + imageRotation','View-Master PDF pair-level rotation']
];
let failed=false;for(const [text,needle,label] of required){if(!text.includes(needle)){console.error(`Missing established feature contract: ${label} (${needle})`);failed=true;}}
if(failed)process.exit(1);console.log(`Established feature contract passed (${required.length} checks)`);
