// Regresiones de sesión con el código real de index.html y servicios sintéticos.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('index.html', 'utf8');
const helpers = source.slice(source.indexOf('/* ---------- sesión y acceso ---------- */'), source.indexOf('/* ---------- lecturas remotas ---------- */'));
const reads = source.slice(source.indexOf('async function loadAll()'), source.indexOf('const V='));

function harness() {
  const saved = new Map(), clients = [], messages = [];
  let profile = {id:'a',nombre:'Prueba',approved:true,role:'familiar'};
  const box = {
    REMOTE:true, CFG:{supabaseUrl:'https://synthetic.supabase.co',supabaseKey:'public-test'},
    URL, AbortController, Date, Map, Set, sb:null,session:null,chan:null,rtT:null,msgT:null,
    S:{allP:[],allM:[],allT:[],people:[],media:[],msgs:[],seasons:[],staff:[],cards:[]},
    V:{view:'app',tab:'chat'},REC:{},
    localStorage:{getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)},
    document:{querySelectorAll:()=>[],activeElement:{matches:()=>true}},
    setTimeout:()=>1,clearTimeout:()=>{},clearInterval:()=>{},render:()=>{},
    toast:t=>messages.push(t),coach:()=>false,dbxLoad:async()=>{},
    fetch:async()=>{throw new Error('sin red')},
    window:{supabase:{createClient:(url,key,options)=>{
      const client = {
        options,profileReply:null,chatReply:null,signReply:null,signedCalls:0,
        auth:{stopAutoRefresh:()=>{},onAuthStateChange:f=>{
          client.emit=f;return {data:{subscription:{unsubscribe:()=>{}}}};
        }},
        from:table=>{
          const q={select:()=>q,eq:()=>q,order:()=>q,limit:()=>q,
            maybeSingle:()=>client.profileReply||Promise.resolve({data:profile,error:null}),
            then:(resolve,reject)=>Promise.resolve(table==='messages'?(client.chatReply||{data:[],error:null}):{data:[],error:null}).then(resolve,reject)};
          return q;
        },
        storage:{from:()=>({createSignedUrls:()=>{client.signedCalls++;return client.signReply||Promise.resolve({data:[]})}})},
        rpc:async()=>({data:[],error:null}),
        channel:()=>{const c={on:()=>c,subscribe:()=>c};return c},removeChannel:()=>{}
      };
      clients.push(client);return client;
    }}}
  };
  const context = vm.createContext(box);
  const api = vm.runInContext(helpers+reads+`;({ensureAuthClient,logoutLocal,boot,refresh,loadChat,
    setUser(id){session={user:{id,email:'synthetic@example.invalid'},access_token:'synthetic-token'};S.user={id,approved:true,role:'familiar'}},
    fill(){S.people=[{nombre:'Dato sintético'}];S.msgs=[{body:'Privado sintético'}];URLC.private={u:'https://example.invalid/private'};V.logs=[{old:{tel:'000000000'}}];V.clip={mid:1};},
    snapshot(){return {session,view:V.view,people:S.people.length,msgs:S.msgs.length,urls:Object.keys(URLC).length,logs:V.logs,clip:V.clip}},
    seedCache(){URLC.private={u:'https://example.invalid/private'}}
  })`, context);
  return {api,box,saved,clients,messages,setProfile:p=>{profile=p}};
}
const deferred = () => {let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve}};

(async()=>{
  {
    const h=harness(),c=h.api.ensureAuthClient(),storage=c.options.auth.storage,key=c.options.auth.storageKey;
    h.api.setUser('a');h.api.fill();storage.setItem(key,'sesión sintética');
    await h.api.logoutLocal();
    assert.equal(h.saved.has(key),false);
    const state=h.api.snapshot();assert.equal(state.session,null);assert.equal(state.view,'login');
    assert.equal(state.people+state.msgs+state.urls,0);assert.equal(state.logs,undefined);assert.equal(state.clip,undefined);
    assert.ok(h.messages.some(m=>m.includes('No se ha podido confirmar')));
    // Una renovación tardía del cliente retirado no restaura ni borra otra sesión.
    const next=h.api.ensureAuthClient();h.api.setUser('b');next.options.auth.storage.setItem(key,'sesión nueva');
    storage.setItem(key,'sesión antigua');storage.removeItem(key);c.emit('SIGNED_IN',{user:{id:'a'}});
    assert.equal(h.saved.get(key),'sesión nueva');assert.equal(h.api.snapshot().session.user.id,'b');
  }
  for (const view of ['app','medit']) {
    const h=harness();h.api.ensureAuthClient();h.api.setUser('a');h.api.fill();h.box.V.view=view;
    h.setProfile({id:'a',approved:false,role:'familiar'});await h.api.refresh();
    const state=h.api.snapshot();assert.equal(state.view,'pending');assert.equal(state.people+state.msgs+state.urls,0);
  }
  {
    const h=harness(),client=h.api.ensureAuthClient(),pending=deferred();h.api.setUser('a');
    client.profileReply=pending.promise;const boot=h.api.boot();await h.api.logoutLocal();
    h.api.ensureAuthClient();h.api.setUser('b');
    pending.resolve({data:{id:'a',approved:true,role:'entrenador'}});await boot;
    assert.equal(h.api.snapshot().session.user.id,'b');assert.equal(h.box.S.user.id,'b');
  }
  {
    const h=harness(),client=h.api.ensureAuthClient(),pending=deferred();h.api.setUser('a');
    client.chatReply={data:[{audio:'old/private.webm',body:'Privado sintético'}]};client.signReply=pending.promise;
    const chat=h.api.loadChat();for(let i=0;i<8&&!client.signedCalls;i++)await Promise.resolve();
    assert.equal(client.signedCalls,1,'la respuesta firmada debe estar pendiente antes del logout');
    await h.api.logoutLocal();h.api.ensureAuthClient();h.api.setUser('b');
    pending.resolve({data:[{path:'old/private.webm',signedUrl:'https://example.invalid/old'}]});await chat;
    assert.equal(h.api.snapshot().msgs,0);assert.equal(h.api.snapshot().urls,0);
  }
  {
    const h=harness(),client=h.api.ensureAuthClient();h.api.setUser('a');h.api.fill();
    client.emit('SIGNED_OUT',null);
    assert.equal(h.api.snapshot().session,null);assert.equal(h.api.snapshot().msgs,0);
  }
  {
    const h=harness();h.api.ensureAuthClient();h.api.setUser('a');h.api.fill();h.setProfile(null);
    await h.api.refresh();assert.equal(h.api.snapshot().view,'rol');assert.equal(h.api.snapshot().people,0);
  }
  console.log('OK: logout sin red, cliente retirado, cambio de cuenta, revocación y respuestas tardías');
})().catch(e=>{console.error(e);process.exitCode=1});
