// Mock mínimo de supabase-js para probar el flujo remoto
(function(){
 const DB=window.__DB={profiles:[],players:[{id:1,n:'Raúl',p:'POR',d:null,dem:'Portero',pie:'Diestro',cual:null,seasons:['2026/27']},{id:2,n:'Gonzalo',p:'DEF',d:null,dem:'Lateral izquierdo',pie:'Zurdo',cual:'Rápido',seasons:['2026/27']},{id:6,n:'Nico',p:'DEL',d:null,dem:'Delantero',pie:'Diestro',cual:null,seasons:['2026/27']},{id:5,n:'Tadeo',p:'MED',d:null,dem:'Mediocentro',pie:'Diestro',cual:null,seasons:['2026/27']},{id:3,n:'Lucas',p:'DEF',d:null,dem:'Central',pie:'Diestro',cual:null,seasons:['2026/27']}],matches:[],ratings:[],trainings:[],settings:[{key:'seasons',value:'["2026/27"]'},{key:'season',value:'2026/27'}],media:[],messages:[],audit_log:[]};const FILES={};let MID=1;
 let cb=null,sess=null,subs=[];
 const fire=()=>setTimeout(()=>subs.forEach(f=>f()),10);
 window.__login=(id)=>{sess={user:{id,email:id+'@x.es'}};cb&&cb('SIGNED_IN',sess)};
 window.__fire=fire;
 function Q(t){this.t=t;this.f=[];this.op='select'}
 Q.prototype.select=function(){return this};Q.prototype.order=function(){return this};Q.prototype.limit=function(){return this};
 Q.prototype.eq=function(k,v){this.f.push([k,v]);return this};
 Q.prototype.maybeSingle=function(){this.single=1;return this};
 Q.prototype.insert=function(r){this.op='insert';this.row=r;return this};
 Q.prototype.upsert=function(r){this.op='upsert';this.row=r;return this};
 Q.prototype.update=function(r){this.op='update';this.row=r;return this};
 Q.prototype.delete=function(){this.op='delete';return this};
 Q.prototype.then=function(res,rej){const T=DB[this.t],m=x=>this.f.every(([k,v])=>x[k]==v);let out={error:null,data:null};
  if(this.op==='select'){const d=JSON.parse(JSON.stringify(T.filter(m)));out.data=this.single?(d[0]||null):d}
  else if(this.op==='insert'){const r={...this.row};if(this.t==='profiles'){r.approved=r.role==='entrenador'&&!T.some(x=>x.approved&&(x.role==='entrenador'||x.admin));r.admin=false;r.created_at=Date.now()}if(this.t==='messages'){const me=DB.profiles.find(p=>p.id===sess.user.id);r.id=MID++;r.author=sess.user.id;r.author_name=me?me.nombre:'?';r.author_info=me&&me.role==='entrenador'?'Entrenador':'Familia';r.created_at=new Date(Date.now()+MID).toISOString()}if(this.t==='media'){const me=DB.profiles.find(p=>p.id===sess.user.id);r.uploader=sess.user.id;r.approved=!!me&&(me.role==='entrenador'||me.admin);r.created_at=new Date().toISOString()}T.push(r);fire()}
  else if(this.op==='upsert'){if(['players','matches'].includes(this.t)){const ex=T.find(x=>x.id==this.row.id);const me=DB.profiles.find(p=>p.id===sess?.user?.id);DB.audit_log.unshift({id:Date.now(),at:new Date().toISOString(),actor:sess.user.id,actor_name:me?me.nombre+' '+me.apellidos:'?',tbl:this.t,action:ex?'UPDATE':'INSERT',old:ex?JSON.parse(JSON.stringify(ex)):null,new:{...(ex||{}),...this.row}})}const key=this.t==='ratings'?['match_id','player_id']:this.t==='settings'?['key']:['id'];const i=T.findIndex(x=>key.every(k=>x[k]==this.row[k]));if(i>=0)Object.assign(T[i],this.row);else T.push({...this.row});fire()}
  else if(this.op==='update'){T.filter(m).forEach(x=>Object.assign(x,this.row));fire()}
  else if(this.op==='delete'){DB[this.t]=T.filter(x=>!m(x));fire()}
  return Promise.resolve(out).then(res,rej)};
 window.supabase={createClient:()=>({
  from:t=>new Q(t),
  rpc:async n=>n==='last_access'?({data:DB.profiles.map(p=>({id:p.id,last_sign_in_at:new Date().toISOString()})),error:null}):({data:DB.profiles.filter(p=>p.approved).map(p=>({id:p.id,name:p.nombre,info:p.role,avatar:p.avatar||null})),error:null}),
  auth:{onAuthStateChange:f=>{cb=f;setTimeout(()=>f('INITIAL_SESSION',sess),0)},signInWithPassword:async({email})=>{window.__login(email.split('@')[0]);return {error:null}},signUp:async()=>({data:{session:null},error:null}),signOut:async()=>{sess=null;cb('SIGNED_OUT',null);return{}},resetPasswordForEmail:async()=>({}),updateUser:async()=>({}),signInWithOAuth:async()=>({error:{message:'x'}})},
  storage:{from:()=>({upload:async(p,b)=>{FILES[p]=b;return{error:null}},createSignedUrls:async(ps)=>({data:ps.map(p=>({path:p,signedUrl:FILES[p]?URL.createObjectURL(FILES[p]):''}))}),createSignedUrl:async(p)=>({data:{signedUrl:'about:blank'},error:null}),remove:async(ps)=>{ps.forEach(p=>delete FILES[p]);return{}}})},
  channel:()=>{const c={on:(a,b,f)=>{subs.push(f);return c},subscribe:()=>c};return c},removeChannel:()=>{}
 })};
})();
