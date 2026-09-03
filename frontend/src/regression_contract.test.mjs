import fs from 'node:fs';
const read=(p)=>fs.readFileSync(new URL(p,import.meta.url),'utf8');
const editor=read('./AnaglyphEditor.tsx');
const controls=read('./TechniqueControls.tsx');
const app=read('./App.tsx');
const main=read('./main.tsx');
const required=[
 [editor,'downloadEye','eye downloads'],[editor,'requestFullscreen','fullscreen'],[editor,"event.key.toLowerCase()",'keyboard shortcuts'],[editor,'optimiseRRAnaglyph','retinal rivalry'],[editor,'jpegQuality','JPEG quality'],[editor,'randomdot','random-dot'],[editor,'lenticular','lenticular'],[editor,'cardboard','Cardboard'],[editor,'stereoscope','stereoscope'],
 [controls,'Build a new random-dot pattern','random-dot rebuild'],[controls,'Download black/white calibration bars','lenticular calibration'],[controls,'Custom repeating pattern','pattern upload'],[controls,'Color rendering','anaglyph color slider'],
 [app,'ViewMasterBuilder','View-Master workspace'],[app,'sidebarCollapsed','collapsible sidebar'],[main,'scheduleTechniqueAutoApply','automatic discrete setting apply']
];
let failed=false;for(const [text,needle,label] of required){if(!text.includes(needle)){console.error(`Missing established feature contract: ${label} (${needle})`);failed=true;}}
if(failed)process.exit(1);console.log(`Established feature contract passed (${required.length} checks)`);
