const fs=require('fs'); const lines=fs.readFileSync(process.argv[2],'utf8').split('\n');
let out=[];
for(let i=0;i<lines.length;i++){ if(i===lines.length-1&&lines[i]==='')break; const p=lines[i];
  const input=fs.readFileSync(p,'utf8');
  let rc=1; try{ JSON.parse(input); rc=0;}catch(e){if(!(e instanceof SyntaxError))throw e;} out.push(i+' '+rc);}
process.stdout.write(out.join('\n')+'\n');
