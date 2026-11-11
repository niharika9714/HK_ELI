// Data reaches these renderers only after Python validates actual axes and metric capabilities.
const ns='http://www.w3.org/2000/svg';
function shape(tag,attrs={},text){const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n;}
export function chart(data){
  const rows=data.rows||[],type=data.chart;if(!rows.length||type==='table'||!type)return null;
  const keys=data.columns||Object.keys(rows[0]),dims=keys.filter(k=>k!=='value'),values=rows.map(r=>Number(r.value));
  if(values.some(v=>!Number.isFinite(v)))return null;
  const svg=shape('svg',{viewBox:'0 0 740 420',role:'img','aria-label':`${type}: ${data.measure||'value'}`});
  const colors=['#276d59','#6b9f85','#b3cfaa','#d8b467','#497c96','#9983ae'];
  svg.append(shape('text',{x:20,y:20},`${data.measure||'Value'} (${data.unit||'unknown unit'})`));
  if(type==='pie'){
    const total=values.reduce((a,b)=>a+b,0);let angle=-Math.PI/2;
    rows.forEach((r,i)=>{const end=angle+values[i]/total*2*Math.PI,cx=210,cy=220,radius=150;
      const path=shape('path',{d:values[i]===total?`M ${cx-radius},${cy} a ${radius},${radius} 0 1,0 ${radius*2},0 a ${radius},${radius} 0 1,0 -${radius*2},0`:`M ${cx},${cy} L ${cx+radius*Math.cos(angle)},${cy+radius*Math.sin(angle)} A ${radius},${radius} 0 ${end-angle>Math.PI?1:0},1 ${cx+radius*Math.cos(end)},${cy+radius*Math.sin(end)} Z`,fill:colors[i%colors.length]});
      path.append(shape('title',{},`${r[dims[0]]}: ${r.value}`));svg.append(path,shape('text',{x:400,y:55+i*17},`${r[dims[0]]}: ${r.value}`));angle=end;});
  }else if(type==='heatmap'){
    const xs=[...new Set(rows.map(r=>r[dims[0]]))],ys=[...new Set(rows.map(r=>r[dims[1]]))],max=Math.max(...values.map(Math.abs),1);
    rows.forEach((r,i)=>{const cell=shape('rect',{x:120+xs.indexOf(r[dims[0]])*550/xs.length,y:50+ys.indexOf(r[dims[1]])*300/ys.length,width:550/xs.length-2,height:300/ys.length-2,fill:'#276d59',opacity:.15+.85*Math.abs(values[i])/max});cell.append(shape('title',{},`${r[dims[0]]}, ${r[dims[1]]}: ${r.value}`));svg.append(cell);});
    xs.forEach((v,i)=>svg.append(shape('text',{x:120+i*550/xs.length,y:375},String(v).slice(0,16))));ys.forEach((v,i)=>svg.append(shape('text',{x:0,y:65+i*300/ys.length},String(v).slice(0,18))));
  }else{
    const min=Math.min(0,...values),max=Math.max(0,...values),span=max-min||1,y=v=>350-(v-min)/span*290,x=i=>100+i*560/Math.max(rows.length-1,1);
    svg.append(shape('line',{x1:80,y1:y(0),x2:700,y2:y(0),stroke:'#a4b8ad'}));
    if(type==='line')svg.append(shape('polyline',{points:values.map((v,i)=>`${x(i)},${y(v)}`).join(' '),fill:'none',stroke:colors[0],'stroke-width':3}));
    rows.forEach((r,i)=>{const mark=type==='line'?shape('circle',{cx:x(i),cy:y(values[i]),r:4,fill:colors[0]}):shape('rect',{x:90+i*600/rows.length,y:Math.min(y(0),y(values[i])),width:Math.max(2,550/rows.length),height:Math.abs(y(0)-y(values[i])),fill:colors[i%colors.length]});mark.append(shape('title',{},`${dims.map(d=>r[d]).join(' / ')}: ${r.value}`));svg.append(mark);if(rows.length<=12)svg.append(shape('text',{x:type==='line'?x(i):90+i*600/rows.length,y:380},dims.map(d=>r[d]).join('/').slice(0,14)));});
    svg.append(shape('text',{x:5,y:60},String(max)),shape('text',{x:5,y:350},String(min)));
  }
  return svg;
}
