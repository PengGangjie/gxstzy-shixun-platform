
(function(){
  const DATA = window.CLASSROOM_ROOMS || {};
  const ROOMS = DATA.rooms || [];
  const byId = Object.fromEntries(ROOMS.map(r => [r.id, r]));
  const ALIGN = {code:'编号对齐', name:'名称对齐', room_no:'门牌对齐', jw_only:'仅教务', lab_only:'仅实训'};
  const ALIGN_CLS = {code:'b-ok', name:'b-ok', room_no:'b-ok', jw_only:'b-jw', lab_only:'b-lab'};

  const EDIT_FIELDS = [
    {key:'jw_name', label:'教室名称', group:'jw'},
    {key:'type', label:'教室类型', group:'jw'},
    {key:'enabled', label:'是否启用', group:'jw'},
    {key:'dept', label:'管理部门', group:'jw'},
    {key:'class_cap', label:'最大上课容纳', group:'jw'},
    {key:'exam_cap', label:'考场容纳', group:'jw'},
    {key:'multimedia', label:'多媒体', group:'jw'},
    {key:'monitor', label:'监控', group:'jw'},
    {key:'ac', label:'空调', group:'jw'},
    {key:'ac_count', label:'空调数量', group:'jw'},
    {key:'seat_layout', label:'座位排布', group:'jw'},
    {key:'area', label:'面积', group:'jw'},
    {key:'pc_count', label:'电脑数量', group:'jw'},
    {key:'asset_value', label:'资产总值', group:'jw'},
    {key:'door_no', label:'门牌号', group:'jw'},
    {key:'desc', label:'教室描述', group:'jw'},
    {key:'lab_name', label:'实训室名称', group:'lab'},
    {key:'building', label:'楼栋', group:'lab'},
    {key:'floor', label:'楼层', group:'lab'},
    {key:'room_no', label:'房号', group:'lab'},
    {key:'admin_name', label:'管理员', group:'lab'},
    {key:'admin_phone', label:'管理员电话', group:'lab'},
    {key:'teacher_name', label:'责任教师', group:'lab'},
    {key:'teacher_phone', label:'责任教师电话', group:'lab'},
    {key:'dean_name', label:'院长', group:'lab'},
    {key:'dean_phone', label:'院长电话', group:'lab'},
    {key:'level', label:'风险等级', group:'lab'},
    {key:'category', label:'分类', group:'lab'}
  ];

  function esc(s){
    return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function lvCls(lv){
    const u = String(lv||'').replace('级','');
    if(u==='Ⅰ'||u==='I') return 'lv-I';
    if(u==='Ⅱ'||u==='II') return 'lv-II';
    if(u==='Ⅲ'||u==='III') return 'lv-III';
    if(u==='Ⅳ'||u==='IV') return 'lv-IV';
    return 'b-off';
  }
  function roomUrl(id){ return id + '.html'; }
  function lsKey(kind, id){ return 'gxstzy-room-'+kind+'-'+id; }

  function renderCatalog(){
    const qEl = document.getElementById('q');
    const colEl = document.getElementById('college');
    const typeEl = document.getElementById('type');
    const alEl = document.getElementById('align');
    const jump = document.getElementById('jump');
    const grid = document.getElementById('grid');
    const meta = document.getElementById('meta');
    const colleges = DATA.college_order || [];
    const types = [...new Set(ROOMS.map(r => r.type).filter(Boolean))].sort();

    colEl.innerHTML = '<option value="">全部学院</option>' + colleges.map(c => `<option>${esc(c)}</option>`).join('');
    typeEl.innerHTML = '<option value="">全部类型</option>' + types.map(t => `<option>${esc(t)}</option>`).join('');
    alEl.innerHTML = '<option value="">全部对齐</option>'
      + Object.entries(ALIGN).map(([k,v]) => `<option value="${k}">${v}</option>`).join('');

    jump.innerHTML = colleges.map(c => `<button type="button" data-c="${esc(c)}">${esc(c)}</button>`).join('');
    jump.addEventListener('click', e => {
      const b = e.target.closest('button'); if(!b) return;
      colEl.value = b.dataset.c;
      [...jump.querySelectorAll('button')].forEach(x => x.classList.toggle('active', x===b));
      draw();
    });

    function filtered(){
      const q = (qEl.value||'').trim().toLowerCase();
      const col = colEl.value;
      const ty = typeEl.value;
      const al = alEl.value;
      return ROOMS.filter(r => {
        if(col && r.college !== col) return false;
        if(ty && r.type !== ty) return false;
        if(al && r.align !== al) return false;
        if(!q) return true;
        const hay = [r.display_name,r.display_code,r.jw_code,r.sys_code,r.building,r.room_no,r.college].join(' ').toLowerCase();
        return hay.includes(q);
      });
    }
    function draw(){
      const list = filtered();
      meta.textContent = '显示 ' + list.length + ' / ' + ROOMS.length;
      if(!list.length){ grid.innerHTML = '<div class="empty">没有符合条件的教室</div>'; return; }
      grid.innerHTML = list.map(r => {
        const cap = r.class_cap ? ('上课 ' + r.class_cap + ' 人') : '';
        return `<a class="card" href="${esc(roomUrl(r.id))}" target="_top">
          <div>
            <span class="badge ${ALIGN_CLS[r.align]||'b-off'}">${ALIGN[r.align]||r.align}</span>
            ${r.level ? `<span class="badge ${lvCls(r.level)}">${esc(r.level)}</span>` : ''}
            ${r.enabled==='否' ? '<span class="badge b-off">停用</span>' : ''}
            ${r.has_chem ? '<span class="badge b-jw">危化</span>' : ''}
          </div>
          <h3>${esc(r.display_name)}</h3>
          <div class="meta">${esc(r.college)} · ${esc(r.campus||'')} · ${esc(r.building||'')}${r.room_no?' · '+esc(r.room_no):''}<br>
          教务 ${esc(r.jw_code||'—')} · 实训 ${esc(r.sys_code||'—')} · ${esc(r.type||'')}${cap?' · '+cap:''}</div>
        </a>`;
      }).join('');
    }
    [qEl,colEl,typeEl,alEl].forEach(el => el.addEventListener('input', draw));
    draw();
  }

  function kv(label, val){
    if(val===undefined || val===null || val==='') val = '—';
    return `<div><span>${esc(label)}</span>${esc(val)}</div>`;
  }
  function tablePairs(pairs){
    return '<table class="data"><tbody>' + pairs.map(([k,v]) =>
      `<tr><th>${esc(k)}</th><td>${v===undefined||v===null||v===''?'—':esc(v)}</td></tr>`
    ).join('') + '</tbody></table>';
  }
  function listOrDash(arr){
    if(!arr || !arr.length) return '<p class="hint">暂无记录。</p>';
    return '<ul>' + arr.map(x => `<li>${esc(x)}</li>`).join('') + '</ul>';
  }

  function baseVals(r){
    const jw = r.jw || {};
    const lab = r.lab || {};
    return {
      jw_name: jw.jw_name || r.display_name || '',
      type: jw.type || r.type || '',
      enabled: jw.enabled || r.enabled || '',
      dept: jw.dept || jw.tag || '',
      class_cap: jw.class_cap || r.class_cap || '',
      exam_cap: jw.exam_cap || r.exam_cap || '',
      multimedia: jw.multimedia || '',
      monitor: jw.monitor || '',
      ac: jw.ac || '',
      ac_count: jw.ac_count || '',
      seat_layout: jw.seat_layout || '',
      area: jw.area || '',
      pc_count: jw.pc_count || '',
      asset_value: jw.asset_value || '',
      door_no: jw.door_no || '',
      desc: jw.desc || '',
      lab_name: lab.name || '',
      building: lab.building || r.building || '',
      floor: lab.floor || r.floor || '',
      room_no: lab.room_no || r.room_no || '',
      admin_name: lab.admin_name || '',
      admin_phone: lab.admin_phone || '',
      teacher_name: lab.teacher_name || '',
      teacher_phone: lab.teacher_phone || '',
      dean_name: lab.dean_name || '',
      dean_phone: lab.dean_phone || '',
      level: lab.level || r.level || '',
      category: lab.category || r.category || ''
    };
  }

  function mergedVals(r, overrides){
    return Object.assign({}, baseVals(r), overrides || {});
  }

  async function apiMe(){
    try{
      const res = await fetch('/api/me', {credentials:'same-origin'});
      return await res.json();
    }catch(_){ return {authenticated:false}; }
  }

  async function loadState(roomId){
    try{
      const res = await fetch('/api/rooms/' + encodeURIComponent(roomId) + '/state', {credentials:'same-origin'});
      if(res.status === 401) return {overrides:{}, photos:[], equipment:[], offline:true, needLogin:true};
      if(!res.ok) throw new Error('HTTP '+res.status);
      const data = await res.json();
      data.offline = false;
      return data;
    }catch(_){
      const local = JSON.parse(localStorage.getItem(lsKey('state', roomId))||'null');
      return local || {overrides:{}, photos:[], equipment:[], offline:true};
    }
  }

  function saveLocalState(roomId, state){
    localStorage.setItem(lsKey('state', roomId), JSON.stringify({
      overrides: state.overrides || {},
      photos: state.photos || [],
      equipment: state.equipment || []
    }));
  }

  function compressImage(file, maxSide, quality){
    return new Promise((resolve, reject) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        let w = img.width, h = img.height;
        const scale = Math.min(1, maxSide / Math.max(w, h));
        w = Math.round(w * scale); h = Math.round(h * scale);
        const canvas = document.createElement('canvas');
        canvas.width = w; canvas.height = h;
        canvas.getContext('2d').drawImage(img, 0, 0, w, h);
        URL.revokeObjectURL(url);
        resolve(canvas.toDataURL('image/jpeg', quality));
      };
      img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('读图失败')); };
      img.src = url;
    });
  }

  function renderRoom(id){
    const r = byId[id];
    const root = document.getElementById('app');
    if(!r){ root.innerHTML = '<div class="wrap"><div class="empty">未找到该教室。</div></div>'; return; }
    document.title = r.display_name + ' · 教室分室';
    const lab = r.lab || {};
    const chemTab = r.has_chem ? '' : 'display:none';
    const yishi = (r.yishi && r.yishi.files) || [];
    const signs = lab.signs || {};
    const signImgs = []
      .concat(signs.prohibit||[], signs.warning||[], signs.instruct||[])
      .slice(0, 12);
    const boardCode = lab.sys_code || r.sys_code || '';

    let state = {overrides:{}, photos:[], equipment:[], canWrite:false, me:null};
    let editing = false;

    root.innerHTML = `
      <header class="top"><div class="top-inner">
        <div>
          <h1>${esc(r.display_name)}</h1>
          <p>${esc(r.college)} · ${esc(ALIGN[r.align]||r.align)} · 扫码进入本页</p>
        </div>
        <nav>
          <a href="index.html">教室目录</a>
          <a href="../广西生态工程职业技术学院-教务处-实训科管理平台.html">平台首页</a>
          ${boardCode ? `<a href="../lab-grade-boards/home.html?id=${esc(boardCode)}#${esc(boardCode)}" target="_blank" rel="noopener">安全信息牌</a>` : ''}
        </nav>
      </div></header>
      <div class="wrap">
        <div class="room-head">
          <div class="room-title">
            <span class="badge ${ALIGN_CLS[r.align]||'b-off'}">${ALIGN[r.align]||r.align}</span>
            ${r.level?`<span class="badge ${lvCls(r.level)}">${esc(r.level)}</span>`:''}
            <span class="badge b-ok">${esc(r.type||'')}</span>
            <h2>${esc(r.display_name)}</h2>
            <div class="kv" id="room-kv"></div>
          </div>
          <div class="qrbox"><div id="qr"></div><p>本教室专属界面</p></div>
        </div>
        <div class="status-row" id="status-row"></div>
        <div class="tabs" id="tabs">
          <button data-tab="info" class="active">基础信息</button>
          <button data-tab="safety">安全信息</button>
          <button data-tab="schedule">使用情况</button>
          <button data-tab="equip">仪器设备</button>
          <button data-tab="access">安全准入</button>
          <button data-tab="scan">设备登记</button>
          <button data-tab="inspect">安全检查</button>
          <button data-tab="chem" style="${chemTab}">危化品</button>
        </div>
        <section class="panel active" data-panel="info"></section>
        <section class="panel" data-panel="safety"></section>
        <section class="panel" data-panel="schedule"></section>
        <section class="panel" data-panel="equip"></section>
        <section class="panel" data-panel="access"></section>
        <section class="panel" data-panel="scan"></section>
        <section class="panel" data-panel="inspect"></section>
        <section class="panel" data-panel="chem"></section>
        <p class="foot-note">可编辑字段、教室照片与仪器台账写入云端（Turso）；未登录或离线时回落本机缓存。电子牌与分级分类台账同源。</p>
      </div>`;

    function vals(){ return mergedVals(r, state.overrides); }

    function paintHead(){
      const v = vals();
      root.querySelector('#room-kv').innerHTML =
        kv('教务编号', r.jw_code) + kv('实训编号', r.sys_code || boardCode) +
        kv('校区 / 楼栋', [r.campus, v.building, v.floor].filter(Boolean).join(' · ')) +
        kv('门牌', v.room_no || v.door_no) + kv('上课容量', v.class_cap) + kv('安全类别', v.category);
      const st = root.querySelector('#status-row');
      const writeHint = state.canWrite ? '可编辑' : (state.me && state.me.authenticated ? '只读（需教务/学院/实验员/教师）' : '登录后可编辑');
      st.innerHTML = `
        <span>电子牌：${boardCode?'已关联':'未关联'}</span>
        <span>照片：${(state.photos||[]).length} 张</span>
        <span>仪器：${(state.equipment||[]).length} 条</span>
        <span>${writeHint}</span>
        <span>一室一表：${yishi.length?'有档案':'待补'}</span>`;
    }

    function photosCarouselHtml(){
      const list = state.photos || [];
      const up = state.canWrite
        ? `<div class="actions photo-actions">
            <label class="btn sec file-btn">拍照 / 上传
              <input id="photo-input" type="file" accept="image/*" capture="environment" hidden>
            </label>
            <input id="photo-caption" type="text" placeholder="照片说明（可选）">
            <span class="hint" id="photo-status"></span>
          </div>`
        : '';
      if(!list.length){
        return up + '<div class="photo-carousel empty"><p class="hint">暂无教室照片，可用手机拍照上传展示环境。</p></div>';
      }
      const slides = list.map((p, i) => `
        <figure class="carousel-slide${i===0?' active':''}">
          <img src="${esc(p.data_url)}" alt="${esc(p.caption||'教室照片')}">
          <figcaption>${esc(p.caption||'教室环境')}${state.canWrite?` <button type="button" class="linkish" data-del-photo="${p.id}">删除</button>`:''}</figcaption>
        </figure>`).join('');
      const dots = list.map((_, i) => `<button type="button" class="carousel-dot${i===0?' active':''}" aria-label="第 ${i+1} 张"></button>`).join('');
      const nav = list.length > 1
        ? `<button type="button" class="carousel-btn prev" aria-label="上一张">‹</button>
           <button type="button" class="carousel-btn next" aria-label="下一张">›</button>
           <div class="carousel-dots">${dots}</div>`
        : '';
      return up + `<div class="photo-carousel" id="photo-carousel">${slides}${nav}</div>`;
    }

    function moduleBlock(title, inner){
      return `<section class="info-module">
        <h3>${esc(title)}</h3>
        <div class="info-module-body">${inner}</div>
      </section>`;
    }

    function boardHtml(){
      if(!boardCode){
        return '<p class="hint">本室尚未对齐实训编号，无法展示安全信息电子牌。请先在对齐表核对照。</p>';
      }
      const src = `../lab-grade-boards/home.html?embed=1&preview=1&id=${encodeURIComponent(boardCode)}`;
      return `<div class="board-preview">
        <h3>安全信息电子牌</h3>
        <div class="board-viewport" id="board-viewport" title="点击放大查看">
          <p class="hint board-loading">正在生成信息牌…</p>
          <img class="board-shot hidden" id="board-shot" alt="安全信息电子牌">
        </div>
        <div class="board-toolbar">
          <button type="button" class="btn sec" id="btn-board-dl" disabled>下载 JPG</button>
          <button type="button" class="btn sec" id="btn-board-print" disabled>打印 A4</button>
        </div>
        <iframe class="board-render-frame" title="信息牌渲染" src="${esc(src)}" tabindex="-1" aria-hidden="true"></iframe>
      </div>`;
    }

    function printBoardA4(src){
      if(!src) return;
      const w = window.open('', '_blank');
      if(!w){ alert('请允许弹出窗口以打印'); return; }
      w.document.open();
      w.document.write('<!DOCTYPE html><html><head><meta charset="utf-8"><title>安全信息电子牌</title><style>@page{size:A4 landscape;margin:0}html,body{margin:0;padding:0;width:100%;height:100%}img{width:100%;height:100%;object-fit:contain;display:block}</style></head><body></body></html>');
      w.document.close();
      const img = w.document.createElement('img');
      img.onload = () => { w.focus(); w.print(); setTimeout(() => w.close(), 400); };
      img.src = src;
      w.document.body.appendChild(img);
    }

    function openBoardLightbox(src){
      let lb = document.getElementById('board-lightbox');
      if(!lb){
        lb = document.createElement('div');
        lb.id = 'board-lightbox';
        lb.className = 'board-lightbox';
        lb.hidden = true;
        lb.innerHTML = '<button type="button" class="board-lightbox-close" aria-label="关闭">×</button><img alt="安全信息电子牌">';
        lb.addEventListener('click', e => {
          if(e.target === lb || e.target.classList.contains('board-lightbox-close')) lb.hidden = true;
        });
        document.body.appendChild(lb);
      }
      lb.querySelector('img').src = src;
      lb.hidden = false;
    }

    function initBoardViewer(el){
      const img = el.querySelector('#board-shot');
      const loading = el.querySelector('.board-loading');
      const viewport = el.querySelector('#board-viewport');
      const dl = el.querySelector('#btn-board-dl');
      const printBtn = el.querySelector('#btn-board-print');
      const showShot = url => {
        if(!url || !img) return;
        img.src = url;
        img.classList.remove('hidden');
        if(loading) loading.classList.add('hidden');
        if(dl) dl.disabled = false;
        if(printBtn) printBtn.disabled = false;
      };
      el._boardShowShot = showShot;
      if(viewport) viewport.onclick = () => { if(img && img.src) openBoardLightbox(img.src); };
      if(dl) dl.onclick = e => {
        e.stopPropagation();
        if(!img || !img.src) return;
        const a = document.createElement('a');
        a.href = img.src;
        a.download = (boardCode || r.id).replace(/[\\/:*?"<>|]/g, '_') + '_安全信息牌.jpg';
        a.click();
      };
      if(printBtn) printBtn.onclick = e => { e.stopPropagation(); if(img && img.src) printBoardA4(img.src); };
    }

    function infoView(){
      const v = vals();
      const yishiHtml = yishi.length
        ? yishi.map(f => `<li><a href="${esc(f.href)}" target="_blank" rel="noopener">${esc(f.title||'一室一表')}</a></li>`).join('')
        : '<p class="hint">尚未关联一室一表主文件。</p>';
      const editBtn = state.canWrite
        ? `<button type="button" class="btn" id="btn-edit-info">${editing?'取消编辑':'编辑本室信息'}</button>
           ${editing?'<button type="button" class="btn" id="btn-save-info">保存修改</button>':''}`
        : (state.needLogin || !(state.me&&state.me.authenticated)
          ? '<a class="btn sec" href="/sign-in?next='+encodeURIComponent(location.pathname)+'">登录后编辑</a>'
          : '<span class="hint">当前角色不可编辑</span>');

      if(editing){
        const fields = EDIT_FIELDS.map(f => `
          <div><label class="f">${esc(f.label)}</label>
          <input type="text" name="${esc(f.key)}" value="${esc(v[f.key]||'')}"></div>`).join('');
        return `<div class="actions">${editBtn}</div>
          <form id="edit-info-form" class="form-grid" style="margin-top:12px">${fields}</form>
          <p class="hint">保存后覆盖写入云端，并与下方展示合并（教务编号等主键不可改）。</p>`;
      }

      return `<div class="actions info-actions">${editBtn}</div>
        <div class="info-layout">
          <div class="info-top-grid">
            <div class="info-col-board">${boardHtml()}</div>
            <div class="info-col-photos">
              <div class="photo-panel">
                <h3>教室图片</h3>
                ${photosCarouselHtml()}
              </div>
            </div>
          </div>
          <div class="info-bottom-grid">
            ${moduleBlock('教务系统', tablePairs([
              ['教室编号', r.jw_code],['教室名称', v.jw_name],['教室类型', v.type],
              ['是否启用', v.enabled],['管理部门', v.dept],
              ['最大上课容纳', v.class_cap],['考场容纳', v.exam_cap],
              ['多媒体', v.multimedia],['监控', v.monitor],
              ['空调', (v.ac||'') + (v.ac_count?(' × '+v.ac_count):'')],
              ['座位排布', v.seat_layout],['面积', v.area],['电脑数量', v.pc_count],
              ['资产总值', v.asset_value],['门牌号', v.door_no],['教室描述', v.desc]
            ]))}
            ${moduleBlock('实训系统', boardCode || lab.sys_code ? tablePairs([
              ['系统编号', boardCode || lab.sys_code],['实训室名称', v.lab_name],
              ['楼栋 / 楼层 / 房号', [v.building,v.floor,v.room_no].filter(Boolean).join(' · ')],
              ['管理员', (v.admin_name||'')+' '+(v.admin_phone||'')],
              ['责任教师', (v.teacher_name||'')+' '+(v.teacher_phone||'')],
              ['院长', (v.dean_name||'')+' '+(v.dean_phone||'')],
              ['风险等级', v.level],['分类', v.category]
            ]) : '<p class="hint">教务有教室记录，分级分类台账尚未对齐到本编号。</p>')}
          </div>
          <div class="info-yishi">${moduleBlock('一室一表档案', yishi.length?`<ul class="yishi-list">${yishiHtml}</ul>`:yishiHtml)}</div>
        </div>`;
    }

    function equipView(){
      const rows = state.equipment || [];
      const body = rows.length
        ? rows.map(x => `<tr><td>${esc(x.code)}</td><td>${esc(x.name)}</td><td>${esc(x.model)}</td><td>${esc(x.status)}</td><td>${esc(x.risk_note)}</td></tr>`).join('')
        : '<tr><td colspan="5">暂无设备台账。请上传 Excel/CSV 更新。</td></tr>';
      const tools = state.canWrite
        ? `<div class="actions">
            <a class="btn sec" href="data:text/csv;charset=utf-8,${encodeURIComponent('仪器编号,名称,型号,状态,风险提示\nEQ-001,示例设备,型号A,正常,注意散热')}" download="仪器导入模板_${r.id}.csv">下载 CSV 模板</a>
            <label class="btn file-btn">Excel / CSV 上传更新
              <input id="equip-file" type="file" accept=".xlsx,.xlsm,.csv,.txt" hidden>
            </label>
            <span class="hint" id="equip-status"></span>
          </div>
          <p class="hint">表头建议：仪器编号、名称、型号、状态、风险提示。上传后整表替换本室仪器列表。</p>`
        : '<p class="hint">登录且具备编辑权限后可 Excel 更新仪器台账。</p>';
      return tools
        + `<table class="data"><thead><tr><th>仪器编号</th><th>名称</th><th>型号</th><th>状态</th><th>风险提示</th></tr></thead>
           <tbody>${body}</tbody></table>`;
    }

    const panels = {
      info: () => infoView(),
      safety: () => {
        if(!boardCode) return '<p class="hint">本教室尚未对齐实训安全台账。</p>';
        const src = `../lab-grade-boards/home.html?embed=1&edit=1&id=${encodeURIComponent(boardCode)}`;
        return `<p class="hint">在此编辑信息牌字段（等级、类别、负责人、事故诱因、防护措施、灭火要点等）。保存后「基础信息」页将显示最新成图。</p>
          <iframe class="board-edit-frame" title="安全信息牌编辑" src="${esc(src)}" loading="lazy"></iframe>`;
      },
      schedule: () => `<p class="hint">对接超星课表后按课次/开放时段自动同步。</p>
        <table class="data"><thead><tr><th>使用人</th><th>课程</th><th>人数</th><th>起止时间</th><th>异常</th></tr></thead>
        <tbody><tr><td colspan="5">暂无课表数据（超星接口未开通）</td></tr></tbody></table>`,
      equip: () => equipView(),
      access: () => `<p class="hint">集中展示本室准入证书状态、有效期与安全承诺书。</p>
        <table class="data"><thead><tr><th>姓名</th><th>身份</th><th>准入证书</th><th>有效期</th><th>承诺书</th></tr></thead>
        <tbody><tr><td colspan="5">暂无准入记录</td></tr></tbody></table>`,
      scan: () => scanForm(r),
      inspect: () => inspectForm(r),
      chem: () => r.has_chem
        ? `<p>本室启用危化品与物资管理页签。</p>
           <table class="data"><thead><tr><th>品名</th><th>规格</th><th>库存</th><th>预警</th><th>存放</th></tr></thead>
           <tbody><tr><td colspan="5">暂无在库危化品记录</td></tr></tbody></table>`
        : '<p class="hint">本室未启用危化品模块。</p>'
    };

    function paint(name, force){
      const el = root.querySelector('[data-panel="'+name+'"]');
      if(!el) return;
      if(force) el.dataset.ready = '';
      if(el.dataset.ready) return;
      el.innerHTML = panels[name]();
      el.dataset.ready = '1';
      bindPanel(name, el);
    }

    function initPhotoCarousel(el){
      const carousel = el.querySelector('#photo-carousel');
      if(!carousel || carousel.classList.contains('empty')) return;
      const slides = [...carousel.querySelectorAll('.carousel-slide')];
      if(!slides.length) return;
      let idx = slides.findIndex(s => s.classList.contains('active'));
      if(idx < 0) idx = 0;
      const dots = [...carousel.querySelectorAll('.carousel-dot')];
      const show = i => {
        idx = (i + slides.length) % slides.length;
        slides.forEach((s, j) => s.classList.toggle('active', j === idx));
        dots.forEach((d, j) => d.classList.toggle('active', j === idx));
      };
      const prev = carousel.querySelector('.carousel-btn.prev');
      const next = carousel.querySelector('.carousel-btn.next');
      if(prev) prev.onclick = () => show(idx - 1);
      if(next) next.onclick = () => show(idx + 1);
      dots.forEach((d, j) => { d.onclick = () => show(j); });
      if(slides.length > 1){
        let timer = setInterval(() => show(idx + 1), 6000);
        carousel.addEventListener('mouseenter', () => clearInterval(timer));
        carousel.addEventListener('mouseleave', () => {
          timer = setInterval(() => show(idx + 1), 6000);
        });
      }
    }

    function bindPanel(name, el){
      if(name === 'info'){
        const editBtn = el.querySelector('#btn-edit-info');
        if(editBtn) editBtn.onclick = () => { editing = !editing; paint('info', true); };
        const saveBtn = el.querySelector('#btn-save-info');
        if(saveBtn) saveBtn.onclick = () => saveOverrides(el);
        const photoInput = el.querySelector('#photo-input');
        if(photoInput) photoInput.onchange = () => uploadPhoto(el, photoInput);
        el.querySelectorAll('[data-del-photo]').forEach(btn => {
          btn.onclick = () => delPhoto(btn.getAttribute('data-del-photo'));
        });
        initPhotoCarousel(el);
        initBoardViewer(el);
      }
      if(name === 'equip'){
        const file = el.querySelector('#equip-file');
        if(file) file.onchange = () => importEquip(el, file);
      }
    }

    async function saveOverrides(el){
      const form = el.querySelector('#edit-info-form');
      if(!form) return;
      const fd = new FormData(form);
      const overrides = {};
      EDIT_FIELDS.forEach(f => { overrides[f.key] = String(fd.get(f.key) || '').trim(); });
      try{
        const res = await fetch('/api/rooms/' + encodeURIComponent(r.id) + '/overrides', {
          method:'PUT', credentials:'same-origin',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({overrides})
        });
        if(!res.ok){
          const err = await res.json().catch(()=>({}));
          alert(err.detail || '保存失败');
          return;
        }
        const data = await res.json();
        state.overrides = data.overrides || overrides;
      }catch(_){
        state.overrides = overrides;
        saveLocalState(r.id, state);
        alert('云端不可用，已写入本机缓存');
      }
      editing = false;
      paintHead();
      paint('info', true);
      paint('safety', true);
    }

    async function uploadPhoto(el, input){
      const file = input.files && input.files[0];
      if(!file) return;
      const status = el.querySelector('#photo-status');
      const caption = (el.querySelector('#photo-caption')||{}).value || '';
      if(status) status.textContent = '压缩中…';
      try{
        const data_url = await compressImage(file, 1280, 0.72);
        if(status) status.textContent = '上传中…';
        const res = await fetch('/api/rooms/' + encodeURIComponent(r.id) + '/photos', {
          method:'POST', credentials:'same-origin',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({data_url, caption})
        });
        if(!res.ok){
          const err = await res.json().catch(()=>({}));
          throw new Error(err.detail || '上传失败');
        }
        const data = await res.json();
        state.photos = [data.photo].concat(state.photos || []);
        saveLocalState(r.id, state);
        if(status) status.textContent = '已上传';
        paintHead();
        paint('info', true);
      }catch(err){
        if(status) status.textContent = String(err.message || err);
        alert(String(err.message || err));
      }finally{
        input.value = '';
      }
    }

    async function delPhoto(pid){
      if(!confirm('删除这张照片？')) return;
      try{
        const res = await fetch('/api/rooms/' + encodeURIComponent(r.id) + '/photos/' + pid, {
          method:'DELETE', credentials:'same-origin'
        });
        if(!res.ok){
          const err = await res.json().catch(()=>({}));
          throw new Error(err.detail || '删除失败');
        }
      }catch(err){
        alert(String(err.message || err));
        return;
      }
      state.photos = (state.photos || []).filter(p => String(p.id) !== String(pid));
      saveLocalState(r.id, state);
      paintHead();
      paint('info', true);
    }

    async function importEquip(el, input){
      const file = input.files && input.files[0];
      if(!file) return;
      const status = el.querySelector('#equip-status');
      if(status) status.textContent = '导入中…';
      try{
        const fd = new FormData();
        fd.append('file', file);
        const res = await fetch('/api/rooms/' + encodeURIComponent(r.id) + '/equipment/import', {
          method:'POST', credentials:'same-origin', body: fd
        });
        if(!res.ok){
          const err = await res.json().catch(()=>({}));
          throw new Error(err.detail || '导入失败');
        }
        const data = await res.json();
        state.equipment = data.equipment || [];
        saveLocalState(r.id, state);
        if(status) status.textContent = '已更新 ' + (data.count||0) + ' 条';
        paintHead();
        paint('equip', true);
      }catch(err){
        if(status) status.textContent = String(err.message || err);
        alert(String(err.message || err));
      }finally{
        input.value = '';
      }
    }

    root.querySelector('#tabs').addEventListener('click', e => {
      const b = e.target.closest('button'); if(!b) return;
      const name = b.dataset.tab;
      root.querySelectorAll('#tabs button').forEach(x => x.classList.toggle('active', x===b));
      root.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.dataset.panel===name));
      paint(name);
    });

    const qrEl = document.getElementById('qr');
    if(qrEl && window.QRCode){
      new QRCode(qrEl, {text: location.href, width:132, height:132, correctLevel: QRCode.CorrectLevel.M});
    }

    (async function boot(){
      const me = await apiMe();
      state.me = me;
      state.canWrite = !!(me && me.authenticated && (me.capabilities||[]).includes('rooms.write'));
      const remote = await loadState(r.id);
      state.overrides = remote.overrides || {};
      state.photos = remote.photos || [];
      state.equipment = remote.equipment || [];
      state.needLogin = !!remote.needLogin;
      state.offline = !!remote.offline;
      paintHead();
      paint('info', true);
    })();
  }

  function scanForm(r){
    const saved = JSON.parse(localStorage.getItem(lsKey('scan', r.id))||'[]');
    const rows = saved.length ? saved.map(x => `<tr><td>${esc(x.no)}</td><td>${esc(x.name)}</td><td>${esc(x.device)}</td><td>${esc(x.start)}</td><td>${esc(x.status)}</td></tr>`).join('')
      : '<tr><td colspan="5">暂无扫码登记。</td></tr>';
    return `<p class="hint">学生扫设备二维码登记（本页提供演示闭环）。</p>
      <form id="scan-form">
        <div class="form-grid">
          <div><label class="f">学号</label><input name="sid" type="text" required></div>
          <div><label class="f">姓名</label><input name="name" type="text" required></div>
          <div><label class="f">课程 / 项目</label><input name="course" type="text"></div>
          <div><label class="f">使用设备</label><input name="device" type="text" required></div>
          <div><label class="f">预估时长（分钟）</label><input name="mins" type="number" min="1" value="90"></div>
          <div><label class="f">指导教师</label><input name="teacher" type="text"></div>
        </div>
        <label class="chk"><input type="checkbox" name="agree" required>已阅读实验室安全操作规范</label>
        <div class="actions"><button class="btn" type="submit">提交登记</button></div>
      </form>
      <h3 style="margin-top:16px">本室登记明细</h3>
      <table class="data"><thead><tr><th>流水号</th><th>使用人</th><th>设备</th><th>开始</th><th>状态</th></tr></thead><tbody id="scan-rows">${rows}</tbody></table>`;
  }

  function inspectForm(r){
    const saved = JSON.parse(localStorage.getItem(lsKey('inspect', r.id))||'[]');
    const rows = saved.length ? saved.map(x => `<tr><td>${esc(x.time)}</td><td>${esc(x.who)}</td><td>${esc(x.items)}</td><td>${esc(x.result)}</td></tr>`).join('')
      : '<tr><td colspan="4">暂无检查记录。</td></tr>';
    return `<p class="hint">日检下沉到本分室后在此归集。</p>
      <form id="insp-form">
        <div class="form-grid">
          <div><label class="f">检查人</label><input name="who" type="text" required></div>
          <div><label class="f">结论</label><select name="result"><option>正常</option><option>有隐患</option></select></div>
        </div>
        <label class="chk"><input type="checkbox" name="it" value="断电">离开断电 / 电源规范</label>
        <label class="chk"><input type="checkbox" name="it" value="通道">应急通道畅通</label>
        <label class="chk"><input type="checkbox" name="it" value="灭火器">灭火器在位有效</label>
        <div><label class="f">隐患说明</label><textarea name="note" rows="2"></textarea></div>
        <div class="actions"><button class="btn" type="submit">登记本室日检</button></div>
      </form>
      <h3 style="margin-top:16px">历史检查</h3>
      <table class="data"><thead><tr><th>时间</th><th>检查人</th><th>项目</th><th>结论</th></tr></thead><tbody id="insp-rows">${rows}</tbody></table>`;
  }

  document.addEventListener('submit', e => {
    const form = e.target;
    if(form.id==='scan-form'){
      e.preventDefault();
      const id = document.body.dataset.room;
      const fd = new FormData(form);
      const rec = {
        no: 'S' + Date.now(),
        name: fd.get('name'),
        device: fd.get('device'),
        start: new Date().toISOString().slice(0,16).replace('T',' '),
        status: '外观完好'
      };
      const arr = JSON.parse(localStorage.getItem(lsKey('scan', id))||'[]');
      arr.unshift(rec);
      localStorage.setItem(lsKey('scan', id), JSON.stringify(arr.slice(0,50)));
      form.reset();
      const panel = document.querySelector('[data-panel="scan"]');
      if(panel){ panel.dataset.ready=''; document.querySelector('[data-tab="scan"]').click(); }
    }
    if(form.id==='insp-form'){
      e.preventDefault();
      const id = document.body.dataset.room;
      const fd = new FormData(form);
      const rec = {
        time: new Date().toISOString().slice(0,16).replace('T',' '),
        who: fd.get('who'),
        items: [...form.querySelectorAll('input[name=it]:checked')].map(x=>x.value).join('、') || '未勾选',
        result: fd.get('result')
      };
      const arr = JSON.parse(localStorage.getItem(lsKey('inspect', id))||'[]');
      arr.unshift(rec);
      localStorage.setItem(lsKey('inspect', id), JSON.stringify(arr.slice(0,50)));
      form.reset();
      const panel = document.querySelector('[data-panel="inspect"]');
      if(panel){ panel.dataset.ready=''; document.querySelector('[data-tab="inspect"]').click(); }
    }
  });

  const page = document.body.dataset.page;
  if(page==='catalog') renderCatalog();
  else if(page==='room') renderRoom(document.body.dataset.room);

  window.addEventListener('message', e => {
    const data = e.data;
    if(data === 'lab-board-saved'){
      const frame = document.querySelector('.board-render-frame');
      if(!frame) return;
      const url = frame.src;
      frame.src = '';
      frame.src = url;
      return;
    }
    if(data && data.type === 'lab-board-image'){
      const panel = document.querySelector('[data-panel="info"]');
      if(panel && panel._boardShowShot) panel._boardShowShot(data.url);
    }
  });
})();
