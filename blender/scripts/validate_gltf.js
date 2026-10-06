// Structural validation of an exported pack with the Khronos glTF-Validator (https://github.com/KhronosGroup/glTF-Validator).
//   npm install gltf-validator      (once, outside the repo is fine)
//   node validate_gltf.js library/humanoid/hair/front/blunt/blunt.gltf
// Prints errors, warnings and the validator's own counts (triangles, materials, skin influences). Fix every error before import.
const v=require('gltf-validator'),fs=require('fs');
const f=process.argv[2];
v.validateBytes(new Uint8Array(fs.readFileSync(f)),{uri:f,externalResourceFunction:(uri)=>new Promise((res,rej)=>{const p=require('path').resolve(require('path').dirname(f),decodeURIComponent(uri));fs.readFile(p,(e,d)=>e?rej(e):res(new Uint8Array(d)))})}).then(r=>{const m=r.issues.messages;console.log(JSON.stringify({numErrors:r.issues.numErrors,numWarnings:r.issues.numWarnings,numInfos:r.issues.numInfos,info:r.info&&{generator:r.info.generator,drawCallCount:r.info.drawCallCount,totalVertexCount:r.info.totalVertexCount,totalTriangleCount:r.info.totalTriangleCount,materialCount:r.info.materialCount,animationCount:r.info.animationCount,maxInfluences:r.info.maxInfluences,hasSkins:r.info.hasSkins}, first:m.slice(0,6).map(x=>x.code+' '+x.pointer+' '+x.message)},null,1))}).catch(e=>console.log('ERR',e.message));
