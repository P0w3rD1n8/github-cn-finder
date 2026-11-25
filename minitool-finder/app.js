/* GitHub 中文发现器 · 离线小工具 v1.0.0
 * 纯前端、无网络请求；数据来自内置 tool-data.js（截至 2026-11-25）。
 * 功能：榜单、分类/用途筛选、搜索、四段详情、收藏（本地缓存）。
 */
(function () {
  'use strict';

  var NOW = Date.parse('2026-11-25T00:00:00+08:00');
  var DAY = 86400000;
  var PAGE = 20;
  var STORE_KEY = 'fav:v1';

  /* ---------------- 工具函数 ---------------- */

  function $(id) { return document.getElementById(id); }

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function daysSince(dateStr) {
    if (!dateStr) return null;
    var t = Date.parse(dateStr + 'T00:00:00+08:00');
    if (isNaN(t)) return null;
    return Math.floor((NOW - t) / DAY);
  }

  function fmtStars(n) {
    if (n >= 10000) return (n / 10000).toFixed(1) + ' 万';
    return String(n);
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  /* ---------------- 内置数据 ---------------- */

  var RAW = window.TOOL_DATA || [];
  var ITEMS = RAW.map(function (r) {
    return {
      name: r[0], desc: r[1], stars: r[2], lang: r[3], cat: r[4],
      pushed: r[5], growth: r[6], forks: r[7], issues: r[8], archived: r[9],
      usage: r[10] || [], detail: r[11] || ''
    };
  });

  var BY_NAME = {};
  ITEMS.forEach(function (it) { BY_NAME[it.name] = it; });

  /* ---------------- 收藏（本地缓存） ---------------- */

  // 容器内用平台 Storage（客户端 9.46+）；浏览器预览退化为内存，不读写浏览器存储。
  var memStore = '';

  function storeGet() {
    try {
      if (window.xhs && window.xhs.miniTool && window.xhs.miniTool.getStorage) {
        var r = window.xhs.miniTool.getStorage({ key: STORE_KEY });
        if (r && typeof r.data === 'string') return r.data;
        return '';
      }
    } catch (e) {}
    return memStore;
  }

  function storeSet(value) {
    try {
      if (window.xhs && window.xhs.miniTool && window.xhs.miniTool.setStorage) {
        window.xhs.miniTool.setStorage({ key: STORE_KEY, data: value });
        return;
      }
    } catch (e) {}
    memStore = value;
  }

  var favs = [];
  (function loadFavs() {
    try {
      var arr = JSON.parse(storeGet() || '[]');
      if (arr && arr.length) {
        for (var i = 0; i < arr.length; i++) {
          if (BY_NAME[arr[i]]) favs.push(arr[i]);
        }
      }
    } catch (e) { favs = []; }
  })();

  function isFav(name) { return favs.indexOf(name) >= 0; }

  function toggleFav(name) {
    var i = favs.indexOf(name);
    if (i >= 0) favs.splice(i, 1); else favs.push(name);
    storeSet(JSON.stringify(favs));
  }

  /* ---------------- 「值不值得装」判断 ---------------- */

  function dimsOf(item) {
    var out = [];

    var d = daysSince(item.pushed);
    if (item.archived) {
      out.push({ k: '还在维护吗', v: '已归档', cls: 'r',
        x: '作者把它封存了，不会再修问题', key: '维护' });
    } else if (d === null) {
      out.push({ k: '还在维护吗', v: '看不出来', cls: 'y', x: '没有可用信息', key: '维护' });
    } else if (d <= 90) {
      out.push({ k: '还在维护吗', v: '活跃', cls: 'g',
        x: '最近一次推送 ' + item.pushed, key: '维护' });
    } else if (d <= 365) {
      out.push({ k: '还在维护吗', v: '偶尔动一下', cls: 'y',
        x: '最近一次推送 ' + item.pushed + '，差不多 ' + Math.round(d / 30) + ' 个月前', key: '维护' });
    } else {
      out.push({ k: '还在维护吗', v: '很久没动了', cls: 'r',
        x: '最近一次推送 ' + item.pushed + '，已超过一年', key: '维护' });
    }

    var g = item.growth;
    var forkRatio = item.stars ? item.forks / item.stars : 0;
    if (g >= 25 && item.stars >= 20000 && forkRatio < 0.05) {
      out.push({ k: '热度走势', v: '涨得太快，留个心眼', cls: 'y',
        x: '短时间涨 ' + g + '%，但 fork 只有 star 的 ' + Math.round(forkRatio * 100) + '%',
        key: '热度' });
    } else if (g >= 5) {
      out.push({ k: '热度走势', v: '在稳步涨', cls: 'g', x: '这一轮涨了 ' + g + '%', key: '热度' });
    } else if (g >= 1) {
      out.push({ k: '热度走势', v: '涨得慢', cls: 'y', x: '这一轮只涨了 ' + g + '%', key: '热度' });
    } else if (g >= 0) {
      out.push({ k: '热度走势', v: '基本没动', cls: 'y', x: '这一轮变化 ' + g + '%，热度停住了', key: '热度' });
    } else {
      out.push({ k: '热度走势', v: '在退', cls: 'r', x: '这一轮掉了 ' + Math.abs(g) + '%', key: '热度' });
    }

    var issueRatio = item.stars ? item.issues / item.stars : 0;
    if (issueRatio > 0.15) {
      out.push({ k: '社区', v: '问题堆积', cls: 'r',
        x: '未解决的 issue 有 ' + item.issues + ' 个，相对 star 数偏多', key: '社区' });
    } else if (forkRatio >= 0.08) {
      out.push({ k: '社区', v: '有人跟着改', cls: 'g',
        x: 'fork ' + fmtStars(item.forks) + '，说明有人真的在用、在改', key: '社区' });
    } else if (forkRatio >= 0.03) {
      out.push({ k: '社区', v: '围观多、动手少', cls: 'y',
        x: 'fork 只有 star 的 ' + Math.round(forkRatio * 100) + '%', key: '社区' });
    } else {
      out.push({ k: '社区', v: '基本纯围观', cls: 'y',
        x: 'fork 只有 ' + fmtStars(item.forks) + '，出了问题多半得自己扛', key: '社区' });
    }

    if (item.stars >= 20000) {
      out.push({ k: '用的人多不多', v: '人多，踩坑能搜到', cls: 'g',
        x: fmtStars(item.stars) + ' 星标', key: '规模' });
    } else if (item.stars >= 3000) {
      out.push({ k: '用的人多不多', v: '中等规模', cls: 'y',
        x: fmtStars(item.stars) + ' star，遇问题可能要自己想办法', key: '规模' });
    } else {
      out.push({ k: '用的人多不多', v: '小众，资料少', cls: 'y',
        x: fmtStars(item.stars) + ' 星标', key: '规模' });
    }

    return out;
  }

  var LEVELS = [
    { min: 7, lv: 3, t: '放心用', tx: '四个维度都过得去，可以当日常工具用。' },
    { min: 5, lv: 2, t: '可以用，但留条后路', tx: '能用，只是某一块有短板。先别把重要文件只放它一处。' },
    { min: 3, lv: 1, t: '谨慎，先小范围试', tx: '有明显短板。先拿它干点不重要的事，跑一周再说。' },
    { min: 0, lv: 0, t: '暂时别用', tx: '风险大于收益。同样的事，找个还在维护的替代品更省心。' }
  ];

  function levelOf(dims) {
    var sum = 0;
    for (var i = 0; i < dims.length; i++) {
      sum += dims[i].cls === 'g' ? 2 : (dims[i].cls === 'y' ? 1 : 0);
    }
    var lv = LEVELS[LEVELS.length - 1];
    for (var j = 0; j < LEVELS.length; j++) {
      if (sum >= LEVELS[j].min) { lv = LEVELS[j]; break; }
    }
    return { score: sum, max: dims.length * 2, level: lv };
  }

  function weakest(dims) {
    var order = { r: 0, y: 1, g: 2 };
    var worst = null;
    for (var i = 0; i < dims.length; i++) {
      if (!worst || order[dims[i].cls] < order[worst.cls]) worst = dims[i];
    }
    return worst;
  }

  var TODO_BY_KEY = {
    '维护': '先看它的最近更新日期。一年没动的项目，装之前先想好：出问题谁来修。',
    '热度': '去翻翻它最近的讨论区，看看大家在聊什么、有没有人已经换掉了。',
    '社区': '去它的 issue 列表翻两页，看看别人问的问题有人回没有。没人回，等于没有客服。',
    '规模': '用的人少，教程和踩坑记录就少。先搜一下有没有别人写过使用心得。'
  };

  /* ---------------- 视图切换 ---------------- */

  var views = { discover: $('view-discover'), fav: $('view-fav'), detail: $('view-detail') };
  var backTo = 'discover';

  function show(name) {
    for (var k in views) {
      if (views.hasOwnProperty(k)) views[k].className = 'view' + (k === name ? '' : ' is-hide');
    }
    window.scrollTo(0, 0);
  }

  function tabOn(which) {
    var ids = { discover: 'tab-discover', fav: 'tab-fav' };
    for (var k in ids) {
      if (ids.hasOwnProperty(k)) $(ids[k]).className = 'tab' + (k === which ? ' is-on' : '');
    }
  }

  /* ---------------- 榜单 ---------------- */

  function topBy(key, n) {
    return ITEMS.slice().sort(function (a, b) { return b[key] - a[key]; }).slice(0, n);
  }

  function renderBoards() {
    var box = $('boards');
    clear(box);

    addBoard(box, '最近涨得最快', topBy('growth', 5), function (it) {
      return '+' + it.growth + '%';
    });
    addBoard(box, '用的人最多', topBy('stars', 5), function (it) {
      return fmtStars(it.stars);
    });
  }

  function addBoard(box, title, items, valueOf) {
    var board = el('div', 'board');
    board.appendChild(el('div', 'board-t', title));
    items.forEach(function (it, i) {
      var row = el('button', 'brow');
      row.type = 'button';
      row.setAttribute('data-name', it.name);
      row.appendChild(el('span', 'brank', String(i + 1)));
      row.appendChild(el('span', 'bname', it.name));
      row.appendChild(el('span', 'bval', valueOf(it)));
      board.appendChild(row);
    });
    box.appendChild(board);
  }

  $('boards').addEventListener('click', function (ev) {
    var node = ev.target;
    while (node && node !== this && !node.getAttribute('data-name')) node = node.parentNode;
    if (!node || node === this) return;
    var it = BY_NAME[node.getAttribute('data-name')];
    if (it) openDetail(it, 'discover');
  });

  /* ---------------- 用途 / 分类 ---------------- */

  var USES = [];
  (function buildUses() {
    var seen = {};
    ITEMS.forEach(function (it) {
      it.usage.forEach(function (u) { seen[u] = (seen[u] || 0) + 1; });
    });
    var order = ['普通用户', '程序员', '学编程', '自媒体创作者', '设计师', '视频剪辑', '游戏玩家', '自托管/运维'];
    order.forEach(function (u) { if (seen[u]) USES.push(u); });
    for (var u in seen) {
      if (seen.hasOwnProperty(u) && order.indexOf(u) < 0) USES.push(u);
    }
  })();

  var curUse = '全部';
  var curCat = '全部';
  var curQuery = '';
  var shown = 0;
  var filtered = [];

  function renderUses() {
    var box = $('uses');
    clear(box);
    var all = ['全部'].concat(USES);
    all.forEach(function (u) {
      var b = el('button', 'use' + (u === curUse ? ' is-on' : ''), u);
      b.type = 'button';
      b.setAttribute('data-use', u);
      box.appendChild(b);
    });
  }

  $('uses').addEventListener('click', function (ev) {
    var node = ev.target;
    while (node && node !== this && !node.getAttribute('data-use')) node = node.parentNode;
    if (!node || node === this) return;
    curUse = node.getAttribute('data-use');
    renderUses();
    applyFilter();
  });

  function categories() {
    var seen = {};
    var out = ['全部'];
    ITEMS.forEach(function (it) {
      if (!seen[it.cat]) { seen[it.cat] = 1; out.push(it.cat); }
    });
    return out;
  }

  function renderCats() {
    var box = $('cats');
    clear(box);
    categories().forEach(function (c) {
      var b = el('button', 'cat' + (c === curCat ? ' is-on' : ''), c);
      b.type = 'button';
      b.setAttribute('data-cat', c);
      box.appendChild(b);
    });
  }

  $('cats').addEventListener('click', function (ev) {
    var node = ev.target;
    while (node && node !== this && !node.getAttribute('data-cat')) node = node.parentNode;
    if (!node || node === this) return;
    curCat = node.getAttribute('data-cat');
    renderCats();
    applyFilter();
  });

  function matches(it, q) {
    if (curUse !== '全部' && it.usage.indexOf(curUse) < 0) return false;
    if (curCat !== '全部' && it.cat !== curCat) return false;
    if (!q) return true;
    return it.name.toLowerCase().indexOf(q) >= 0 ||
      it.desc.toLowerCase().indexOf(q) >= 0 ||
      it.cat.toLowerCase().indexOf(q) >= 0;
  }

  function applyFilter() {
    var q = curQuery.toLowerCase();
    filtered = ITEMS.filter(function (it) { return matches(it, q); });
    filtered.sort(function (a, b) { return b.stars - a.stars; });
    shown = 0;
    var list = $('list');
    clear(list);
    appendRows();
    $('empty').className = filtered.length ? 'empty is-hide' : 'empty';
    var filtering = q || curUse !== '全部' || curCat !== '全部';
    $('boards').className = filtering ? 'is-hide' : '';
    $('listNote').textContent = filtering
      ? '共 ' + filtered.length + ' 个' +
        (curUse === '全部' ? '' : ' · 用途：' + curUse) +
        (curCat === '全部' ? '' : ' · 分类：' + curCat)
      : '共 ' + filtered.length + ' 个，按星标排序';
    $('moreBar').className = filtered.length > shown ? 'bar' : 'bar is-hide';
  }

  function rowOf(it) {
    var row = el('div', 'row');
    row.setAttribute('data-name', it.name);

    var left = el('div', 'row-l');
    left.appendChild(el('div', 'row-n', it.name));
    left.appendChild(el('div', 'row-d', it.desc));
    var tags = el('div', 'row-t');
    tags.textContent = it.usage.join(' · ') || it.cat;
    left.appendChild(tags);
    row.appendChild(left);

    var right = el('div', 'row-r');
    right.appendChild(el('div', 'row-s', fmtStars(it.stars)));
    right.appendChild(el('div', 'row-g', it.cat));
    row.appendChild(right);

    var fav = el('button', 'row-fav' + (isFav(it.name) ? ' is-on' : ''), isFav(it.name) ? '★' : '☆');
    fav.type = 'button';
    fav.setAttribute('data-fav', it.name);
    row.appendChild(fav);
    return row;
  }

  function appendRows() {
    var list = $('list');
    var end = Math.min(shown + PAGE, filtered.length);
    for (var i = shown; i < end; i++) {
      list.appendChild(rowOf(filtered[i]));
    }
    shown = end;
    $('moreBar').className = filtered.length > shown ? 'bar' : 'bar is-hide';
  }

  $('list').addEventListener('click', function (ev) {
    var node = ev.target;
    while (node && node !== this && !node.getAttribute('data-name')) node = node.parentNode;
    if (!node || node === this) return;
    var name = node.getAttribute('data-name');

    var hit = ev.target;
    while (hit && hit !== node && !hit.getAttribute('data-fav')) hit = hit.parentNode;
    if (hit && hit !== node && hit.getAttribute('data-fav')) {
      toggleFav(name);
      var on = isFav(name);
      hit.className = 'row-fav' + (on ? ' is-on' : '');
      hit.textContent = on ? '★' : '☆';
      return;
    }
    if (BY_NAME[name]) openDetail(BY_NAME[name], 'discover');
  });

  $('btnMore').addEventListener('click', appendRows);

  var timer = null;
  $('q').addEventListener('input', function () {
    var v = this.value || '';
    if (timer) clearTimeout(timer);
    timer = setTimeout(function () {
      curQuery = v.trim();
      applyFilter();
    }, 120);
  });

  /* ---------------- 收藏视图 ---------------- */

  function renderFavs() {
    var list = $('favList');
    clear(list);
    var items = favs.map(function (n) { return BY_NAME[n]; }).filter(Boolean);
    items.sort(function (a, b) { return b.stars - a.stars; });
    items.forEach(function (it) { list.appendChild(rowOf(it)); });
    $('favEmpty').className = items.length ? 'empty is-hide' : 'empty';
    $('favLead').textContent = items.length
      ? '已收藏 ' + items.length + ' 个。收藏存在手机本地，换设备不会同步。'
      : '收藏是存在你手机本地的，换设备不会同步。';
  }

  $('favList').addEventListener('click', function (ev) {
    var node = ev.target;
    while (node && node !== this && !node.getAttribute('data-name')) node = node.parentNode;
    if (!node || node === this) return;
    var name = node.getAttribute('data-name');

    var hit = ev.target;
    while (hit && hit !== node && !hit.getAttribute('data-fav')) hit = hit.parentNode;
    if (hit && hit !== node && hit.getAttribute('data-fav')) {
      toggleFav(name);
      renderFavs();
      return;
    }
    if (BY_NAME[name]) openDetail(BY_NAME[name], 'fav');
  });

  /* ---------------- 详情 ---------------- */

  function parseDetail(str) {
    if (!str) return [];
    var out = [];
    var lines = str.split('\n');
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].replace(/^\s+|\s+$/g, '');
      if (!line) continue;
      var p = line.indexOf('：');
      if (p < 0) out.push({ t: '', b: line });
      else out.push({ t: line.slice(0, p), b: line.slice(p + 1) });
    }
    return out;
  }

  function openDetail(it, from) {
    backTo = from || 'discover';
    var box = $('detailBody');
    clear(box);

    box.appendChild(el('div', 'd-name', it.name));
    box.appendChild(el('div', 'd-desc', it.desc));
    box.appendChild(el('div', 'd-meta',
      it.cat + ' · ' + it.lang + ' · ' + fmtStars(it.stars) + ' 星标' +
      (it.usage.length ? ' · ' + it.usage.join(' / ') : '')));

    var favBar = el('div', 'favbar');
    var fb = el('button', 'favbtn' + (isFav(it.name) ? ' is-on' : ''),
      isFav(it.name) ? '★ 已收藏，点一下取消' : '☆ 收藏这个项目');
    fb.type = 'button';
    fb.addEventListener('click', function () {
      toggleFav(it.name);
      var on = isFav(it.name);
      fb.className = 'favbtn' + (on ? ' is-on' : '');
      fb.textContent = on ? '★ 已收藏，点一下取消' : '☆ 收藏这个项目';
      renderFavs();
    });
    favBar.appendChild(fb);
    box.appendChild(favBar);

    var dims = dimsOf(it);
    var res = levelOf(dims);

    var v = el('div', 'verdict');
    v.appendChild(el('div', 'verdict-lv lv' + res.level.lv, res.level.t));
    v.appendChild(el('div', 'verdict-tx', res.level.tx));
    box.appendChild(v);

    var secs = parseDetail(it.detail);
    if (secs.length) {
      var wrap = el('div', 'secs');
      wrap.appendChild(el('div', 'secs-t', '这是什么、能干什么'));
      secs.forEach(function (s) {
        var row = el('div', 'sec');
        if (s.t) row.appendChild(el('div', 'sec-t', s.t));
        row.appendChild(el('div', 'sec-b', s.b));
        wrap.appendChild(row);
      });
      box.appendChild(wrap);
    }

    var list = el('div', 'dims');
    list.appendChild(el('div', 'secs-t', '现在能不能放心用'));
    dims.forEach(function (d) {
      var row = el('div', 'dim');
      row.appendChild(el('span', 'dot ' + d.cls));
      var left = el('div', 'dim-l');
      left.appendChild(el('div', 'dim-k', d.k + '：' + d.v));
      if (d.x) left.appendChild(el('div', 'dim-x', d.x));
      row.appendChild(left);
      list.appendChild(row);
    });
    box.appendChild(list);

    var w = weakest(dims);
    var todo = el('div', 'todo');
    todo.appendChild(el('div', 'todo-t',
      res.level.lv === 3 ? '还能更稳一点的地方' : '最该先确认的一件事'));
    todo.appendChild(el('div', 'todo-x', TODO_BY_KEY[w.key] || '先用一周再决定。'));
    box.appendChild(todo);

    show('detail');
  }

  $('btnBack').addEventListener('click', function () {
    if (backTo === 'fav') { tabOn('fav'); renderFavs(); show('fav'); }
    else { tabOn('discover'); show('discover'); }
  });

  /* ---------------- 顶部切换 ---------------- */

  $('tab-discover').addEventListener('click', function () {
    tabOn('discover');
    show('discover');
  });

  $('tab-fav').addEventListener('click', function () {
    tabOn('fav');
    renderFavs();
    show('fav');
  });

  /* ---------------- 启动 ---------------- */

  renderBoards();
  renderUses();
  renderCats();
  renderFavs();
  applyFilter();
  show('discover');
  tabOn('discover');
})();
