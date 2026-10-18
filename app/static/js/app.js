/* 研讯 YanXun — 前端交互（零依赖，零构建） */
(function () {
  'use strict';

  var $ = function (s) { return document.querySelector(s); };
  var state = { school: '', status: '', q: '', items: [], overview: null, poll: null };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function api(path, opts) {
    return fetch(path, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {}))
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      });
  }

  function toast(msg, isErr) {
    var t = $('#toast');
    t.textContent = msg;
    t.className = 'toast show' + (isErr ? ' err' : '');
    clearTimeout(t._h);
    t._h = setTimeout(function () { t.className = 'toast'; }, 2600);
  }

  function clock() {
    var d = new Date();
    var p = function (n) { return n < 10 ? '0' + n : n; };
    $('#clock').textContent = p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }

  /* ---------- 概览 ---------- */
  function loadOverview() {
    return api('/api/overview').then(function (o) {
      state.overview = o;
      var last = o.last_run || {};
      $('#kpiTotal').textContent = o.total || 0;
      $('#kpiSchools').innerHTML = (o.schools || 0) + '<small>/' + (o.sources || []).length + '</small>';
      $('#kpiReview').textContent = o.review || 0;

      var pagesTotal = last.pages_total || 0;
      var pagesOk = last.pages_ok || 0;
      if (pagesTotal) {
        var rate = Math.round(pagesOk / pagesTotal * 100);
        $('#kpiHealth').innerHTML = rate + '<small>%</small>';
        $('#kpiHealthNote').textContent = pagesOk + ' / ' + pagesTotal + ' 页面';
      }
      if (last.raw_count) {
        $('#kpiHit').innerHTML = Math.round(last.accepted / last.raw_count * 100) + '<small>%</small>';
      }

      $('#liveToday').innerHTML = (o.today_new || 0) + '<small>条</small>';
      $('#livePages').innerHTML = pagesOk + '<small>/ ' + pagesTotal + '</small>';
      $('#liveScore').innerHTML = (o.avg_score || 0) + '<small>分</small>';

      renderSpark(o.trend || []);
      fillSchools(o.sources || []);
      renderSources(o.health || [], o.sources || []);
      if (last.finished_at) $('#runId').textContent = 'RUN #' + (last.id || '-');
    }).catch(function () {
      toast('无法连接后端，请确认服务已启动', true);
    });
  }

  function renderSpark(trend) {
    var box = $('#spark');
    if (!box) return;
    var max = 1;
    trend.forEach(function (d) { if (d.n > max) max = d.n; });
    var html = '';
    // 固定 14 格时间轴：缺数据的日期留空柱，今天的高峰才有参照
    var rows = trend.slice(-14);
    var pad = 14 - rows.length;
    for (var i = 0; i < pad; i++) html += '<i style="height:2px"></i>';
    rows.forEach(function (d) {
      var h = d.n ? Math.max(4, Math.round(d.n / max * 26)) : 2;
      var cls = d.n === max && d.n > 0 ? 'peak' : (d.n >= max * 0.6 && d.n > 0 ? 'hot' : '');
      html += '<i class="' + cls + '" style="height:' + h + 'px"></i>';
    });
    box.innerHTML = html;
  }

  function fillSchools(sources) {
    var sel = $('#schoolSel');
    if (sel.options.length > 1) return;
    sources.forEach(function (s) {
      var o = document.createElement('option');
      o.value = s.school; o.textContent = s.school;
      sel.appendChild(o);
    });
  }

  function statusText(k) {
    return { ok: '正常', blocked: '反爬', timeout: '超时', error: '失败', not_found: '404', conn: '连接', idle: '待采' }[k] || '待采';
  }

  function renderSources(health, sources) {
    var map = {};
    health.forEach(function (h) { map[h.school] = h; });
    var ok = 0, total = 0, html = '';
    sources.forEach(function (s) {
      var h = map[s.school];
      var st = h ? (h.status || 'idle') : 'idle';
      if (st === 'ok') ok++;
      total++;
      var extra = h && h.items ? ' · ' + h.items + ' 条' : '';
      html += '<div class="src"><i class="dot ' + esc(st) + '"></i>' +
        '<span class="name">' + esc(s.school) + '</span>' +
        '<span class="st">' + statusText(st) + extra + '</span></div>';
    });
    $('#srcList').innerHTML = html || '<div class="empty">暂无源数据</div>';
    $('#healthNote').textContent = ok + '/' + total + ' 正常';
  }

  /* ---------- 通知列表 ---------- */
  function loadItems() {
    var qs = '?limit=200';
    if (state.school) qs += '&school=' + encodeURIComponent(state.school);
    if (state.status) qs += '&status=' + encodeURIComponent(state.status);
    if (state.q) qs += '&q=' + encodeURIComponent(state.q);
    return api('/api/items' + qs).then(function (r) {
      state.items = r.items || [];
      renderItems();
      renderTicker();
    }).catch(function () {});
  }

  function renderTicker() {
    var top = state.items.slice(0, 6);
    if (!top.length) return;
    var one = top.map(function (it) {
      return '<span><i>·</i><b>' + esc(it.school) + '</b>' + esc(it.title.replace(it.school, '')) + '</span>';
    }).join('');
    $('#tickerTrack').innerHTML = one + one;
  }

  function renderItems() {
    var box = $('#list');
    $('#listCount').textContent = state.items.length;
    if (!state.items.length) {
      box.innerHTML = '<div class="empty"><b>还没有命中记录</b>点击「开始采集」抓取一轮，或调整筛选条件</div>';
      return;
    }
    box.innerHTML = state.items.map(function (it) {
      var tags = (it.tags || '').split(',').filter(Boolean).slice(0, 2).map(function (t) {
        return '<span class="tag' + (/简章|目录|科目/.test(t) ? ' red' : '') + '">' + esc(t) + '</span>';
      }).join('');
      var date = it.publish_date || '未标注日期';
      var star = it.status === 'starred' ? ' on' : '';
      return '<div class="item" data-id="' + it.id + '">' +
        '<div class="item-main">' +
          '<a class="item-title" href="' + esc(it.url) + '" target="_blank" rel="noopener">' + esc(it.title) + '</a>' +
          '<div class="item-meta">' +
            '<span class="school">' + esc(it.school) + '</span><i class="sep"></i>' +
            '<span>' + esc(date) + '</span><i class="sep"></i>' + tags +
          '</div>' +
        '</div>' +
        '<div class="item-side">' +
          '<div class="score"><span class="bar"><i style="width:' + Math.min(100, it.score) + '%"></i></span>' + it.score + '</div>' +
          '<div class="acts">' +
            '<button class="icon-btn' + star + '" data-act="star" title="收藏">' +
              '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m12 3 2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 18l-5.9 3 1.2-6.5L2.5 9.9 9.1 9z"/></svg>' +
            '</button>' +
            '<button class="icon-btn" data-act="ignore" title="忽略">' +
              '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/></svg>' +
            '</button>' +
          '</div>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.icon-btn');
    if (!btn) return;
    var row = btn.closest('.item');
    var id = row && row.getAttribute('data-id');
    if (!id) return;
    var act = btn.getAttribute('data-act');
    var status = act === 'star' ? 'starred' : 'ignored';
    api('/api/items/' + id + '/status', { method: 'POST', body: JSON.stringify({ status: status }) })
      .then(function () {
        toast(act === 'star' ? '已收藏' : '已忽略');
        loadItems(); loadOverview();
      }).catch(function () { toast('操作失败', true); });
  });

  /* ---------- 采集 ---------- */
  function setRunning(on) {
    $('#btnRun').disabled = on;
    $('#btnRunSide').disabled = on;
    $('#btnRunTop').disabled = on;
    $('#runState').textContent = on ? '采集中…' : '空闲';
    $('#navState').textContent = on ? '正在采集' : '监控运行中';
  }

  function startRun() {
    if (state.poll) return;
    api('/api/run', { method: 'POST', body: JSON.stringify({}) })
      .then(function (r) {
        if (!r.ok) { toast('任务已在运行', true); return; }
        setRunning(true);
        toast('采集任务已启动');
        state.poll = setInterval(pollRun, 900);
      }).catch(function () { toast('启动失败', true); });
  }

  function pollRun() {
    api('/api/run/status').then(function (s) {
      $('#runBar').style.width = (s.percent || 0) + '%';
      $('#runPct').textContent = (s.percent || 0) + '%';
      $('#rsPages').textContent = (s.pages_ok || 0) + '/' + (s.pages_total || 0);
      $('#rsHits').textContent = s.accepted || 0;
      $('#rsNew').textContent = s.new_count || 0;
      if (s.run_id) $('#runId').textContent = 'RUN #' + s.run_id;
      if (s.current) $('#runState').textContent = s.current.slice(0, 26);
      if (s.log && s.log.length) {
        $('#log').innerHTML = s.log.slice(-30).map(function (l) {
          var cls = l.indexOf('✗') >= 0 || l.indexOf('!') >= 0 ? 'err' : (l.indexOf('✓') >= 0 ? 'ok' : '');
          return '<div class="' + cls + '">' + esc(l) + '</div>';
        }).join('');
        $('#log').scrollTop = 99999;
      }
      if (!s.running) {
        clearInterval(state.poll); state.poll = null;
        setRunning(false);
        $('#runBar').style.width = '100%';
        loadOverview(); loadItems();
        toast('采集完成，新增 ' + (s.new_count || 0) + ' 条');
      }
    }).catch(function () {
      clearInterval(state.poll); state.poll = null; setRunning(false);
    });
  }

  /* ---------- 部署 tab ---------- */
  var SNIPPETS = {
    conda: '<span class="c"># 1. 克隆</span>\ngit clone https://github.com/&lt;you&gt;/yanxun.git\n<span class="k">cd</span> yanxun\n\n<span class="c"># 2. 创建 conda 环境（已存在则跳过）</span>\nconda create -n pyy python=3.11 -y\nconda activate pyy\npip install -r requirements.txt\n\n<span class="c"># 3. 启动</span>\npython run.py\n<span class="c"># -> http://127.0.0.1:8000</span>',
    docker: '<span class="c"># 构建并后台启动</span>\ndocker compose -f deploy/docker-compose.yml up -d --build\n\n<span class="c"># 查看日志 / 停止</span>\ndocker logs -f yanxun\ndocker compose -f deploy/docker-compose.yml down\n\n<span class="c"># 数据持久化在 ./data</span>\n<span class="p">YANXUN_PORT</span>=8000',
    actions: '<span class="c"># .github/workflows/ci.yml 已内置</span>\n<span class="k">on</span>: [push, pull_request]\n<span class="k">jobs</span>:\n  test:\n    <span class="p">runs-on</span>: ubuntu-latest\n    <span class="p">steps</span>:\n      - <span class="p">uses</span>: actions/checkout@v4\n      - <span class="p">uses</span>: actions/setup-python@v5\n        <span class="p">with</span>: {python-version: <span class="s">"3.11"</span>}\n      - <span class="p">run</span>: pip install -r requirements.txt pytest\n      - <span class="p">run</span>: pytest -q'
  };

  /* ---------- 初始化 ---------- */
  function init() {
    clock(); setInterval(clock, 1000);

    document.querySelectorAll('#tabs .tab').forEach(function (t) {
      t.addEventListener('click', function () {
        document.querySelectorAll('#tabs .tab').forEach(function (x) { x.classList.remove('active'); });
        t.classList.add('active');
        $('#codeBox').innerHTML = SNIPPETS[t.getAttribute('data-tab')] || '';
      });
    });

    var timer = null;
    $('#q').addEventListener('input', function (e) {
      clearTimeout(timer);
      timer = setTimeout(function () { state.q = e.target.value.trim(); loadItems(); }, 260);
    });
    $('#schoolSel').addEventListener('change', function (e) {
      state.school = e.target.value; loadItems();
    });
    document.querySelectorAll('.chip').forEach(function (c) {
      c.addEventListener('click', function () {
        document.querySelectorAll('.chip').forEach(function (x) { x.classList.remove('active'); });
        c.classList.add('active');
        state.status = c.getAttribute('data-status'); loadItems();
      });
    });

    ['#btnRun', '#btnRunSide', '#btnRunTop'].forEach(function (sel) {
      var el = $(sel);
      if (el) el.addEventListener('click', startRun);
    });
    $('#btnExport').addEventListener('click', function () { window.location.href = '/api/export.md'; });

    loadOverview().then(loadItems);
    api('/api/run/status').then(function (s) {
      if (s.running) { setRunning(true); state.poll = setInterval(pollRun, 900); }
    }).catch(function () {});
  }

  document.addEventListener('DOMContentLoaded', init);
})();
