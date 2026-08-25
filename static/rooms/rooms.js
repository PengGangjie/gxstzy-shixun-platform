
(function(){
  const DATA = window.CLASSROOM_ROOMS || {};
  const ROOMS = DATA.rooms || [];
  const byId = Object.fromEntries(ROOMS.map(r => [r.id, r]));
  const ALIGN = {code:'编号对齐', name:'名称对齐', room_no:'门牌对齐', jw_only:'仅教务', lab_only:'仅实训'};
  const ALIGN_CLS = {code:'b-ok', name:'b-ok', room_no:'b-ok', jw_only:'b-jw', lab_only:'b-lab'};

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

  function renderRoom(id){
    const r = byId[id];
    const root = document.getElementById('app');
    if(!r){ root.innerHTML = '<div class="wrap"><div class="empty">未找到该教室。</div></div>'; return; }
    document.title = r.display_name + ' · 教室分室';
    const jw = r.jw || {};
    const lab = r.lab || {};
    const chemTab = r.has_chem ? '' : 'display:none';
    const yishi = (r.yishi && r.yishi.files) || [];
    const signs = lab.signs || {};
    const signImgs = []
      .concat(signs.prohibit||[], signs.warning||[], signs.instruct||[])
      .slice(0, 12);

    root.innerHTML = `
      <header class="top"><div class="top-inner">
        <div>
          <h1>${esc(r.display_name)}</h1>
          <p>${esc(r.college)} · ${esc(ALIGN[r.align]||r.align)} · 扫码进入本页</p>
        </div>
        <nav>
          <a href="index.html">教室目录</a>
          <a href="../广西生态工程职业技术学院-教务处-实训科管理平台.html">平台首页</a>
          ${lab.sys_code ? `<a href="../lab-grade-boards/home.html?id=${esc(lab.sys_code)}">安全信息牌</a>` : ''}
        </nav>
      </div></header>
      <div class="wrap">
        <div class="room-head">
          <div class="room-title">
            <span class="badge ${ALIGN_CLS[r.align]||'b-off'}">${ALIGN[r.align]||r.align}</span>
            ${r.level?`<span class="badge ${lvCls(r.level)}">${esc(r.level)}</span>`:''}
            <span class="badge b-ok">${esc(r.type||'')}</span>
            <h2>${esc(r.display_name)}</h2>
            <div class="kv">
              ${kv('教务编号', r.jw_code)}
              ${kv('实训编号', r.sys_code)}
              ${kv('校区 / 楼栋', [r.campus,r.building,r.floor].filter(Boolean).join(' · '))}
              ${kv('门牌', r.room_no)}
              ${kv('上课容量', r.class_cap)}
              ${kv('安全类别', r.category)}
            </div>
          </div>
          <div class="qrbox"><div id="qr"></div><p>本教室专属界面</p></div>
        </div>
        <div class="status-row">
          <span>超星课表：待对接</span>
          <span>资产系统：待对接（可 Excel 导入）</span>
          <span>万欣安全台账：${lab.sys_code?'已关联':'未关联'}</span>
          <span>一室一表：${yishi.length?'有档案':'待补'}</span>
        </div>
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
        <p class="foot-note">模块按《实训室系统模块需求表》规划：综合信息页签仅展示；编辑回安全信息 / 扫码登记 / 危化品等对应模块。数据真源：腾讯文档教室对齐表 + 分级分类台账。</p>
      </div>`;

    const panels = {
      info: () => {
        const yishiHtml = yishi.length
          ? yishi.map(f => `<li><a href="${esc(f.href)}" target="_blank" rel="noopener">${esc(f.title||'一室一表')}</a></li>`).join('')
          : '<p class="hint">尚未关联一室一表主文件。</p>';
        return `<div class="mod-grid">
          <div class="mod"><h4>实验室综合信息</h4><p>多页签展示，编辑回原模块。本页为该分室专属界面。</p></div>
          <div class="mod"><h4>安全信息电子牌</h4><p>扫码查看分级分类、危险源与责任人，与台账同步。</p></div>
          <div class="mod"><h4>数据交互</h4><p>预留超星课表、资产接口与 Excel 导入。</p></div>
        </div>`
          + '<h3>教务系统</h3>'
          + tablePairs([
            ['教室编号', jw.jw_code],['教室名称', jw.jw_name],['教室类型', jw.type],
            ['是否启用', jw.enabled],['管理部门', jw.dept||jw.tag],
            ['最大上课容纳', jw.class_cap],['考场容纳', jw.exam_cap],
            ['多媒体', jw.multimedia],['监控', jw.monitor],['空调', (jw.ac||'') + (jw.ac_count?(' × '+jw.ac_count):'')],
            ['座位排布', jw.seat_layout],['面积', jw.area],['电脑数量', jw.pc_count],
            ['资产总值', jw.asset_value],['是否考场', jw.as_exam],['门牌号', jw.door_no],
            ['教室描述', jw.desc]
          ])
          + '<h3 style="margin-top:16px">实训系统</h3>'
          + (lab.sys_code ? tablePairs([
            ['系统编号', lab.sys_code],['实训室名称', lab.name],['楼栋 / 楼层 / 房号', [lab.building,lab.floor,lab.room_no].filter(Boolean).join(' · ')],
            ['管理员', (lab.admin_name||'')+' '+ (lab.admin_phone||'')],
            ['责任教师', (lab.teacher_name||'')+' '+(lab.teacher_phone||'')],
            ['院长', (lab.dean_name||'')+' '+(lab.dean_phone||'')],
            ['风险等级', lab.level],['分类', lab.category]
          ]) : '<p class="hint">教务有教室记录，分级分类台账尚未对齐到本编号。请在对齐表中核对照。</p>')
          + '<h3 style="margin-top:16px">一室一表档案</h3>' + (yishi.length?`<ul>${yishiHtml}</ul>`:yishiHtml)
          + '<h3 style="margin-top:16px">教室图片</h3><p class="hint">教务字段「教室图片」当前为空。上传后在本页签展示环境照片（需求表 3.1）。</p>';
      },
      safety: () => {
        const imgHtml = signImgs.length
          ? '<div class="signs">' + signImgs.map(s => {
              const src = s.file ? '../lab-grade-boards/' + s.file : '';
              return src ? `<img src="${esc(src)}" alt="${esc(s.label||'')}">` : '';
            }).join('') + '</div>'
          : '<p class="hint">未挂警示图标。</p>';
        if(!lab.sys_code) return '<p class="hint">本教室尚未对齐实训安全台账，安全信息页签待编号对齐后自动同步。</p>';
        return tablePairs([
          ['实验级别', lab.level],['类别', lab.category],
          ['危险源', lab.hazard],['防护要点', lab.protect],
          ['应急处置', lab.fire],['防范措施', lab.measures],
          ['管理员', (lab.admin_name||'')+' '+(lab.admin_phone||'')],
          ['责任教师', (lab.teacher_name||'')+' '+(lab.teacher_phone||'')]
        ]) + '<h3 style="margin-top:14px">危险源分项</h3>' + listOrDash(lab.hazard_points)
          + '<h3>防护要点分项</h3>' + listOrDash(lab.protect_points)
          + '<h3>警示图标</h3>' + imgHtml
          + (lab.sys_code ? `<p class="hint" style="margin-top:12px"><a href="../lab-grade-boards/home.html?id=${esc(lab.sys_code)}">打开 A4 安全信息牌</a> · 二维码与后台数据同源。</p>` : '');
      },
      schedule: () => `<p class="hint">对接超星课表后按课次/开放时段自动同步。字段：使用人、课程名称、上课人数、起止时间、异常情况。</p>
        <table class="data"><thead><tr><th>使用人</th><th>课程</th><th>人数</th><th>起止时间</th><th>异常</th></tr></thead>
        <tbody><tr><td colspan="5">暂无课表数据（超星接口未开通）</td></tr></tbody></table>`,
      equip: () => `<p class="hint">仪器设备页签补充风险提示。资产系统未开放前，可用 Excel 批量导入；开放后走数据平台同步。</p>
        <table class="data"><thead><tr><th>仪器编号</th><th>名称</th><th>型号</th><th>状态</th><th>风险提示</th></tr></thead>
        <tbody><tr><td colspan="5">暂无设备台账</td></tr></tbody></table>
        <div class="actions"><button class="btn sec" type="button" disabled>Excel 导入（待开通）</button></div>`,
      access: () => `<p class="hint">集中展示本室准入证书状态、有效期与安全承诺书，支持按姓名检索。</p>
        <div class="filters" style="grid-template-columns:1fr auto"><input id="acc-q" type="search" placeholder="按人员姓名检索"><button class="btn sec" type="button">检索</button></div>
        <table class="data"><thead><tr><th>姓名</th><th>身份</th><th>准入证书</th><th>有效期</th><th>承诺书</th></tr></thead>
        <tbody><tr><td colspan="5">暂无准入记录（待学习通 / 安全准入模块回写）</td></tr></tbody></table>`,
      scan: () => scanForm(r),
      inspect: () => inspectForm(r),
      chem: () => r.has_chem
        ? `<p>本室为化学类或含化学品危险源，启用危化品与物资管理页签（申购→入库→领用→归还→库存→危废）。</p>
           <div class="mod-grid">
             <div class="mod"><h4>库存</h4><p>分库库存、预警数量待危化品模块开通后同步。</p></div>
             <div class="mod"><h4>领用 / 归还</h4><p>管制类需双人认证，对齐「五双」。</p></div>
             <div class="mod"><h4>废弃物</h4><p>分类、回收桶与处理明细按实验室归集。</p></div>
           </div>
           <table class="data"><thead><tr><th>品名</th><th>规格</th><th>库存</th><th>预警</th><th>存放</th></tr></thead>
           <tbody><tr><td colspan="5">暂无在库危化品记录</td></tr></tbody></table>`
        : '<p class="hint">本室未启用危化品模块。</p>'
    };

    function paint(name){
      const el = root.querySelector('[data-panel="'+name+'"]');
      if(el && !el.dataset.ready){ el.innerHTML = panels[name](); el.dataset.ready = '1'; }
    }
    paint('info');
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
  }

  function lsKey(kind, id){ return 'gxstzy-room-'+kind+'-'+id; }

  function scanForm(r){
    const saved = JSON.parse(localStorage.getItem(lsKey('scan', r.id))||'[]');
    const rows = saved.length ? saved.map(x => `<tr><td>${esc(x.no)}</td><td>${esc(x.name)}</td><td>${esc(x.device)}</td><td>${esc(x.start)}</td><td>${esc(x.status)}</td></tr>`).join('')
      : '<tr><td colspan="5">暂无扫码登记。以下为本地演示，开通后对接超星身份与教师核验。</td></tr>';
    return `<p class="hint">学生扫设备二维码登记：身份由超星静默校验；提交后推送教师核验。本页先提供本室演示闭环。</p>
      <form id="scan-form">
        <div class="form-grid">
          <div><label class="f">学号</label><input name="sid" type="text" required></div>
          <div><label class="f">姓名</label><input name="name" type="text" required></div>
          <div><label class="f">课程 / 项目</label><input name="course" type="text"></div>
          <div><label class="f">使用设备</label><input name="device" type="text" required></div>
          <div><label class="f">预估时长（分钟）</label><input name="mins" type="number" min="1" value="90"></div>
          <div><label class="f">指导教师</label><input name="teacher" type="text"></div>
        </div>
        <label class="f" style="margin-top:8px">开机前状态</label>
        <label class="chk"><input type="checkbox" name="st" value="外观完好">外观完好、无明显损坏</label>
        <label class="chk"><input type="checkbox" name="st" value="配件缺失">电源线/配件缺失</label>
        <label class="chk"><input type="checkbox" name="st" value="表面破损">表面有破损痕迹</label>
        <label class="chk"><input type="checkbox" name="agree" required>已阅读实验室安全操作规范</label>
        <div class="actions"><button class="btn" type="submit">提交登记</button></div>
      </form>
      <h3 style="margin-top:16px">本室登记明细</h3>
      <table class="data"><thead><tr><th>流水号</th><th>使用人</th><th>设备</th><th>开始</th><th>状态</th></tr></thead><tbody id="scan-rows">${rows}</tbody></table>`;
  }

  function inspectForm(r){
    const saved = JSON.parse(localStorage.getItem(lsKey('inspect', r.id))||'[]');
    const rows = saved.length ? saved.map(x => `<tr><td>${esc(x.time)}</td><td>${esc(x.who)}</td><td>${esc(x.items)}</td><td>${esc(x.result)}</td></tr>`).join('')
      : '<tr><td colspan="4">暂无检查记录。日检下沉到本分室后在此归集。</td></tr>';
    return `<p class="hint">关联「查询统计-按实验室显示」后自动同步检查时间、检查人、隐患、整改与复查。</p>
      <form id="insp-form">
        <div class="form-grid">
          <div><label class="f">检查人</label><input name="who" type="text" required></div>
          <div><label class="f">结论</label><select name="result"><option>正常</option><option>有隐患</option></select></div>
        </div>
        <label class="chk"><input type="checkbox" name="it" value="断电">离开断电 / 电源规范</label>
        <label class="chk"><input type="checkbox" name="it" value="通道">应急通道畅通</label>
        <label class="chk"><input type="checkbox" name="it" value="灭火器">灭火器在位有效</label>
        <label class="chk"><input type="checkbox" name="it" value="危化">危化品柜上锁（如有）</label>
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
        status: [...form.querySelectorAll('input[name=st]:checked')].map(x=>x.value).join('、') || '外观完好'
      };
      const arr = JSON.parse(localStorage.getItem(lsKey('scan', id))||'[]');
      arr.unshift(rec);
      localStorage.setItem(lsKey('scan', id), JSON.stringify(arr.slice(0,50)));
      form.reset();
      document.querySelector('[data-panel="scan"]').dataset.ready = '';
      document.querySelector('[data-tab="scan"]').click();
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
      document.querySelector('[data-panel="inspect"]').dataset.ready = '';
      document.querySelector('[data-tab="inspect"]').click();
    }
  });

  const page = document.body.dataset.page;
  if(page==='catalog') renderCatalog();
  else if(page==='room') renderRoom(document.body.dataset.room);
})();
