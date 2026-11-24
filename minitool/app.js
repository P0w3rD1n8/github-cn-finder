/* 开源项目速判器 · 离线小工具
 * 纯前端、无网络请求；数据来自内置 tool-data.js（截至 2026-11-24）。
 */
(function () {
  'use strict';

  var NOW = Date.parse('2026-11-24T00:00:00+08:00');
  var DAY = 86400000;
  var PAGE = 20;

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
      pushed: r[5], growth: r[6], forks: r[7], issues: r[8], archived: r[9]
    };
  });

  /* ---------------- 判断规则 ---------------- */

  function dimsOf(item) {
    var out = [];

    // 1. 还在维护吗
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

    // 2. 热度走势（用 24 期星标变化）
    var g = item.growth;
    var forkRatio = item.stars ? item.forks / item.stars : 0;
    if (g >= 25 && item.stars >= 20000 && forkRatio < 0.05) {
      out.push({ k: '热度走势', v: '涨得太快，留个心眼', cls: 'y',
        x: '短时间涨 ' + g + '%，但 fork 只有 star 的 ' + Math.round(forkRatio * 100) + '%',
        key: '热度' });
    } else if (g >= 5) {
      out.push({ k: '热度走势', v: '在稳步涨', cls: 'g',
        x: '这一轮涨了 ' + g + '%', key: '热度' });
    } else if (g >= 1) {
      out.push({ k: '热度走势', v: '涨得慢', cls: 'y',
        x: '这一轮只涨了 ' + g + '%', key: '热度' });
    } else if (g >= 0) {
      out.push({ k: '热度走势', v: '基本没动', cls: 'y',
        x: '这一轮变化 ' + g + '%，热度停住了', key: '热度' });
    } else {
      out.push({ k: '热度走势', v: '在退', cls: 'r',
        x: '这一轮掉了 ' + Math.abs(g) + '%', key: '热度' });
    }

    // 3. 社区
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

    // 4. 用的人多不多
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

  function levelOf(score, dims) {
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

  /* ---------------- 自己判：问答 ---------------- */

  var QUESTIONS = [
    { q: '它最近一次更新是什么时候？',
      opts: [['三个月内', 2], ['半年内', 1], ['一年以上', 0], ['很久没动了', -1], ['没注意过', 0]] },
    { q: '它的 star 数这几个月在变吗？',
      opts: [['一直在涨', 2], ['基本没变', 0], ['突然暴涨', 0], ['在往下掉', -1], ['没看过', 0]] },
    { q: '有人提问题，作者回吗？',
      opts: [['几天内就有人回', 2], ['回得慢，但会回', 1], ['基本没人理', -1], ['没提过', 0]] },
    { q: '它的说明，你看得懂吗？',
      opts: [['中文说明很清楚', 2], ['英文，但能啃下来', 1], ['看不懂', -1]] },
    { q: '真出了问题，谁来修？',
      opts: [['有团队或公司在维护', 2], ['个人作者，但一直在更新', 1], ['作者好像不露面了', -1], ['不知道', 0]] }
  ];

  var answers = {};

  var LV_SELF = [
    { min: 8, lv: 3, t: '放心用', tx: '几个关键点都站得住，可以放心用起来。' },
    { min: 6, lv: 2, t: '可以用，但留条后路', tx: '能用。先把数据留个备份，等用顺了再完全依赖它。' },
    { min: 4, lv: 1, t: '谨慎，先小范围试', tx: '有硬伤。先拿它做不重要的事，跑一段时间再决定。' },
    { min: -99, lv: 0, t: '暂时别用', tx: '这几个问题里踩了两条以上红线，换个替代品更省时间。' }
  ];

  var TODO_SELF = [
    '先确认它最近还更新吗。一年没动的项目，等于没人管。',
    '去它的 issue 列表翻两页，看看别人问的问题有没有人回。',
    '先找到替代品再决定。只装一个来源不明的工具，风险最大。',
    '把说明看一遍再装。看不懂说明，等于不会用它的应急方案。',
    '看看作者还有没有在别的地方出现。人不见了，问题就只能自己扛。'
  ];

  /* ---------------- 视图切换 ---------------- */

  var views = { check: $('view-check'), lib: $('view-lib'), detail: $('view-detail') };
  var backTo = 'check';

  function show(name) {
    for (var k in views) {
      if (views.hasOwnProperty(k)) views[k].className = 'view' + (k === name ? '' : ' is-hide');
    }
    window.scrollTo(0, 0);
  }

  function tabOn(which) {
    $('tab-check').className = 'tab' + (which === 'check' ? ' is-on' : '');
    $('tab-lib').className = 'tab' + (which === 'lib' ? ' is-on' : '');
  }

  /* ---------------- 问答渲染 ---------------- */

  function renderQuestions() {
    var box = $('questions');
    clear(box);
    QUESTIONS.forEach(function (item, qi) {
      var wrap = el('div', 'q');
      var t = el('div', 'q-t');
      t.appendChild(document.createTextNode((qi + 1) + '. ' + item.q));
      wrap.appendChild(t);

      var opts = el('div', 'opts');
      item.opts.forEach(function (pair, oi) {
        var b = el('button', 'opt', pair[0]);
        b.type = 'button';
        b.setAttribute('data-q', String(qi));
        b.setAttribute('data-o', String(oi));
        if (answers[qi] === oi) b.className = 'opt is-on';
        opts.appendChild(b);
      });
      wrap.appendChild(opts);
      box.appendChild(wrap);
    });
    updateCheckBar();
  }

  function updateCheckBar() {
    var n = 0;
    for (var k in answers) { if (answers.hasOwnProperty(k)) n++; }
    var left = QUESTIONS.length - n;
    $('btnJudge').disabled = left > 0;
    $('checkHint').textContent = left > 0 ? ('还有 ' + left + ' 题要选') : '都选完了，点上面看结论';
  }

  $('questions').addEventListener('click', function (ev) {
    var node = ev.target;
    while (node && node !== this && !node.getAttribute('data-q')) node = node.parentNode;
    if (!node || node === this) return;
    var qi = Number(node.getAttribute('data-q'));
    var oi = Number(node.getAttribute('data-o'));
    answers[qi] = oi;

    var group = node.parentNode;
    var kids = group.children;
    for (var i = 0; i < kids.length; i++) {
      if (kids[i].className && kids[i].className.indexOf('opt') === 0) {
        kids[i].className = kids[i] === node ? 'opt is-on' : 'opt';
      }
    }
    updateCheckBar();
  });

  $('btnJudge').addEventListener('click', function () {
    var total = 0;
    var picked = [];
    var lowIdx = -1;
    var lowVal = 99;
    QUESTIONS.forEach(function (item, qi) {
      var oi = answers[qi];
      if (oi === undefined) return;
      var pair = item.opts[oi];
      total += pair[1];
      picked.push({ q: item.q, a: pair[0] });
      if (pair[1] < lowVal) { lowVal = pair[1]; lowIdx = qi; }
    });

    var lvl = LV_SELF[LV_SELF.length - 1];
    for (var i = 0; i < LV_SELF.length; i++) {
      if (total >= LV_SELF[i].min) { lvl = LV_SELF[i]; break; }
    }

    backTo = 'check';
    tabOn('check');
    renderSelfResult(total, lvl, picked, lowIdx);
    show('detail');
  });

  function renderSelfResult(total, lvl, picked, lowIdx) {
    var box = $('detailBody');
    clear(box);

    box.appendChild(el('div', 'd-name', '你这个项目的判断结果'));
    box.appendChild(el('div', 'd-desc', '按你选的 5 个情况，加总 ' + total + ' 分（满分 10）。'));

    var v = el('div', 'verdict');
    var lv = el('div', 'verdict-lv lv' + lvl.lv, lvl.t);
    v.appendChild(lv);
    v.appendChild(el('div', 'verdict-tx', lvl.tx));
    box.appendChild(v);

    var dims = el('div', 'dims');
    picked.forEach(function (p) {
      var row = el('div', 'dim');
      row.appendChild(el('span', 'dot y'));
      var left = el('div', 'dim-l');
      left.appendChild(el('div', 'dim-k', p.q));
      left.appendChild(el('div', 'dim-v', p.a));
      row.appendChild(left);
      dims.appendChild(row);
    });
    box.appendChild(dims);

    var todo = el('div', 'todo');
    todo.appendChild(el('div', 'todo-t', '下一步先做这一件事'));
    var tip = TODO_SELF[3];
    if (total >= 8) tip = '先用起来。顺手记一下你对它不满意的地方，一周后就知道要不要换。';
    else if (lowIdx >= 0 && lowIdx < TODO_SELF.length) tip = TODO_SELF[lowIdx];
    todo.appendChild(el('div', 'todo-x', tip));
    box.appendChild(todo);

    var bar = el('div', 'bar');
    var again = el('button', 'btn btn-ghost', '再判一个');
    again.type = 'button';
    again.addEventListener('click', function () {
      answers = {};
      renderQuestions();
      tabOn('check');
      show('check');
    });
    bar.appendChild(again);
    box.appendChild(bar);
  }

  /* ---------------- 内置库 ---------------- */

  var curCat = '全部';
  var curQuery = '';
  var shown = 0;
  var filtered = [];

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

  function applyFilter() {
    var q = curQuery.toLowerCase();
    filtered = ITEMS.filter(function (it) {
      if (curCat !== '全部' && it.cat !== curCat) return false;
      if (!q) return true;
      return it.name.toLowerCase().indexOf(q) >= 0 || it.desc.toLowerCase().indexOf(q) >= 0;
    });
    filtered.sort(function (a, b) { return b.stars - a.stars; });
    shown = 0;
    var list = $('list');
    clear(list);
    appendRows();
    $('empty').className = filtered.length ? 'empty is-hide' : 'empty';
    $('moreBar').className = filtered.length > shown ? 'bar' : 'bar is-hide';
  }

  function appendRows() {
    var list = $('list');
    var end = Math.min(shown + PAGE, filtered.length);
    for (var i = shown; i < end; i++) {
      var it = filtered[i];
      var row = el('button', 'row');
      row.type = 'button';
      row.setAttribute('data-name', it.name);

      var left = el('div', 'row-l');
      left.appendChild(el('div', 'row-n', it.name));
      left.appendChild(el('div', 'row-d', it.desc));
      row.appendChild(left);

      var right = el('div', 'row-r');
      right.appendChild(el('div', 'row-s', fmtStars(it.stars)));
      right.appendChild(el('div', 'row-g', it.cat));
      row.appendChild(right);

      list.appendChild(row);
    }
    shown = end;
    $('moreBar').className = filtered.length > shown ? 'bar' : 'bar is-hide';
  }

  $('list').addEventListener('click', function (ev) {
    var node = ev.target;
    while (node && node !== this && !node.getAttribute('data-name')) node = node.parentNode;
    if (!node || node === this) return;
    var name = node.getAttribute('data-name');
    for (var i = 0; i < ITEMS.length; i++) {
      if (ITEMS[i].name === name) { openDetail(ITEMS[i]); return; }
    }
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

  /* ---------------- 详情 ---------------- */

  function openDetail(it) {
    backTo = 'lib';
    var box = $('detailBody');
    clear(box);

    box.appendChild(el('div', 'd-name', it.name));
    box.appendChild(el('div', 'd-desc', it.desc));
    box.appendChild(el('div', 'd-meta',
      it.cat + ' · ' + it.lang + ' · ' + fmtStars(it.stars) + ' 星标'));

    var dims = dimsOf(it);
    var res = levelOf(0, dims);

    var v = el('div', 'verdict');
    v.appendChild(el('div', 'verdict-lv lv' + res.level.lv, res.level.t));
    v.appendChild(el('div', 'verdict-tx', res.level.tx));
    box.appendChild(v);

    var list = el('div', 'dims');
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
    if (backTo === 'lib') { tabOn('lib'); show('lib'); }
    else { tabOn('check'); show('check'); }
  });

  /* ---------------- 顶部切换 ---------------- */

  $('tab-check').addEventListener('click', function () {
    tabOn('check');
    show('check');
  });

  $('tab-lib').addEventListener('click', function () {
    tabOn('lib');
    if (!filtered.length) applyFilter();
    show('lib');
  });

  /* ---------------- 启动 ---------------- */

  renderQuestions();
  renderCats();
  applyFilter();
  show('check');
  tabOn('check');
})();
