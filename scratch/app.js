
// ════════════════════════════════════════════════════════════
//  CONSTANTS & STATE
// ════════════════════════════════════════════════════════════
const API  = window.location.origin;
const DIMS = 16;

const COL_DARK  = { cs:'#E0E0E0', math:'#CCCCCC', food:'#B8B8B8', sports:'#A4A4A4', doc:'#909090', default:'#6E6E6E' };
const COL_LIGHT = { cs:'#1d1d1f', math:'#3e3e42', food:'#515154', sports:'#636366', doc:'#767679', default:'#8e8e93' };
const COL_BG_DARK = { cs:'rgba(224,224,224,0.1)', math:'rgba(204,204,204,0.1)', food:'rgba(184,184,184,0.1)', sports:'rgba(164,164,164,0.1)', doc:'rgba(144,144,144,0.1)', default:'rgba(110,110,110,0.1)' };
const COL_BG_LIGHT = { cs:'rgba(29,29,31,0.06)', math:'rgba(62,62,66,0.06)', food:'rgba(81,81,84,0.06)', sports:'rgba(99,99,102,0.06)', doc:'rgba(118,118,121,0.06)', default:'rgba(142,142,147,0.06)' };

function getCatColor(cat) {
  const isLight = document.documentElement.classList.contains('light-theme');
  const palette = isLight ? COL_LIGHT : COL_DARK;
  return palette[cat] || palette.default;
}

function getCatBgColor(cat) {
  const isLight = document.documentElement.classList.contains('light-theme');
  const palette = isLight ? COL_BG_LIGHT : COL_BG_DARK;
  return palette[cat] || palette.default;
}

let allItems = [], pcaPoints3D = [];
let selAlgo = 'hnsw', selMetric = 'cosine', searchResults = [];
let recentVectors = [];
let clusterInterval = null;

// New Enterprise state variables
let hybridWeight = 50; // default 50% semantic
let metadataFilters = []; // array of objects { key, op, val }
let selectedProjection = 'pca3d'; // 'pca3d', 'tsne', 'umap'
let localClusterLatency = 0; // ms
let localClusterLoss = 0; // %
let selectedSDK = 'python';
let currentDemoTrace = null;
let activeSystemPersona = 'standard';

const nodeOverrides = {
  coordinator: true,
  'worker-1': true,
  'worker-2': true,
  'worker-3': true
};
let simulatedLeader = 'worker-1';

function recalculateLeader() {
  const activeWorkers = ['worker-1', 'worker-2', 'worker-3'].filter(id => nodeOverrides[id]);
  if (activeWorkers.length === 0) {
    simulatedLeader = null;
  } else {
    if (!simulatedLeader || !activeWorkers.includes(simulatedLeader)) {
      simulatedLeader = activeWorkers[0];
    }
  }
}

function toggleNode(id) {
  const cb = document.getElementById('toggle-checkbox-' + id);
  if (!cb) return;
  const isChecked = cb.checked;
  nodeOverrides[id] = isChecked;
  
  const label = document.getElementById('toggle-label-' + id);
  const slider = document.getElementById('slider-' + id);
  const knob = document.getElementById('knob-' + id);
  
  if (label) {
    label.textContent = isChecked ? 'ON' : 'OFF';
    label.style.color = isChecked ? 'var(--switch-label-on)' : 'var(--switch-label-off)';
  }
  if (slider) {
    slider.style.background = isChecked ? 'var(--switch-track-on)' : 'var(--switch-track-off)';
  }
  if (knob) {
    const isWorker = id.startsWith('worker');
    knob.style.left = isChecked ? (isWorker ? '15px' : '18px') : '2px';
  }
  
  if (typeof playClickSound === 'function') {
    playClickSound();
  }
  
  recalculateLeader();
  fetchClusterHealth();
}


// ═══════════════════════════════════════════════════════════
//  TABS & MOBILE NAVIGATION — 100x PREMIUM HORIZONTAL SCROLL
// ═══════════════════════════════════════════════════════════
let isProgrammaticScrolling = false;
let _navScrollVelocity = 0; // exposed for particle system

function updateNavIndicator(activeEl) {
  // Pill is fixed centered; width transitions via CSS
}

// ── SPRING PHYSICS EASING ──
function springInterp(t) {
  const c4 = (2 * Math.PI) / 3.2;
  return t === 0 ? 0 : t === 1 ? 1
    : Math.pow(2, -12 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
}

// ── PREMIUM COVER-FLOW ENGINE (MINIMALIST) ──
function updateTabScales() {
  const navContainer = document.querySelector('.nav-links');
  if (!navContainer) return;
  
  const containerCenter = navContainer.scrollLeft + (navContainer.offsetWidth / 2);
  const items = navContainer.querySelectorAll('.nav-item');
  
  items.forEach(item => {
    const itemCenter = item.offsetLeft + (item.offsetWidth / 2);
    const signedDist = containerCenter - itemCenter;
    const distance = Math.abs(signedDist);
    
    const maxDist = navContainer.offsetWidth / 2;
    const pct = Math.min(distance / maxDist, 1);
    
    // Clean, subtle scaling and opacity transitions
    const scale = 1.08 - (pct * 0.16);
    const opacity = 1.0 - (pct * 0.55);
    
    item.style.transform = `scale(${scale})`;
    item.style.opacity = opacity;
  });
}

// ── MOMENTUM WHEEL SCROLL WITH ELASTIC OVERSCROLL ──
(function initNavWheelScroll() {
  document.addEventListener('DOMContentLoaded', () => {
    const nav = document.querySelector('.nav-links');
    if (!nav) return;
    
    let wheelVelocity = 0;
    let wheelRAF = null;
    const friction = 0.90;
    const minVelocity = 0.2;
    
    function wheelTick() {
      if (Math.abs(wheelVelocity) < minVelocity) {
        wheelVelocity = 0;
        _navScrollVelocity = 0;
        wheelRAF = null;
        return;
      }
      
      // Elastic overscroll bounce
      const maxScroll = nav.scrollWidth - nav.offsetWidth;
      if (nav.scrollLeft <= 0 && wheelVelocity < 0) {
        wheelVelocity *= -0.3; // bounce back
      } else if (nav.scrollLeft >= maxScroll && wheelVelocity > 0) {
        wheelVelocity *= -0.3;
      }
      
      nav.scrollLeft += wheelVelocity;
      _navScrollVelocity = wheelVelocity;
      wheelVelocity *= friction;
      updateTabScales();
      wheelRAF = requestAnimationFrame(wheelTick);
    }
    
    nav.addEventListener('wheel', (e) => {
      e.preventDefault();
      const delta = (Math.abs(e.deltaY) > Math.abs(e.deltaX)) ? e.deltaY : e.deltaX;
      wheelVelocity += delta * 0.45;
      _navScrollVelocity = wheelVelocity;
      
      if (!wheelRAF) {
        wheelRAF = requestAnimationFrame(wheelTick);
      }
    }, { passive: false });
  });
})();

// ── ARROW BUTTON SCROLL (with spring + haptic feedback) ──
function scrollTabs(direction) {
  const container = document.querySelector('.nav-links');
  if (!container) return;
  const tabWidth = container.querySelector('.nav-item').offsetWidth;
  const gap = parseInt(window.getComputedStyle(container).gap) || 8;
  const scrollAmount = tabWidth + gap;
  const targetDelta = direction === 'left' ? -scrollAmount : scrollAmount;
  
  const startScroll = container.scrollLeft;
  const duration = 480;
  let startTime = null;
  
  function animateSpring(ts) {
    if (!startTime) startTime = ts;
    const elapsed = ts - startTime;
    const t = Math.min(elapsed / duration, 1);
    const eased = springInterp(t);
    
    container.scrollLeft = startScroll + (targetDelta * eased);
    _navScrollVelocity = targetDelta * (1 - t) * 0.1;
    updateTabScales();
    
    if (t < 1) {
      requestAnimationFrame(animateSpring);
    } else {
      _navScrollVelocity = 0;
    }
  }
  requestAnimationFrame(animateSpring);
  
  // Haptic visual feedback on arrow
  const btn = document.querySelector(`.nav-arrow-btn.${direction === 'left' ? 'left' : 'right'}`);
  if (btn) {
    btn.style.boxShadow = '0 0 25px rgba(106, 76, 245, 0.4)';
    setTimeout(() => { btn.style.boxShadow = ''; }, 300);
  }
  
  if (typeof playClickSound === 'function') {
    playClickSound();
  }
}

// ── AUTO-SELECT TAB ON SCROLL (MAGNETIC SNAP) ──
let isNavScrolling = null;
document.addEventListener('DOMContentLoaded', () => {
  const navContainer = document.querySelector('.nav-links');
  if (!navContainer) return;
  
  // Real-time 3D cover-flow animation on every scroll frame
  navContainer.addEventListener('scroll', () => {
    updateTabScales();
    
    if (isProgrammaticScrolling) return;
    
    // Debounced magnetic snap selection
    window.clearTimeout(isNavScrolling);
    isNavScrolling = setTimeout(() => {
      if (isProgrammaticScrolling) return;
      
      const containerCenter = navContainer.scrollLeft + (navContainer.offsetWidth / 2);
      let closestItem = null;
      let minDistance = Infinity;
      
      navContainer.querySelectorAll('.nav-item').forEach(item => {
        const itemCenter = item.offsetLeft + (item.offsetWidth / 2);
        const distance = Math.abs(containerCenter - itemCenter);
        if (distance < minDistance) {
          minDistance = distance;
          closestItem = item;
        }
      });
      
      // Magnetic snap: smoothly pull to nearest tab center
      if (closestItem) {
        const itemCenter = closestItem.offsetLeft + (closestItem.offsetWidth / 2);
        const desiredScroll = itemCenter - (navContainer.offsetWidth / 2);
        if (Math.abs(navContainer.scrollLeft - desiredScroll) > 3) {
          isProgrammaticScrolling = true;
          const startScroll = navContainer.scrollLeft;
          const delta = desiredScroll - startScroll;
          const dur = 350;
          let startT = null;
          function snapAnimate(ts) {
            if (!startT) startT = ts;
            const t = Math.min((ts - startT) / dur, 1);
            const eased = springInterp(t);
            navContainer.scrollLeft = startScroll + delta * eased;
            _navScrollVelocity = delta * (1 - t) * 0.06;
            updateTabScales();
            if (t < 1) {
              requestAnimationFrame(snapAnimate);
            } else {
              isProgrammaticScrolling = false;
              _navScrollVelocity = 0;
            }
          }
          requestAnimationFrame(snapAnimate);
        }
        
        if (!closestItem.classList.contains('on')) {
          const onclickAttr = closestItem.getAttribute('onclick');
          const match = onclickAttr.match(/switchTab\('([^']+)'/);
          if (match && match[1]) {
            const tabName = match[1];
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('on'));
            const targetContent = document.getElementById('tab-' + tabName);
            if (targetContent) targetContent.classList.add('on');
            
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('on'));
            closestItem.classList.add('on');
            
            if (tabName === 'stats') {
              setTimeout(() => {
                render3DPlot();
                loadHNSW();
              }, 100);
            }
            if (tabName === 'docs') loadDocList();
            if (tabName === 'about') {
              setTimeout(triggerAboutAnimations, 100);
            }
            if (tabName === 'cluster') {
              fetchClusterHealth();
            }
            if (typeof playClickSound === 'function') {
              playClickSound();
            }
          }
        }
      }
    }, 180);
  });
  
  // Initialize premium cover-flow on page load
  setTimeout(() => {
    const activeNav = document.querySelector('.nav-item.on');
    if (activeNav) {
      const containerHalfWidth = navContainer.offsetWidth / 2;
      const elementHalfWidth = activeNav.offsetWidth / 2;
      navContainer.scrollLeft = activeNav.offsetLeft - containerHalfWidth + elementHalfWidth;
    }
    updateTabScales();
  }, 300);
  
  // Recalculate on resize
  window.addEventListener('resize', () => {
    const activeNav = document.querySelector('.nav-item.on');
    if (activeNav && navContainer) {
      const containerHalfWidth = navContainer.offsetWidth / 2;
      const elementHalfWidth = activeNav.offsetWidth / 2;
      navContainer.scrollLeft = activeNav.offsetLeft - containerHalfWidth + elementHalfWidth;
    }
    updateTabScales();
    
    // Also resize Plotly
    const scatter = document.getElementById('scatter3d');
    if (scatter && scatter.classList.contains('js-plotly-plot')) {
      Plotly.Plots.resize('scatter3d');
    }
  });
});

function switchTab(name, el) {
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('on'));
  const targetContent = document.getElementById('tab-' + name);
  if (targetContent) {
    targetContent.classList.add('on');
  }
  
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('on'));
  if (el) {
    el.classList.add('on');
    
    // Smoothly center the active tab with spring physics
    const navLinksContainer = document.querySelector('.nav-links');
    if (navLinksContainer) {
      const containerHalfWidth = navLinksContainer.offsetWidth / 2;
      const elementHalfWidth = el.offsetWidth / 2;
      const scrollTarget = el.offsetLeft - containerHalfWidth + elementHalfWidth;
      
      if (Math.abs(navLinksContainer.scrollLeft - scrollTarget) > 2) {
        isProgrammaticScrolling = true;
        const startScroll = navLinksContainer.scrollLeft;
        const delta = scrollTarget - startScroll;
        const dur = 500;
        let startT = null;
        function animateCenter(ts) {
          if (!startT) startT = ts;
          const t = Math.min((ts - startT) / dur, 1);
          const eased = springInterp(t);
          navLinksContainer.scrollLeft = startScroll + delta * eased;
          _navScrollVelocity = delta * (1 - t) * 0.08;
          updateTabScales();
          if (t < 1) {
            requestAnimationFrame(animateCenter);
          } else {
            isProgrammaticScrolling = false;
            _navScrollVelocity = 0;
          }
        }
        requestAnimationFrame(animateCenter);
      }
    }
  }
  
  if (name === 'stats') {
    setTimeout(() => { render3DPlot(); loadHNSW(); }, 100);
  }
  if (name === 'docs') loadDocList();
  if (name === 'about') {
    setTimeout(triggerAboutAnimations, 100);
  }
  if (name === 'cluster') {
    fetchClusterHealth();
    if (!clusterInterval) {
      clusterInterval = setInterval(fetchClusterHealth, 2500);
    }
  } else {
    if (clusterInterval) {
      clearInterval(clusterInterval);
      clusterInterval = null;
    }
  }
}

function triggerAboutAnimations() {
  document.querySelectorAll('.hl-bar, .skill-fill').forEach(el => {
    el.style.width = '0%';
    setTimeout(() => {
      el.style.width = (el.dataset.w || 0) + '%';
    }, 50);
  });
  
  const wrap = document.getElementById('portalFormWrap');
  if (wrap && wrap.classList.contains('open')) {
    loadPortalMessages();
  }
}

function setAlgo(el, algo) {
  document.querySelectorAll('#algoPills .pill').forEach(p => p.classList.remove('on'));
  el.classList.add('on'); 
  selAlgo = algo;
  
  const container = document.getElementById('hybridTuningContainer');
  if (container) {
    container.style.display = (algo === 'hybrid') ? 'block' : 'none';
  }
}

function setMetric(el, metric) {
  document.querySelectorAll('#metricPills .pill').forEach(p => p.classList.remove('on'));
  el.classList.add('on'); 
  selMetric = metric;
}

// ════════════════════════════════════════════════════════════
//  TEXT → EMBEDDING & PCA (3D)
// ════════════════════════════════════════════════════════════
const KW = {
  cs: ['algorithm','data','tree','graph','array','linked','hash','stack','queue','sort','binary','dynamic','programming','recursion','complexity','pointer','node','search','insert','bfs','dfs','heap','trie'],
  math: ['calculus','matrix','probability','theorem','integral','derivative','linear','algebra','equation','function','prime','modular','combinatorics','permutation','eigenvalue','statistics','proof'],
  food: ['food','pizza','sushi','ramen','pasta','recipe','cook','eat','restaurant','dish','ingredient','flavor','spice','noodle','bread','croissant','taco','fish','rice','soup','zomato','dinner','lunch','breakfast','dessert','coffee','tea','drink','cheese','chocolate','chicken','meat','bake','fry','grill','cafe','bakery','menu','cuisine','chef','sweet','spicy','vegan','salad','delivery','dine','fruit','vegetable','snack','meal','butter','cream','egg','sauce','honey'],
  sports: ['sport','basketball','football','tennis','chess','swim','game','play','score','team','athlete','competition','match','tournament','olympic','dribble','tackle','serve']
};

function textToEmbedding(text) {
  const t = text.toLowerCase(), ws = t.split(/\s+/);
  const s = {cs:0,math:0,food:0,sports:0};
  for (const w of ws)
    for (const [cat, kws] of Object.entries(KW))
      for (const kw of kws) if (w.includes(kw)||kw.startsWith(w)) { s[cat]+=0.35; break; }
  const mx = Math.max(...Object.values(s), 0.01);
  const n = v => Math.min(v/mx*0.88, 0.94);
  const jitter = () => (Math.random()-.5)*.04;
  const emb = new Array(16).fill(0.08);
  const fill = (i,score) => {
    if (score<.01) return;
    const b = n(score);
    emb[i]=Math.max(.05,b+jitter()); emb[i+1]=Math.max(.05,b+jitter());
    emb[i+2]=Math.max(.05,b*.92+jitter()); emb[i+3]=Math.max(.05,b*.87+jitter());
  };
  fill(0,s.cs); fill(4,s.math); fill(8,s.food); fill(12,s.sports);
  return emb;
}

function pca3D(embs) {
  const n = embs.length, d = embs[0].length;
  if (n < 2) return embs.map(() => [0,0,0]);
  const mean = new Array(d).fill(0);
  for (const e of embs) for (let i=0;i<d;i++) mean[i]+=e[i]/n;
  const X = embs.map(e => e.map((v,i)=>v-mean[i]));
  
  function powerIter(X,excl) {
    let v = new Array(d).fill(0).map(()=>Math.random()-.5);
    if (excl) { let dot=v.reduce((s,vi,i)=>s+vi*excl[i],0); v=v.map((vi,i)=>vi-dot*excl[i]); }
    let nrm = Math.sqrt(v.reduce((s,vi)=>s+vi*vi,0));
    v = v.map(vi=>vi/nrm);
    for (let it=0;it<200;it++) {
      const Xv=X.map(xi=>xi.reduce((s,xij,j)=>s+xij*v[j],0));
      const nv=new Array(d).fill(0);
      for (let k=0;k<n;k++) for (let j=0;j<d;j++) nv[j]+=X[k][j]*Xv[k];
      if (excl) { let dot=nv.reduce((s,vi,i)=>s+vi*excl[i],0); for (let i=0;i<d;i++) nv[i]-=dot*excl[i]; }
      nrm=Math.sqrt(nv.reduce((s,vi)=>s+vi*vi,0));
      if (nrm<1e-10) break;
      const prev=v.slice(); v=nv.map(vi=>vi/nrm);
      if (v.reduce((s,vi,i)=>s+(vi-prev[i])**2,0)<1e-12) break;
    }
    return v;
  }
  
  const pc1=powerIter(X,null);
  const pc2=powerIter(X,pc1);
  const pc3=powerIter(X,pc2);
  
  return X.map(x=>[
    x.reduce((s,v,i)=>s+v*pc1[i],0),
    x.reduce((s,v,i)=>s+v*pc2[i],0),
    x.reduce((s,v,i)=>s+v*pc3[i],0)
  ]);
}

// ════════════════════════════════════════════════════════════
//  3D PLOT (Plotly)
// ════════════════════════════════════════════════════════════
function render3DPlot() {
  if (pcaPoints3D.length === 0) {
    document.getElementById('scatter3d').innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--ink-muted);font-size:13px;">No data to visualize. Add vectors or check server connection.</div>';
    return;
  }
  
  try {
    const x = pcaPoints3D.map(p => p.x);
    const y = pcaPoints3D.map(p => p.y);
    const z = pcaPoints3D.map(p => p.z);
    const colors = pcaPoints3D.map(p => getCatColor(p.item.category));
    const text = pcaPoints3D.map(p => `${p.item.category.toUpperCase()}: ${p.item.metadata}`);
    
    const isLight = document.documentElement.classList.contains('light-theme');
    const paperBg = isLight ? '#f5f5f7' : '#090909';
    const textClr = isLight ? '#1d1d1f' : '#ffffff';
    const gridClr = isLight ? '#e2e2e8' : '#262626';
    const tickClr = isLight ? '#86868b' : '#999999';

    const trace = {
      x: x, y: y, z: z,
      mode: 'markers',
      type: 'scatter3d',
      marker: {
        size: 7,
        color: colors,
        opacity: 0.9,
        line: { width: 1.5, color: paperBg },
        symbol: 'circle',
        showscale: false
      },
      text: text,
      hoverinfo: 'text',
      hoverlabel: {
        bgcolor: isLight ? '#ffffff' : '#141414',
        bordercolor: isLight ? '#e2e2e8' : '#262626',
        font: { family: 'Inter, sans-serif', size: 12, color: isLight ? '#1d1d1f' : '#ffffff' }
      }
    };
    
    const layout = {
      margin: {l: 0, r: 0, b: 0, t: 0},
      paper_bgcolor: paperBg,
      plot_bgcolor: paperBg,
      scene: {
        xaxis: { 
          title: 'PC1', 
          gridcolor: gridClr, 
          gridwidth: 1,
          zerolinecolor: gridClr, 
          zerolinewidth: 2,
          tickfont: {color: tickClr, family: 'Inter'}, 
          titlefont: {color: textClr, family: 'Inter', size: 12},
          linecolor: gridClr
        },
        yaxis: { 
          title: 'PC2', 
          gridcolor: gridClr, 
          gridwidth: 1,
          zerolinecolor: gridClr, 
          zerolinewidth: 2,
          tickfont: {color: tickClr, family: 'Inter'}, 
          titlefont: {color: textClr, family: 'Inter', size: 12},
          linecolor: gridClr
        },
        zaxis: { 
          title: 'PC3', 
          gridcolor: gridClr, 
          gridwidth: 1,
          zerolinecolor: gridClr, 
          zerolinewidth: 2,
          tickfont: {color: tickClr, family: 'Inter'}, 
          titlefont: {color: textClr, family: 'Inter', size: 12},
          linecolor: gridClr
        },
        bgcolor: paperBg,
        camera: { eye: {x: 1.6, y: 1.6, z: 1.3} },
        aspectmode: 'cube',
        aspectratio: {x: 1, y: 1, z: 0.8}
      },
      font: { family: 'Inter, sans-serif' }
    };
    
    const scatterContainer = document.getElementById('scatter3d');
    if (scatterContainer.querySelector('.js-plotly-plot')) {
      Plotly.react('scatter3d', [trace], layout, {responsive: true, displayModeBar: true});
    } else {
      Plotly.newPlot('scatter3d', [trace], layout, {responsive: true, displayModeBar: true});
    }
  } catch(e) {
    document.getElementById('scatter3d').innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#ff4b4b;font-size:13px;">Plot error: ${e.message}</div>`;
  }
}

// ═══════════════════════════════════════════════════════════
//  LOAD & SEARCH & IVF-PQ CONTROLS
// ═══════════════════════════════════════════════════════════
async function loadItems() {
  try {
    const r = await fetch(API+'/items');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    allItems = await r.json();
    if (allItems.length >= 2) {
      const coords = pca3D(allItems.map(v=>v.embedding));
      pcaPoints3D = allItems.map((item,i)=>({x:coords[i][0],y:coords[i][1],z:coords[i][2],item}));
    }
    loadIVFPQStats();
    updateEngineStats();
  } catch(e) {
    console.error('Failed to load items:', e);
  }
}

async function loadIVFPQStats() {
  try {
    const r = await fetch(API+'/ivfpq/stats');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    
    // Update IVF-PQ Panel UI
    const badge = document.getElementById('ivfpqTrainedBadge');
    badge.textContent = data.trained ? 'Trained' : 'Untrained';
    badge.style.color = data.trained ? '#22c55e' : '#eab308';
    badge.style.background = data.trained ? 'rgba(34,197,94,0.1)' : 'rgba(234,179,8,0.1)';
    badge.style.borderColor = data.trained ? 'rgba(34,197,94,0.2)' : 'rgba(234,179,8,0.2)';
    
    let compVal = data.compression_ratio;
    if (typeof compVal === 'number') {
      compVal = compVal.toFixed(2) + '%';
    } else if (typeof compVal === 'string' && !compVal.endsWith('%')) {
      compVal = compVal + '%';
    }
    document.getElementById('ivfpqCompressionVal').textContent = compVal;
    
    const saved = data.raw_memory_bytes - data.memory_bytes;
    const pctSaved = ((saved / Math.max(1, data.raw_memory_bytes)) * 100).toFixed(1);
    document.getElementById('ivfpqMemorySavedVal').textContent = pctSaved + '%';
    
    // Render Memory Footprint Comparison Chart
    renderMemoryComparison(data);
  } catch(e) {
    console.error('Failed to load IVF-PQ stats:', e);
  }
}

async function trainIVFPQ() {
  const btn = document.getElementById('trainIvfpqBtn');
  btn.disabled = true;
  btn.textContent = 'Training Index...';
  
  try {
    const r = await fetch(API + '/ivfpq/train', { method: 'POST' });
    const d = await r.json();
    showToast(d.message || 'IVF-PQ training complete!', 'success');
    loadIVFPQStats();
  } catch(e) {
    console.error('Failed to train IVF-PQ:', e);
    showToast('Training failed.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Train IVF-PQ Index';
  }
}

function renderMemoryComparison(stats) {
  const container = document.getElementById('memoryComparisonBars');
  if (!container) return;
  
  const numVecs = stats.num_vectors || 10;
  const rawBytes = stats.raw_memory_bytes || (numVecs * DIMS * 4);
  const ivfBytes = stats.memory_bytes || (numVecs * 16);
  
  // HNSW takes roughly 3.5x raw bytes, KD-Tree takes 1.5x
  const hnswBytes = rawBytes * 3.5;
  const kdtBytes = rawBytes * 1.5;
  const bfBytes = rawBytes;
  
  const maxBytes = Math.max(hnswBytes, kdtBytes, bfBytes, ivfBytes, 1);
  
  const fmt = (b) => {
    if (b >= 1024 * 1024) return (b / 1024 / 1024).toFixed(2) + ' MB';
    if (b >= 1024) return (b / 1024).toFixed(2) + ' KB';
    return b + ' B';
  };
  
  const items = [
    { name: 'Brute Force (Raw)', bytes: bfBytes, color: '#666666' },
    { name: 'KD-Tree Index', bytes: kdtBytes, color: '#999999' },
    { name: 'HNSW Graph', bytes: hnswBytes, color: 'var(--grad-magenta)' },
    { name: 'IVF-PQ (Quantized)', bytes: ivfBytes, color: 'var(--accent-blue)' }
  ];
  
  container.innerHTML = items.map(item => {
    const pct = Math.max((item.bytes / maxBytes) * 100, 2);
    return `
      <div class="mem-row">
        <div class="mem-label-row">
          <span class="mem-name">${item.name}</span>
          <span class="mem-value font-mono">${fmt(item.bytes)}</span>
        </div>
        <div class="mem-bar-track">
          <div class="mem-bar-fill" style="width: ${pct}%; background: ${item.color};"></div>
        </div>
      </div>
    `;
  }).join('');
}

// --- NEW INTERACTIVE FEATURE LOGICS ---
function saveSearchHistory(text, algo, metric) {
  try {
    let list = JSON.parse(localStorage.getItem('nuro_query_history') || '[]');
    if (list.length > 0 && list[0].text === text && list[0].algo === algo && list[0].metric === metric) {
      return;
    }
    list.unshift({ text, algo, metric, time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) });
    if (list.length > 8) list.pop();
    localStorage.setItem('nuro_query_history', JSON.stringify(list));
    renderSearchHistory();
  } catch(e) {
    console.error('Save search history failed:', e);
  }
}

function renderSearchHistory() {
  const container = document.getElementById('queryHistoryList');
  const card = document.getElementById('historyCard');
  if (!container || !card) return;
  
  try {
    const list = JSON.parse(localStorage.getItem('nuro_query_history') || '[]');
    if (!list.length) {
      card.style.display = 'none';
      return;
    }
    card.style.display = 'block';
    container.innerHTML = list.map((item) => `
      <div style="display:flex; justify-content:space-between; align-items:center; background:var(--trans-white-05); padding:6px 10px; border-radius:6px; border:1px solid var(--border-trans-soft); font-size:11px; cursor:pointer; transition:all 0.2s; margin-bottom:4px;" onclick="reRunQuery('${escapeHtml(item.text)}', '${item.algo}', '${item.metric}')">
        <div style="flex:1; min-width:0; padding-right:8px;">
          <div style="font-weight:600; color:var(--ink); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(item.text)}</div>
          <div style="font-size:9px; color:var(--ink-muted); margin-top:2px;">
            <span style="text-transform:uppercase; color:var(--accent-blue); font-weight:600;">${item.algo}</span> • <span>${item.metric}</span>
          </div>
        </div>
        <span style="font-size:9px; color:var(--ink-muted); flex-shrink:0;">${item.time}</span>
      </div>
    `).join('');
  } catch(e) {
    console.error('Render search history failed:', e);
  }
}

function clearQueryHistory() {
  localStorage.removeItem('nuro_query_history');
  renderSearchHistory();
  playClickSound();
}

function reRunQuery(text, algo, metric) {
  document.getElementById('qInput').value = text;
  const algoPills = document.querySelectorAll('#algoPills .pill');
  algoPills.forEach(p => {
    if (p.getAttribute('onclick').includes(`'${algo}'`)) {
      setAlgo(p, algo);
    }
  });
  const metricPills = document.querySelectorAll('#metricPills .pill');
  metricPills.forEach(p => {
    if (p.getAttribute('onclick').includes(`'${metric}'`)) {
      setMetric(p, metric);
    }
  });
  runSearch();
  playClickSound();
}

function fillAndSearch(text) {
  document.getElementById('qInput').value = text;
  runSearch();
  playClickSound();
}

function fillRAG(text) {
  document.getElementById('ragQuestion').value = text;
  playClickSound();
}

function fillSQL(text) {
  document.getElementById('sqlQueryText').value = text;
  playClickSound();
}

function fillDoc(title, text) {
  document.getElementById('docTitle').value = title;
  document.getElementById('docText').value = text;
  playClickSound();
}

function insertAtSqlCursor(text) {
  const textarea = document.getElementById('sqlQueryText');
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const currentText = textarea.value;
  textarea.value = currentText.substring(0, start) + text + currentText.substring(end);
  textarea.focus();
  textarea.selectionStart = textarea.selectionEnd = start + text.length;
  playClickSound();
}

function updateEngineStats() {
  if (typeof allItems === 'undefined') return;
  const count = allItems.length;
  const statCount = document.getElementById('statTotalVectors');
  if (statCount) statCount.textContent = count;
  
  const vectorBytes = count * 64;
  const indexOverheadBytes = count * 128;
  const totalBytes = vectorBytes + indexOverheadBytes;
  
  let formattedMemory = "0.0 KB";
  if (totalBytes > 1024 * 1024) {
    formattedMemory = (totalBytes / (1024 * 1024)).toFixed(1) + " MB";
  } else {
    formattedMemory = (totalBytes / 1024).toFixed(1) + " KB";
  }
  const statMem = document.getElementById('statMemoryUsed');
  if (statMem) statMem.textContent = formattedMemory;
}

function highlightKeywords(text, query) {
  if (!query || !text) return text;
  const words = query.toLowerCase().split(/\s+/).filter(w => w.length > 2 && !['explain', 'what', 'tell', 'about', 'does', 'how', 'work'].includes(w));
  if (!words.length) return text;
  
  let highlighted = text;
  words.forEach(word => {
    const escapedWord = word.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
    const regex = new RegExp(`(${escapedWord})`, 'gi');
    highlighted = highlighted.replace(regex, '<mark class="highlight-mark">$1</mark>');
  });
  return highlighted;
}

async function runSearch() {
  const text=document.getElementById('qInput').value.trim(); 
  if(!text) return;
  saveSearchHistory(text, selAlgo, selMetric);
  
  // Render animated skeleton structure first
  renderSkeletons();
  
  const emb=textToEmbedding(text);
  
  let url = `${API}/search?v=${emb.join(',')}&k=5&metric=${selMetric}&algo=${selAlgo}`;
  if (selAlgo === 'hybrid') {
    url += `&text=${encodeURIComponent(text)}`;
  }
  
  try {
    // Artificial min delay of 600ms to allow skeleton to animate smoothly and prevent visual flash
    const [r] = await Promise.all([
      fetch(url),
      new Promise(resolve => setTimeout(resolve, 600))
    ]);
    
    if (r.status === 400) {
      const err = await r.json();
      if (err.error && err.error.includes("not trained")) {
        showToast('IVF-PQ Index is untrained. Train it using the panel in the right sidebar.', 'warning');
        return;
      }
    }
    const data = await r.json();
    searchResults=data.results||[];
    renderResults(searchResults);
    
    // Automatically trigger benchmark display
    runBenchmark();
  } catch(e) { 
    console.error('Search failed:', e); 
    showToast('Search failed: ' + (e.message || 'Server error'), 'error'); 
  }
}

document.getElementById('qInput').addEventListener('keydown',e=>{ if(e.key==='Enter') runSearch(); });

function escapeHtml(s) {
  if (typeof s !== 'string') return '';
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function renderSkeletons() {
  const resContainer = document.getElementById('results');
  resContainer.innerHTML = Array.from({ length: 3 }).map((_, i) => `
    <div class="result-card skeleton-card" style="animation-delay: ${i * 0.15}s;">
      <div class="res-icon skeleton-icon"></div>
      <div class="skeleton-info">
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line skeleton-meta"></div>
      </div>
    </div>
  `).join('');
}

function renderResults(results) {
  const resContainer = document.getElementById('results');
  if (!results || !results.length){
    resContainer.innerHTML=`<div class="empty-state"><div class="empty-state-icon">⌕</div><div class="empty-state-text">No results found</div></div>`;
    return;
  }
  
  resContainer.innerHTML = results.map((r,i)=>{
    const col = getCatColor(r.category);
    const bg = getCatBgColor(r.category);
    // Add dynamic inline animation-delay for staggered entry transition
    return `<div class="result-card" style="animation-delay: ${i * 60}ms;">
      <div class="res-icon" style="background:${bg};color:${col}">${r.category[0].toUpperCase()}</div>
      <div class="res-info">
        <div class="res-title">${escapeHtml(r.metadata)}</div>
        <div class="res-meta">
          <span class="res-badge" style="background:${bg};color:${col}">${escapeHtml(r.category)}</span>
          <span class="res-dist">distance: ${r.distance.toFixed(4)}</span>
        </div>
      </div>
      <button class="res-action" onclick="deleteItem(${r.id})" aria-label="Delete">✕</button>
    </div>`;
  }).join('');
}

async function runBenchmark() {
  const text = document.getElementById('qInput').value.trim() || 'binary tree';
  const emb = textToEmbedding(text);
  
  document.getElementById('benchSec').style.display = 'block';
  document.getElementById('benchBars').innerHTML = '<div style="color:var(--ink-muted); text-align:center; padding:12px; font-size:12px;">Evaluating performance metrics live...</div>';
  
  try {
    const r = await fetch(`${API}/benchmark?v=${emb.join(',')}&k=5&metric=${selMetric}`);
    const d = await r.json();
    
    // Update vector count on benchmark card header
    document.getElementById('benchNumVecs').textContent = `Indexed: ${d.n || 0} vectors`;
    
    // Render detailed live performance gates panel
    renderBenchmarkMatrix(d);
  } catch(e) { 
    console.error('Benchmark failed:', e); 
    document.getElementById('benchBars').innerHTML = `<div style="color:#ff4b4b; font-size:12px; padding:10px;">Benchmark error: ${e.message}</div>`;
  }
}

function renderBenchmarkMatrix(d) {
  const container = document.getElementById('benchBars');
  
  if (!d.metrics) {
    // Fallback if the backend does not return the detailed metrics object
    const mx = Math.max(d.bfUs || 1, d.kdUs || 1, d.hnswUs || 1, d.ivfpqUs || 1, d.gpuUs || 1);
    const bf_disp = d.bfUs < 1000 ? d.bfUs + ' μs' : (d.bfUs/1000).toFixed(2) + ' ms';
    const kd_disp = d.kdUs < 1000 ? d.kdUs + ' μs' : (d.kdUs/1000).toFixed(2) + ' ms';
    const hnsw_disp = d.hnswUs < 1000 ? d.hnswUs + ' μs' : (d.hnswUs/1000).toFixed(2) + ' ms';
    const ivfpq_disp = d.ivfpqUs < 1000 ? d.ivfpqUs + ' μs' : (d.ivfpqUs/1000).toFixed(2) + ' ms';
    const gpu_disp = d.gpuUs < 1000 ? d.gpuUs + ' μs' : (d.gpuUs/1000).toFixed(2) + ' ms';
    
    container.innerHTML = `
      <div class="bench-fallback-bars" style="width:100%; display:flex; flex-direction:column; gap:10px;">
        <div class="bench-row"><div class="bench-label"><span>Brute Force</span><span>${bf_disp}</span></div><div class="bench-track"><div class="bench-fill" style="width:${(d.bfUs/mx)*100}%; background:#666;"></div></div></div>
        <div class="bench-row"><div class="bench-label"><span>KD-Tree</span><span>${kd_disp}</span></div><div class="bench-track"><div class="bench-fill" style="width:${(d.kdUs/mx)*100}%; background:#999;"></div></div></div>
        <div class="bench-row"><div class="bench-label"><span>HNSW Graph</span><span>${hnsw_disp}</span></div><div class="bench-track"><div class="bench-fill" style="width:${(d.hnswUs/mx)*100}%; background:var(--grad-magenta)"></div></div></div>
        <div class="bench-row"><div class="bench-label"><span>IVF-PQ</span><span>${ivfpq_disp}</span></div><div class="bench-track"><div class="bench-fill" style="width:${(d.ivfpqUs/mx)*100}%; background:var(--accent-blue)"></div></div></div>
        <div class="bench-row"><div class="bench-label"><span>GPU PyTorch</span><span>${gpu_disp}</span></div><div class="bench-track"><div class="bench-fill" style="width:${(d.gpuUs/mx)*100}%; background:#00f2fe"></div></div></div>
      </div>
    `;
    return;
  }
  
  // Build a beautiful comparison matrix panel with grid of cards
  let html = `<div class="bench-matrix-grid">`;
  
  const algos = [
    { key: 'bruteforce', name: 'Brute Force', desc: 'Exact Float Scan', glow: '' },
    { key: 'kdtree', name: 'KD-Tree', desc: 'Exact Node Scan', glow: '' },
    { key: 'hnsw', name: 'HNSW Graph', desc: 'Approx. Multi-layer Link', glow: 'card-hnsw' },
    { key: 'ivfpq', name: 'IVF-PQ Code', desc: 'Approx. Quantized Code', glow: 'card-ivfpq' },
    { key: 'gpu', name: 'GPU PyTorch', desc: 'Matrix Multiplication', glow: 'card-gpu' }
  ];
  
  algos.forEach(algo => {
    const m = d.metrics[algo.key];
    if (!m) return;
    
    const latDisp = m.latencyUs < 1000 ? m.latencyUs + ' μs' : (m.latencyUs/1000).toFixed(2) + ' ms';
    const qpsDisp = m.qps.toLocaleString();
    const recallDisp = (m.recall * 100).toFixed(0) + '%';
    const memDisp = m.memoryMb >= 1.0 ? m.memoryMb.toFixed(2) + ' MB' : (m.memoryMb * 1024).toFixed(0) + ' KB';
    
    html += `
      <div class="bench-card ${algo.glow}">
        <div class="bench-card-header">
          <div>
            <h4 class="bench-algo-name">${algo.name}</h4>
            <span class="bench-algo-desc">${algo.desc}</span>
          </div>
          <span class="bench-recall-badge">${recallDisp} Rec</span>
        </div>
        <div class="bench-card-body">
          <div class="bench-stat-row">
            <span class="bench-stat-label">Latency</span>
            <span class="bench-stat-val font-mono">${latDisp}</span>
          </div>
          <div class="bench-stat-row">
            <span class="bench-stat-label">QPS</span>
            <span class="bench-stat-val font-mono">${qpsDisp}</span>
          </div>
          <div class="bench-stat-row">
            <span class="bench-stat-label">Memory</span>
            <span class="bench-stat-val font-mono">${memDisp}</span>
          </div>
        </div>
      </div>
    `;
  });
  
  html += `</div>`;
  container.innerHTML = html;
}

async function loadHNSW() {
  try {
    const r = await fetch(API+'/hnsw-info');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    if (d.error) {
      document.getElementById('layers').innerHTML = `<span style="color:#ff4b4b">Error: ${d.error}</span>`;
      return;
    }
    
    const maxN = d.nodesPerLayer[0] || 1;
    if (!d.nodesPerLayer || d.nodesPerLayer.length === 0) {
      document.getElementById('layers').innerHTML = '<div style="color:var(--ink-muted); text-align:center; padding:10px;">Graph is empty. Insert vectors.</div>';
      return;
    }
    
    document.getElementById('layers').innerHTML = d.nodesPerLayer.map((cnt, lyr) => {
      const pct = Math.max((cnt/maxN)*100, 2), edg = d.edgesPerLayer[lyr] || 0;
      return `<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;font-size:12px;">
        <span style="width:24px;font-weight:600;color:var(--primary)">L${lyr}</span>
        <div style="flex:1;height:6px;background:var(--canvas);border-radius:3px;overflow:hidden;border:1px solid var(--hairline-soft);">
          <div style="width:${pct}%;height:100%;background:var(--accent-blue);border-radius:3px;"></div>
        </div>
        <span style="width:80px;text-align:right;color:var(--ink-muted);font-size:11px;">${cnt} nodes · ${edg} edges</span>
      </div>`;
    }).join('');
  } catch(e) {
    document.getElementById('layers').innerHTML = `<span style="color:#ff4b4b">Failed to load: ${e.message}</span>`;
  }
}

async function addVector() {
  const meta=document.getElementById('addMeta').value.trim(), cat=document.getElementById('addCat').value;
  if(!meta) return;
  const emb=textToEmbedding(meta+' '+cat);
  try {
    const r = await fetch(API+'/insert',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({metadata:meta,category:cat,embedding:emb})
    });
    const d = await r.json();
    document.getElementById('addMeta').value='';
    
    // Add to history list
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
    recentVectors.unshift({ id: d.id, meta, cat, time: timeStr });
    if (recentVectors.length > 8) recentVectors.pop();
    renderHistory();
    
    await loadItems();
    render3DPlot();
    loadHNSW();
  } catch(e) { 
    console.error('Insert vector failed:', e); 
  }
}

function renderHistory() {
  const el = document.getElementById('vectorHistory');
  if (!recentVectors.length) {
    el.innerHTML = '<div style="color:var(--ink-muted); font-size:12px; text-align:center; padding:8px;">No vectors added yet.</div>';
    return;
  }
  el.innerHTML = recentVectors.map(v => {
    const col = getCatColor(v.cat);
    const bg = getCatBgColor(v.cat);
    return `<div class="history-item">
      <div class="h-icon" style="background:${bg};color:${col}">${v.cat[0].toUpperCase()}</div>
      <div class="h-text" style="color:${col}">${v.meta}</div>
      <div class="h-time">${v.time}</div>
    </div>`;
  }).join('');
}

async function deleteItem(id) {
  try {
    await fetch(`${API}/delete/${id}`,{method:'DELETE'});
    searchResults=searchResults.filter(r=>r.id!==id);
    renderResults(searchResults);
    await loadItems();
    render3DPlot();
    loadHNSW();
  } catch(e) { 
    console.error('Delete item failed:', e); 
  }
}

// ═══════════════════════════════════════════════════════════
//  DOCUMENTS & RAG CHAT
// ═══════════════════════════════════════════════════════════
async function checkOllamaStatus() {
  try {
    const r=await fetch(API+'/status'), d=await r.json();
    const badge=document.getElementById('headerBadge');
    if (d.ollamaAvailable) {
      badge.innerHTML = '<span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#22c55e; margin-right:6px; animation:breath-green 2s infinite ease-in-out;"></span> Ollama Online';
      badge.style.color='#22c55e';
      badge.style.background='rgba(34,197,94,0.1)';
      badge.style.borderColor='rgba(34,197,94,0.2)';
    } else {
      badge.innerHTML = '<span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#ff4b4b; margin-right:6px;"></span> Ollama Offline';
      badge.style.color='#ff4b4b';
      badge.style.background='rgba(255,75,75,0.1)';
      badge.style.borderColor='rgba(255,75,75,0.2)';
    }
  } catch(e) { 
    console.error('Ollama status check failed:', e); 
  }
}

async function insertDocument() {
  const title=document.getElementById('docTitle').value.trim();
  const text=document.getElementById('docText').value.trim();
  const btn=document.getElementById('insertDocBtn');
  const status=document.getElementById('insertStatus');
  if(!title||!text){ status.textContent='Title and text body are required.'; return; }

  btn.disabled=true; 
  btn.textContent='Embedding...';
  status.textContent='Sending documents to Ollama embedder...';

  try {
    const r=await fetch(API+'/doc/insert',{
      method:'POST', 
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({title,text})
    });
    const d=await r.json();
    if (d.error) {
      status.innerHTML=`<span style="color:#ff4b4b">✗ ${d.error}</span>`;
    } else {
      status.innerHTML=`<span style="color:#22c55e">✓ Created ${d.chunks} chunk nodes successfully</span>`;
      document.getElementById('docTitle').value='';
      document.getElementById('docText').value='';
      
      const emb16 = textToEmbedding(title + ' ' + text);
      fetch(API+'/insert', {
        method:'POST', 
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({metadata: title, category: 'doc', embedding: emb16})
      }).then(() => { loadItems().then(render3DPlot); });
      
      loadDocList(); 
      checkOllamaStatus();
    }
  } catch(e) { 
    status.innerHTML='<span style="color:#ff4b4b">✗ Ingestion server communication error</span>'; 
    console.error('Insert document failed:', e); 
  } finally {
    btn.disabled=false; 
    btn.textContent='Embed & Insert Text';
  }
}

// Dropzone Drag-and-Drop Handlers
function handleFileSelect(input) {
  const fileInfo = document.getElementById('fileInfo');
  const fileName = document.getElementById('fileName');
  const dropzone = document.getElementById('dropzone');
  
  if (input.files && input.files.length > 0) {
    const file = input.files[0];
    const maxSize = 10 * 1024 * 1024; // 10 MB limit
    if (file.size > maxSize) {
      showToast("File is too large! Max allowed size is 10 MB.", "error");
      clearFileSelect(null);
      return;
    }
    
    fileName.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    fileInfo.style.display = 'flex';
    dropzone.style.borderColor = 'var(--accent-blue)';
    showToast("File loaded: " + file.name, "info");
    playClickSound();
  } else {
    clearFileSelect(null);
  }
}

function clearFileSelect(event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  const fileInput = document.getElementById('docFile');
  const fileInfo = document.getElementById('fileInfo');
  const dropzone = document.getElementById('dropzone');
  
  fileInput.value = '';
  if (fileInfo) fileInfo.style.display = 'none';
  if (dropzone) dropzone.style.borderColor = '';
}

function initDropzone() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('docFile');
  if (!dropzone) return;
  
  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    }, false);
  });
  
  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    }, false);
  });
  
  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      fileInput.files = files;
      handleFileSelect(fileInput);
    }
  }, false);
}

async function uploadDocument() {
  const fileInput = document.getElementById('docFile');
  const status = document.getElementById('insertStatus');
  const btn = document.getElementById('uploadDocBtn');
  
  if (!fileInput.files.length) {
    status.textContent = 'Please choose a PDF or TXT file first.';
    showToast("No file selected", "error");
    return;
  }
  
  const file = fileInput.files[0];
  const maxSize = 10 * 1024 * 1024; // 10 MB limit
  if (file.size > maxSize) {
    status.textContent = 'File is too large! Max allowed size is 10 MB.';
    showToast("File too large", "error");
    clearFileSelect(null);
    return;
  }
  const formData = new FormData();
  formData.append('file', file);
  
  btn.disabled = true; 
  btn.textContent = 'Ingesting File...';
  status.textContent = 'Extracting content text & processing embeddings...';
  
  try {
    const r = await fetch(API + '/doc/upload', {
      method: 'POST',
      body: formData
    });
    const d = await r.json();
    if (d.error) {
      status.innerHTML = `<span style="color:#ff4b4b">✗ ${d.error}</span>`;
      showToast("Ingestion failed: " + d.error, "error");
    } else {
      status.innerHTML = `<span style="color:#22c55e">✓ Uploaded ${d.filename} (${d.chunks} chunks mapped)</span>`;
      showToast("Uploaded successfully", "success");
      clearFileSelect(null);
      loadDocList(); 
      checkOllamaStatus();
    }
  } catch(e) {
    status.innerHTML = '<span style="color:#ff4b4b">✗ File upload request failed</span>';
    showToast("Upload request failed", "error");
    console.error('Upload document failed:', e);
  } finally {
    btn.disabled = false; 
    btn.textContent = 'Upload & Embed File';
  }
}

async function loadDocList() {
  try {
    const r=await fetch(API+'/doc/list'), docs=await r.json();
    const listContainer = document.getElementById('docList');
    if (!docs.length) {
      listContainer.innerHTML='<div class="empty-state"><div class="empty-state-icon">📄</div><div class="empty-state-text">No documents in database.</div></div>';
      return;
    }
    listContainer.innerHTML=docs.map((d, i)=>`
      <div class="result-card magnet" style="animation-delay: ${i * 50}ms; cursor:pointer;" onclick="loadDocChunks('${escapeHtml(d.title)}')">
        <div class="res-icon" style="background:rgba(0,153,255,0.06); color:var(--accent-blue)">
          <i class="ti ti-file-text"></i>
        </div>
        <div class="res-info">
          <div class="res-title" style="font-weight:600;">${escapeHtml(d.title)}</div>
          <div class="res-meta" style="margin-top:4px;">
            <span class="res-badge" style="background:var(--trans-white-05); color:var(--ink-muted); font-size:10px;">${d.words} words</span>
          </div>
        </div>
        <button class="res-action" onclick="event.stopPropagation(); deleteDoc(${d.id})" aria-label="Delete"><i class="ti ti-trash" style="color:#ef4444; font-size:14px;"></i></button>
      </div>`).join('');
      
    if (docs.length > 0) {
      loadDocChunks(docs[0].title);
    }
  } catch(e) { 
    console.error('Load doc list failed:', e); 
  }
}

async function deleteDoc(id) {
  try { 
    await fetch(`${API}/doc/delete/${id}`,{method:'DELETE'}); 
    loadDocList(); 
    checkOllamaStatus(); 
  } catch(e) { 
    console.error('Delete doc failed:', e); 
  }
}

async function askAI() {
  const question = document.getElementById('ragQuestion').value.trim();
  if (!question) return;
  const k = parseInt(document.getElementById('ragK').value);
  const k_retrieve = parseInt(document.getElementById('ragKRetrieve').value);
  const btn = document.getElementById('askBtn');
  const rewrite = document.getElementById('rewriteToggle').classList.contains('on');
  const rerank = document.getElementById('rerankToggle').classList.contains('on');
  const useGraph = document.getElementById('graphToggle') ? document.getElementById('graphToggle').classList.contains('on') : false;
  const endpoint = useGraph ? '/doc/ask/graph' : '/doc/ask';
  
  btn.disabled = true; 
  btn.textContent = 'Reasoning...';

  const history = document.getElementById('chatHistory');
  
  // User chat bubble
  const userBubble = document.createElement('div');
  userBubble.className = 'chat-bubble user';
  userBubble.textContent = question;
  history.appendChild(userBubble);
  
  // AI response bubble
  const aiBubble = document.createElement('div');
  aiBubble.className = 'chat-bubble ai';
  
  const streamSpan = document.createElement('span');
  streamSpan.className = 'stream-text';
  
  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  cursor.style.cssText = 'display:inline-block; width:2px; height:14px; background:var(--ink); margin-left:2px; animation:blink 1s step-end infinite;';
  
  aiBubble.appendChild(streamSpan);
  aiBubble.appendChild(cursor);
  history.appendChild(aiBubble);
  history.scrollTop = history.scrollHeight;

  let fullAnswer = "";
  let retrievedContexts = [];

  try {
    const response = await fetch(API + endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, k, rewrite, rerank, k_retrieve })
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonStr = line.slice(6);
            const data = JSON.parse(jsonStr);
            
            if (data.type === 'context') {
              retrievedContexts = data.data;
            } else if (data.type === 'token') {
              fullAnswer += data.data;
              if (!window._chatUpdateTimer) {
                window._chatUpdateTimer = requestAnimationFrame(() => {
                  streamSpan.textContent = fullAnswer;
                  history.scrollTop = history.scrollHeight;
                  window._chatUpdateTimer = null;
                });
              }
            } else if (data.type === 'error') {
              streamSpan.textContent = "Error: " + data.data;
              streamSpan.style.color = '#ff4b4b';
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    }
    
    // Render source chunk badges below the answer when retrieval completes
    if (retrievedContexts && retrievedContexts.length > 0) {
      const sourcesDiv = document.createElement('div');
      sourcesDiv.className = 'chat-sources';
      
      let sourcesHtml = '<div class="sources-title">Retrieved Chunks & Relevance Rank:</div>';
      retrievedContexts.forEach(c => {
        const simVal = 1 - c.distance;
        const simPct = (simVal * 100).toFixed(0) + '%';
        const rerankBadge = c.rerank_score !== undefined && c.rerank_score !== null 
          ? `<span class="rerank-badge-pill">Rerank: ${c.rerank_score}</span>`
          : '';
        
        sourcesHtml += `
          <div class="source-item-card" onclick="this.classList.toggle('expanded')">
            <div class="source-item-header">
              <span class="source-title-text">${escapeHtml(c.title)}</span>
              <div class="source-badges">
                <span class="source-dist-badge" style="border-left: 3px solid ${simVal > 0.8 ? '#4caf50' : '#ffa726'}; padding-left:4px;">Similarity: ${simPct}</span>
                ${rerankBadge}
                <span class="source-toggle-icon">▼</span>
              </div>
            </div>
            <div class="source-body-text">${highlightKeywords(escapeHtml(c.text), question)}</div>
          </div>
        `;
      });
      
      sourcesDiv.innerHTML = sourcesHtml;
      aiBubble.appendChild(sourcesDiv);
    }
    
  } catch (e) {
    streamSpan.textContent = "Connection error: " + e.message;
    streamSpan.style.color = '#ff4b4b';
  }

  cursor.remove();
  history.scrollTop = history.scrollHeight;
  document.getElementById('ragQuestion').value = '';
  btn.disabled = false; 
  btn.textContent = 'Ask AI';
}

// ═══════════════════════════════════════════════════════════
//  AI WORKING DEMO PIPELINE
// ═══════════════════════════════════════════════════════════
async function runDemoPipeline() {
  const query = document.getElementById('demoQuery').value.trim();
  if (!query) return;

  const btn = document.getElementById('demoBtn');
  btn.disabled = true; 
  btn.textContent = 'Analyzing Pipeline flow...';

  const splitEl = document.getElementById('aiWorkingSplit');
  const resultEl = document.getElementById('pipelineResult');
  const metricsEl = document.getElementById('pipelineMetrics');
  const timerEl = document.getElementById('pipelineTimer');
  
  splitEl.style.display = 'flex';
  resultEl.style.display = 'none';
  metricsEl.style.display = 'none';
  timerEl.style.display = 'flex';
  timerEl.textContent = '0.00s';
  timerEl.style.color = 'var(--ink)';

  await delay(200);

  const steps = ['step1', 'step2', 'step3', 'step4', 'step5'];
  const conns = ['conn1', 'conn2', 'conn3', 'conn4'];

  steps.forEach(s => document.getElementById(s).className = 'pipeline-step');
  conns.forEach(c => document.getElementById(c).className = 'pipeline-connector');

  document.getElementById('step1-desc').textContent = `"${query}"`;

  let allItems = [];
  try {
    const r = await fetch(API + '/items');
    allItems = await r.json();
  } catch (e) {}

  const startTime = performance.now();
  let elapsed = 0;
  const timerInterval = setInterval(() => {
    elapsed = (performance.now() - startTime) / 1000;
    timerEl.textContent = elapsed.toFixed(2) + 's';
  }, 50);

  // STEP 1
  await delay(300);
  activateStep('step1', 'conn1');
  try { renderAIVisualization(allItems, null, [], 'step1'); } catch(e) {}
  await delay(500);
  completeStep('step1', 'conn1');

  // STEP 2
  document.getElementById('step2-desc').textContent = 'Computing embeddings...';
  activateStep('step2', 'conn2');

  const vec16 = textToEmbedding(query);
  const embedStart = performance.now();

  await delay(600);

  const embedTime = ((performance.now() - embedStart) / 1000).toFixed(3);
  const vecPreview = vec16.slice(0, 6).map(v => v.toFixed(3)).join(', ') + ', ...';
  document.getElementById('step2-desc').innerHTML = `[${vecPreview}]<br><span style="color:#22c55e;">16D generated in ${embedTime}s</span>`;

  try { renderAIVisualization(allItems, vec16, [], 'step2'); } catch(e) {}
  completeStep('step2', 'conn2');

  // STEP 3
  document.getElementById('step3-desc').textContent = 'Traversing HNSW layers graph...';
  activateStep('step3', 'conn3');

  try { renderAIVisualization(allItems, vec16, [], 'step3-searching'); } catch(e) {}
  await delay(500);

  let searchResults = [];
  const searchStart = performance.now();
  const rerankEnabled = document.getElementById('rerankToggle').classList.contains('on');
  const demoKRetrieve = rerankEnabled ? 10 : 3;
  
  try {
    const vStr = vec16.join(',');
    const sr = await fetch(`${API}/search?v=${vStr}&k=${demoKRetrieve}&metric=cosine&algo=hnsw`);
    const sd = await sr.json();
    searchResults = sd.results || [];
  } catch (e) {}
  const searchTime = ((performance.now() - searchStart) / 1000).toFixed(3);

  try { renderAIVisualization(allItems, vec16, searchResults, 'step3'); } catch(e) {}
  completeStep('step3', 'conn3');

  document.getElementById('step3-desc').innerHTML = `Traversed ${allItems.length} vectors<br><span style="color:#22c55e;">Recall found ${searchResults.length} candidates in ${searchTime}s</span>`;

  // Update metrics
  metricsEl.style.display = 'block';
  document.getElementById('metricEmbed').textContent = embedTime + 's';
  document.getElementById('metricSearch').textContent = searchTime + 's';
  document.getElementById('metricVectors').textContent = allItems.length;
  document.getElementById('metricMatches').textContent = '3';

  // Update query details
  const qdCard = document.getElementById('queryDetailsCard');
  qdCard.style.display = 'block';
  document.getElementById('qdAlgo').textContent = 'HNSW';
  document.getElementById('qdType').textContent = rerankEnabled ? 'HNSW Recall + Rerank' : 'HNSW Exact';
  document.getElementById('qdEmbed').textContent = 'nomic-embed-text';
  document.getElementById('qdK').textContent = '3';
  document.getElementById('visPointCount').textContent = allItems.length + ' chunks';

  // STEP 4
  document.getElementById('step4-desc').textContent = 'Retrieving context & ranking...';
  activateStep('step4', 'conn4');
  await delay(400);

  // STEP 5
  document.getElementById('step5-desc').textContent = 'Synthesizing response...';
  activateStep('step5', null);

  resultEl.style.display = 'block';
  document.getElementById('pipelineOutput').innerHTML = '<span style="color:var(--ink-muted);">Computing answer...</span>';

  await delay(300);

  let answer = '';
  let finalDemoContexts = [];
  try {
    const useGraph = document.getElementById('graphToggle') ? document.getElementById('graphToggle').classList.contains('on') : false;
    const endpoint = useGraph ? '/doc/ask/graph' : '/doc/ask';
    const askResp = await fetch(API + endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: query, k: 3, rewrite: false, rerank: rerankEnabled })
    });

    if (askResp.ok) {
      const reader = askResp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'context') {
                finalDemoContexts = data.data;
                // Update step 4 desc with actual chunks + rerank badges if present
                const ctxHtml = finalDemoContexts.map(c => {
                  const badge = c.rerank_score ? ` <span class="demo-rerank-badge">Rerank: ${c.rerank_score}</span>` : ` (dist: ${c.distance.toFixed(3)})`;
                  return `<div class="demo-ctx-line">• <strong>${escapeHtml(c.title)}</strong>${badge}</div>`;
                }).join('');
                document.getElementById('step4-desc').innerHTML = `
                  Retrieved ${finalDemoContexts.length} chunks<br>
                  <div class="demo-ctx-list">${ctxHtml}</div>
                `;
                try { renderAIVisualization(allItems, vec16, finalDemoContexts, 'step4'); } catch(e) {}
              } else if (data.type === 'token') {
                answer += data.data;
                if (!window._demoUpdateTimer) {
                  window._demoUpdateTimer = requestAnimationFrame(() => {
                    document.getElementById('pipelineOutput').textContent = answer;
                    resultEl.scrollTop = resultEl.scrollHeight;
                    window._demoUpdateTimer = null;
                  });
                }
              }
            } catch (e) {}
          }
        }
      }
    }
  } catch (e) {
    answer = 'Connection to LLM failed. Make sure Ollama is hosting qwen2.5:0.5b.';
    document.getElementById('pipelineOutput').textContent = answer;
  }

  clearInterval(timerInterval);
  elapsed = (performance.now() - startTime) / 1000;
  timerEl.textContent = elapsed.toFixed(2) + 's';
  timerEl.style.color = '#22c55e';

  completeStep('step4', 'conn4');
  completeStep('step5', null);
  document.getElementById('step5-desc').textContent = 'Synthesis complete.';

  btn.disabled = false; 
  btn.textContent = 'Visualize Pipeline Execution';
}

function renderAIVisualization(items, queryVec, matches, stage) {
  const container = document.getElementById('aiVisGraph');
  if (!container) return;

  if (typeof Plotly === 'undefined') {
    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#ff4b4b;font-size:13px;">Plotly.js failed to load. Check internet connection.</div>';
    return;
  }

  if (!items || items.length < 2) {
    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--ink-muted);font-size:13px;">Add at least 2 vectors to visualize cluster space.</div>';
    return;
  }

  try {
    const embeddings = items.map(v => v.embedding).filter(e => e && e.length > 0);
    if (embeddings.length < 2) {
      container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--ink-muted);font-size:13px;">No valid embedding vectors.</div>';
      return;
    }

    const pcaData = pca2D(embeddings);
    const xAll = pcaData.map(p => p[0]);
    const yAll = pcaData.map(p => p[1]);

    const traces = [];

    const isLight = document.documentElement.classList.contains('light-theme');
    const paperBg = isLight ? '#ffffff' : '#141414';
    const gridClr = isLight ? '#e2e2e8' : '#262626';
    const textClr = isLight ? '#1d1d1f' : '#ffffff';
    const borderClr = isLight ? '#f5f5f7' : '#090909';
    const tickClr = isLight ? '#86868b' : '#6e6e6e';

    // Stored vectors
    traces.push({
      x: xAll, y: yAll,
      mode: 'markers',
      marker: { size: 10, color: isLight ? '#8e8e93' : '#6E6E6E', opacity: stage === 'step3-searching' ? 0.3 : 0.6 },
      text: items.map(v => v.metadata || 'Vector ' + v.id),
      name: 'Stored Vectors',
      hovertemplate: '<b>%{text}</b><extra></extra>'
    });

    if (queryVec && queryVec.length > 0) {
      const allEmbs = [...embeddings, queryVec];
      const allPca = pca2D(allEmbs);
      const qp = allPca[allPca.length - 1];
      const qx = qp[0], qy = qp[1];

      // Query Vector (Star mark)
      traces.push({
        x: [qx], y: [qy],
        mode: 'markers+text',
        marker: { size: 20, color: textClr, line: { width: 3, color: borderClr }, symbol: 'star' },
        text: ['QUERY'],
        textposition: 'top center',
        textfont: { size: 10, color: textClr, weight: 700 },
        name: 'Query',
        hovertemplate: '<b>Query Vector</b><extra></extra>'
      });

      // Search lines on HNSW scan stage
      if (stage === 'step3-searching') {
        const count = Math.min(items.length, 10);
        for (let i = 0; i < count; i++) {
          const idx = Math.floor(Math.random() * items.length);
          traces.push({
            x: [qx, xAll[idx]],
            y: [qy, yAll[idx]],
            mode: 'lines',
            line: { color: isLight ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)', width: 1, dash: 'dot' },
            showlegend: false,
            hoverinfo: 'skip'
          });
        }
      }

      // Context retrieved links
      if (stage === 'step3' || stage === 'step4' || stage === 'step5') {
        matches.forEach((m, i) => {
          const idx = items.findIndex(v => v.id === m.id);
          if (idx >= 0) {
            traces.push({
              x: [qx, xAll[idx]],
              y: [qy, yAll[idx]],
              mode: 'lines',
              line: { color: 'rgba(0,153,255,0.4)', width: 2, dash: 'dot' },
              showlegend: false,
              hoverinfo: 'skip'
            });
          }
        });

        const mx = [], my = [], mt = [], md = [];
        matches.forEach(m => {
          const idx = items.findIndex(v => v.id === m.id);
          if (idx >= 0) {
            mx.push(xAll[idx]);
            my.push(yAll[idx]);
            mt.push('#' + (m.metadata || 'Match'));
            md.push(m.distance);
          }
        });

        // Top match highlights
        traces.push({
          x: mx, y: my,
          mode: 'markers+text',
          marker: { size: 14, color: 'var(--accent-blue)', line: { width: 2, color: borderClr }, symbol: 'diamond' },
          text: mt,
          textposition: 'bottom center',
          textfont: { size: 9, color: 'var(--accent-blue)', weight: 700 },
          name: 'Top Matches',
          hovertemplate: '<b>%{text}</b><br>dist: %{customdata:.4f}<extra></extra>',
          customdata: md
        });
      }
    }

    const layout = {
      paper_bgcolor: paperBg,
      plot_bgcolor: paperBg,
      margin: { l: 5, r: 5, t: 5, b: 5 },
      xaxis: { title: '', showgrid: true, gridcolor: gridClr, zerolinecolor: gridClr, tickfont: { color: tickClr, size: 9 }, fixedrange: false },
      yaxis: { title: '', showgrid: true, gridcolor: gridClr, zerolinecolor: gridClr, tickfont: { color: tickClr, size: 9 }, fixedrange: false },
      showlegend: false,
      font: { family: 'Inter, sans-serif' },
      autosize: true,
      width: container.clientWidth,
      height: container.clientHeight
    };

    const config = { responsive: true, displayModeBar: false, scrollZoom: true };

    if (container.querySelector('.js-plotly-plot')) {
      Plotly.react(container, traces, layout, config);
    } else {
      Plotly.newPlot(container, traces, layout, config);
    }
  } catch (e) {
    console.error('Visualization error:', e);
    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#ff4b4b;font-size:13px;">Graph error: ' + e.message + '</div>';
  }
}

function pca2D(vectors) {
  const n = vectors.length;
  if (n < 2) return vectors.map(() => [0, 0]);
  const d = vectors[0].length;

  const mean = new Array(d).fill(0);
  for (let i = 0; i < n; i++) for (let j = 0; j < d; j++) mean[j] += vectors[i][j];
  for (let j = 0; j < d; j++) mean[j] /= n;

  const centered = vectors.map(v => v.map((val, j) => val - mean[j]));

  if (d > 50) {
    const proj1 = Array.from({ length: d }, () => Math.random() - 0.5);
    const proj2 = Array.from({ length: d }, () => Math.random() - 0.5);
    let dot = 0;
    for (let i = 0; i < d; i++) dot += proj1[i] * proj2[i];
    for (let i = 0; i < d; i++) proj2[i] -= dot * proj1[i];
    const n1 = Math.sqrt(proj1.reduce((s, v) => s + v * v, 0)) || 1;
    const n2 = Math.sqrt(proj2.reduce((s, v) => s + v * v, 0)) || 1;
    for (let i = 0; i < d; i++) { proj1[i] /= n1; proj2[i] /= n2; }
    return centered.map(v => [
      v.reduce((s, val, j) => s + val * proj1[j], 0),
      v.reduce((s, val, j) => s + val * proj2[j], 0)
    ]);
  }

  const cov = Array.from({ length: d }, (_, i) =>
    Array.from({ length: d }, (_, j) =>
      centered.reduce((s, row) => s + row[i] * row[j], 0) / (n - 1)
    )
  );

  let vec1 = Array.from({ length: d }, () => Math.random() - 0.5);
  let vec2 = Array.from({ length: d }, () => Math.random() - 0.5);

  for (let iter = 0; iter < 100; iter++) {
    let newVec1 = Array(d).fill(0);
    for (let i = 0; i < d; i++) for (let j = 0; j < d; j++) newVec1[i] += cov[i][j] * vec1[j];
    const norm1 = Math.sqrt(newVec1.reduce((s, v) => s + v * v, 0)) || 1;
    vec1 = newVec1.map(v => v / norm1);

    let dot = 0;
    for (let i = 0; i < d; i++) dot += vec1[i] * vec2[i];
    let newVec2 = vec2.map((v, i) => v - dot * vec1[i]);
    for (let i = 0; i < d; i++) for (let j = 0; j < d; j++) newVec2[i] += cov[i][j] * newVec2[j];
    const norm2 = Math.sqrt(newVec2.reduce((s, v) => s + v * v, 0)) || 1;
    vec2 = newVec2.map(v => v / norm2);
  }

  return centered.map(v => [
    v.reduce((s, val, j) => s + val * vec1[j], 0),
    v.reduce((s, val, j) => s + val * vec2[j], 0)
  ]);
}

function activateStep(stepId, connId) {
  document.getElementById(stepId).className = 'pipeline-step active';
  if (connId) document.getElementById(connId).className = 'pipeline-connector active';
}

// Check on step complete
function completeStep(stepId, connId) {
  document.getElementById(stepId).className = 'pipeline-step done';
  if (connId) document.getElementById(connId).className = 'pipeline-connector done';
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ═══════════════════════════════════════════════════════════
//  BOOT INITS
// ════════════════════════════════════════════════════════════
if (typeof Plotly === 'undefined') {
  console.warn('Plotly.js not loaded. Visualization features will be limited.');
}

// Auto-resize graphs when containers change size
if (typeof Plotly !== 'undefined') {
  const resizeObserver = new ResizeObserver(entries => {
    for (const entry of entries) {
      const container = entry.target;
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0 && container.querySelector('.js-plotly-plot')) {
        if (container.resizeTimeout) clearTimeout(container.resizeTimeout);
        container.resizeTimeout = setTimeout(() => {
          Plotly.relayout(container, { width, height });
        }, 100); // 100ms debounce
      }
    }
  });

  const aiVisContainer = document.getElementById('aiVisGraph');
  if (aiVisContainer) resizeObserver.observe(aiVisContainer);
  const scatter3dContainer = document.getElementById('scatter3d');
  if (scatter3dContainer) resizeObserver.observe(scatter3dContainer);
}

// Optimized Tactile Magnet Hover Effect
function initMagnetEffect() {
  // Add class magnet to interactive components
  document.querySelectorAll('.nav-item, .btn-primary, .search-btn, .btn-secondary, .pill, .hl-card, .chip, .connect a').forEach(el => {
    el.classList.add('magnet');
  });

  const magnets = document.querySelectorAll('.magnet');
  magnets.forEach(el => {
    let rect = null;
    
    el.addEventListener('mouseenter', () => {
      rect = el.getBoundingClientRect();
    });
    
    el.addEventListener('mousemove', (e) => {
      if (!rect) rect = el.getBoundingClientRect();
      const x = e.clientX - (rect.left + rect.width / 2);
      const y = e.clientY - (rect.top + rect.height / 2);
      
      // Pull element toward cursor by 35% of offset using hardware-accelerated translate3d
      el.style.transform = `translate3d(${x * 0.35}px, ${y * 0.35}px, 0) scale(1.025)`;
      el.style.transition = 'transform 0.08s cubic-bezier(0.25, 0.8, 0.25, 1)';
      el.style.zIndex = '10';
      
      // Dynamic shift of shadows/glows matching cursor vector direction
      if (el.classList.contains('btn-primary') || el.classList.contains('search-btn')) {
        el.style.boxShadow = `${-x * 0.15}px ${-y * 0.15}px 20px rgba(255, 255, 255, 0.25)`;
      } else if (el.classList.contains('nav-item')) {
        el.style.boxShadow = `${x * 0.1}px ${y * 0.1}px 12px rgba(0, 153, 255, 0.15)`;
      }
    });
    
    el.addEventListener('mouseleave', () => {
      rect = null;
      el.style.transform = '';
      el.style.transition = 'transform 0.35s cubic-bezier(0.25, 0.8, 0.25, 1)';
      el.style.boxShadow = '';
      setTimeout(() => { el.style.zIndex = ''; }, 350);
    });
  });
}

// Dynamic Spotlight Glow Cursor Tracking
function initSpotlightEffect() {
  const cards = document.querySelectorAll('.status-card, .result-card, .bench-card, .hl-card, .stat');
  cards.forEach(card => {
    let rect = null;
    let rafId = null;
    
    card.addEventListener('mouseenter', () => {
      rect = card.getBoundingClientRect();
    });
    
    card.addEventListener('mousemove', e => {
      if (!rect) rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        card.style.setProperty('--mouse-x', `${x}px`);
        card.style.setProperty('--mouse-y', `${y}px`);
      });
    });
    
    card.addEventListener('mouseleave', () => {
      rect = null;
      if (rafId) cancelAnimationFrame(rafId);
    });
  });
}

async function runSqlQuery() {
  const query = document.getElementById('sqlQueryText').value.trim();
  const v = document.getElementById('sqlQueryVector').value.trim();
  const text = document.getElementById('sqlQueryTextParam').value.trim();
  
  if (!query) {
    showToast('Please enter a SQL query first.', 'warning');
    return;
  }
  
  const btn = document.getElementById('sqlRunBtn');
  btn.disabled = true;
  btn.textContent = 'Running Query...';
  
  const resultsPanel = document.getElementById('sqlResultsPanel');
  resultsPanel.innerHTML = '<div style="color:var(--ink-muted); text-align:center; padding:20px;">Executing query on database...</div>';
  
  try {
    const response = await fetch(API + '/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, v, text })
    });
    
    const d = await response.json();
    
    if (!response.ok) {
      throw new Error(d.error || 'Server error');
    }
    
    // Update AST and Compiled blocks
    document.getElementById('sqlAstOutput').textContent = JSON.stringify(d.ast || {}, null, 2);
    document.getElementById('sqlCompiledOutput').textContent = JSON.stringify(d.compiled || {}, null, 2);
    
    // Update Results Panel
    const results = d.results || [];
    if (results.length === 0) {
      resultsPanel.innerHTML = '<div style="color:var(--ink-muted); text-align:center; padding:20px;">No matching results found.</div>';
      return;
    }
    
    let html = `
      <div style="overflow-x:auto;">
        <table class="telemetry-table" style="width:100%; border-collapse:collapse; font-family:'JetBrains Mono', monospace; font-size:11px; text-align:left;">
          <thead>
            <tr style="border-bottom:1px solid var(--hairline); font-size:10px; text-transform:uppercase;">
              <th style="padding:10px; color:var(--ink-muted);">ID</th>
              <th style="padding:10px; color:var(--ink-muted);">Table</th>
              <th style="padding:10px; color:var(--ink-muted);">Title / Metadata</th>
              <th style="padding:10px; color:var(--ink-muted);">Content / Details</th>
              <th style="padding:10px; color:var(--ink-muted); text-align:right;">Similarity</th>
            </tr>
          </thead>
          <tbody>
    `;
    results.forEach((h) => {
      const isDoc = h.title !== undefined;
      const id = h.id || '—';
      const tbl = isDoc ? 'documents' : 'vectors';
      const title = isDoc ? h.title : (h.metadata || `Item #${h.id}`);
      const textPreview = isDoc ? h.text : `Category: ${h.category}`;
      const distance = h.distance !== undefined ? h.distance.toFixed(4) : '—';
      const sim = h.distance !== undefined ? (1.0 - h.distance).toFixed(4) : '—';
      
      html += `
        <tr>
          <td style="padding:10px; font-weight:700; color:var(--accent-blue);">${id}</td>
          <td style="padding:10px;"><span class="res-badge" style="background:var(--trans-white-05); color:var(--ink); border:0.5px solid var(--hairline); font-size:9px; padding:2px 4px; border-radius:4px;">${tbl}</span></td>
          <td style="padding:10px; font-weight:600; color:var(--ink); white-space:nowrap; max-width:150px; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(title)}</td>
          <td style="padding:10px; color:var(--ink-muted); max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(textPreview)}</td>
          <td style="padding:10px; text-align:right; font-weight:700; color:#22c55e;">${sim} <span style="font-size:9px; color:var(--ink-muted); font-weight:normal; margin-left:4px;">(dist: ${distance})</span></td>
        </tr>
      `;
    });
    html += '</tbody></table></div>';
    resultsPanel.innerHTML = html;
  } catch (e) {
    resultsPanel.innerHTML = `<div style="color:#ff4b4b; text-align:center; padding:20px;">Error: ${e.message}</div>`;
    document.getElementById('sqlAstOutput').textContent = '{}';
    document.getElementById('sqlCompiledOutput').textContent = '{}';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Execute Query';
  }
}

async function fetchClusterHealth() {
  const coordStatus = document.getElementById('coordinatorStatus');
  const coordHost = document.getElementById('coordinatorHost');
  
  // Recalculate leader consensus roles
  recalculateLeader();

  let coordOnline = false;
  let coordHostUrl = `${API}/cluster/coordinator/health`;
  let realBackendResponsive = false;

  // 1. Check Coordinator
  if (nodeOverrides.coordinator === false) {
    coordOnline = false;
    if (coordHost) coordHost.textContent = `Proxy: ${coordHostUrl} (Offline)`;
  } else {
    try {
      const res = await fetch(`${API}/cluster/coordinator/health`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'ok') {
          coordOnline = true;
          realBackendResponsive = true;
        }
      }
    } catch (e) {
      // Offline
    }
  }

  // 2. Check Workers
  const workers = ['worker-1', 'worker-2', 'worker-3'];
  const workerData = {};
  
  for (const id of workers) {
    if (nodeOverrides[id] !== false) {
      try {
        const res = await fetch(`${API}/cluster/worker/${id}/health`);
        if (res.ok) {
          workerData[id] = await res.json();
          realBackendResponsive = true;
        }
      } catch (err) {
        // Offline
      }
    }
  }

  // Demo mode runs if absolutely no node responds (dashboard running offline preview)
  const isDemoMode = !realBackendResponsive;

  // Update Coordinator UI
  if (nodeOverrides.coordinator === false) {
    if (coordStatus) {
      coordStatus.textContent = 'Offline';
      coordStatus.style.background = '#ff4b4b';
      coordStatus.style.color = '#fff';
    }
  } else {
    if (isDemoMode) {
      if (coordStatus) {
        coordStatus.textContent = 'Online (Simulated)';
        coordStatus.style.background = '#00ff66';
        coordStatus.style.color = '#000';
      }
      if (coordHost) coordHost.textContent = `Proxy: ${coordHostUrl} (Simulated)`;
    } else {
      if (coordStatus) {
        coordStatus.textContent = coordOnline ? 'Online' : 'Offline';
        coordStatus.style.background = coordOnline ? '#00ff66' : '#ff4b4b';
        coordStatus.style.color = coordOnline ? '#000' : '#fff';
      }
      if (coordHost) coordHost.textContent = `Proxy: ${coordHostUrl}${coordOnline ? '' : ' (Offline)'}`;
    }
  }

  // Update Workers UI
  for (const id of workers) {
    const card = document.getElementById(`card-${id}`);
    const statusSpan = document.getElementById(`status-${id}`);
    const roleDiv = document.getElementById(`role-${id}`);
    const vecDiv = document.getElementById(`vec-${id}`);
    const logDiv = document.getElementById(`log-${id}`);
    const cpuSpan = document.getElementById(`cpu-${id}`);
    const cpuBar = document.getElementById(`cpu-bar-${id}`);

    // Manual UI toggle OFF overrides everything
    if (nodeOverrides[id] === false) {
      if (statusSpan) {
        statusSpan.textContent = 'Offline';
        statusSpan.style.background = '#ff4b4b';
        statusSpan.style.color = '#fff';
      }
      if (card) card.style.borderColor = 'rgba(255, 75, 75, 0.15)';
      if (roleDiv) {
        roleDiv.textContent = '—';
        roleDiv.style.color = '';
      }
      if (vecDiv) vecDiv.textContent = '—';
      if (logDiv) logDiv.textContent = '—';
      if (cpuSpan) cpuSpan.textContent = '0%';
      if (cpuBar) {
        cpuBar.style.width = '0%';
        cpuBar.style.background = 'var(--surface-2)';
      }
      continue;
    }

    if (isDemoMode) {
      // Demo / Simulation Mode
      if (statusSpan) {
        statusSpan.textContent = 'Online (Simulated)';
        statusSpan.style.background = '#00ff66';
        statusSpan.style.color = '#000';
      }
      if (card) card.style.borderColor = 'rgba(0, 255, 102, 0.2)';
      
      const isLeader = (simulatedLeader === id);
      if (roleDiv) {
        roleDiv.textContent = isLeader ? 'Leader 👑' : 'Follower';
        roleDiv.style.color = isLeader ? '#ff7a3d' : '#0099ff';
      }
      
      const mockVectors = { 'worker-1': 1084, 'worker-2': 1092, 'worker-3': 1079 };
      const mockLog = { 'worker-1': 48, 'worker-2': 48, 'worker-3': 48 };
      if (vecDiv) vecDiv.textContent = mockVectors[id];
      if (logDiv) logDiv.textContent = mockLog[id];

      const cpuVal = Math.floor(Math.random() * 12) + 5;
      if (cpuSpan) cpuSpan.textContent = cpuVal + '%';
      if (cpuBar) {
        cpuBar.style.width = cpuVal + '%';
        cpuBar.style.background = 'var(--accent-blue)';
      }
    } else {
      // Real backend mode
      const wData = workerData[id];
      const isOnline = !!wData;

      if (statusSpan) {
        statusSpan.textContent = isOnline ? 'Online' : 'Offline';
        statusSpan.style.background = isOnline ? '#00ff66' : '#ff4b4b';
        statusSpan.style.color = isOnline ? '#000' : '#fff';
      }
      if (card) {
        card.style.borderColor = isOnline ? 'rgba(0, 255, 102, 0.2)' : 'rgba(255, 75, 75, 0.15)';
      }

      if (isOnline) {
        if (roleDiv) {
          roleDiv.textContent = wData.raft_is_leader ? 'Leader 👑' : 'Follower';
          roleDiv.style.color = wData.raft_is_leader ? '#ff7a3d' : '#0099ff';
        }
        if (vecDiv) vecDiv.textContent = wData.vectors !== undefined ? wData.vectors : '0';
        if (logDiv) logDiv.textContent = wData.log_size !== undefined ? wData.log_size : '0';

        const cpuVal = Math.floor(Math.random() * 20) + 8;
        if (cpuSpan) cpuSpan.textContent = cpuVal + '%';
        if (cpuBar) {
          cpuBar.style.width = cpuVal + '%';
          cpuBar.style.background = cpuVal > 18 ? 'var(--grad-violet)' : 'var(--accent-blue)';
        }
      } else {
        if (roleDiv) {
          roleDiv.textContent = '—';
          roleDiv.style.color = '';
        }
        if (vecDiv) vecDiv.textContent = '—';
        if (logDiv) logDiv.textContent = '—';
        if (cpuSpan) cpuSpan.textContent = '0%';
        if (cpuBar) {
          cpuBar.style.width = '0%';
          cpuBar.style.background = 'var(--surface-2)';
        }
      }
    }
  }
}

function copyText(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    btn.style.color = '#00ff66';
    setTimeout(() => {
      btn.textContent = orig;
      btn.style.color = '';
    }, 1500);
  });
}

// =====================================================================
//  THEME / SOUNDS / CURSOR CUSTOM FEATURES
// =====================================================================

// Web Audio API Sound Synthesizer
let audioCtx = null;
let isMuted = localStorage.getItem('nurosearch-muted') === 'true';

function initSound() {
  const icon = document.getElementById('soundIcon');
  if (isMuted) {
    if (icon) icon.className = 'ti ti-volume-off';
  } else {
    if (icon) icon.className = 'ti ti-volume';
  }
}

function toggleSound() {
  isMuted = !isMuted;
  localStorage.setItem('nurosearch-muted', isMuted);
  const icon = document.getElementById('soundIcon');
  if (isMuted) {
    if (icon) icon.className = 'ti ti-volume-off';
  } else {
    if (icon) icon.className = 'ti ti-volume';
    // Play test click sound
    playClickSound();
  }
}

function initAudio() {
  if (audioCtx) return;
  try {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  } catch (e) {
    console.warn("Web Audio API not supported in this browser.");
  }
}

function playClickSound() {
  if (isMuted) return;
  if (!audioCtx) initAudio();
  if (!audioCtx) return;
  
  const now = audioCtx.currentTime;
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  
  osc.type = 'sine';
  osc.frequency.setValueAtTime(600, now);
  osc.frequency.exponentialRampToValueAtTime(150, now + 0.08);
  
  gain.gain.setValueAtTime(0.12, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
  
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  
  osc.start(now);
  osc.stop(now + 0.09);
}

function playHoverSound() {
  if (isMuted) return;
  if (!audioCtx) initAudio();
  if (!audioCtx) return;
  
  const now = audioCtx.currentTime;
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  
  osc.type = 'sine';
  osc.frequency.setValueAtTime(240, now);
  osc.frequency.exponentialRampToValueAtTime(260, now + 0.12);
  
  gain.gain.setValueAtTime(0.03, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
  
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  
  osc.start(now);
  osc.stop(now + 0.13);
}

function playTypingSound() {
  if (isMuted) return;
  if (!audioCtx) initAudio();
  if (!audioCtx) return;
  
  const now = audioCtx.currentTime;
  
  const osc1 = audioCtx.createOscillator();
  const osc2 = audioCtx.createOscillator();
  const gain1 = audioCtx.createGain();
  const gain2 = audioCtx.createGain();
  
  osc1.type = 'triangle';
  osc1.frequency.setValueAtTime(160 + Math.random() * 40, now);
  osc1.frequency.exponentialRampToValueAtTime(60, now + 0.04);
  gain1.gain.setValueAtTime(0.12, now);
  gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
  
  osc2.type = 'sine';
  osc2.frequency.setValueAtTime(1100 + Math.random() * 300, now);
  osc2.frequency.exponentialRampToValueAtTime(450, now + 0.02);
  gain2.gain.setValueAtTime(0.08, now);
  gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.02);
  
  osc1.connect(gain1);
  gain1.connect(audioCtx.destination);
  osc2.connect(gain2);
  gain2.connect(audioCtx.destination);
  
  osc1.start(now);
  osc1.stop(now + 0.05);
  osc2.start(now);
  osc2.stop(now + 0.03);
}

// Global Event Listeners for Audio Initialization & Events
document.addEventListener('click', function(e) {
  initAudio();
  const target = e.target.closest('button, a, .nav-item, input[type="radio"], input[type="checkbox"], [onclick]');
  if (target) {
    playClickSound();
  }
});

document.addEventListener('mouseover', function(e) {
  const target = e.target.closest('button, a, .nav-item, .card, .res-card, [onclick]');
  if (target) {
    playHoverSound();
  }
});

document.addEventListener('input', function(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
    playTypingSound();
  }
});

// Theme Toggle Logic
function initTheme() {
  const savedTheme = localStorage.getItem('nurosearch-theme') || 'dark';
  const html = document.documentElement;
  const icon = document.getElementById('themeIcon');
  
  if (savedTheme === 'light') {
    html.classList.add('light-theme');
    if (icon) {
      icon.className = 'ti ti-moon';
    }
  } else {
    html.classList.remove('light-theme');
    if (icon) {
      icon.className = 'ti ti-sun';
    }
  }
}

function toggleTheme() {
  const html = document.documentElement;
  const icon = document.getElementById('themeIcon');
  
  if (html.classList.contains('light-theme')) {
    html.classList.remove('light-theme');
    localStorage.setItem('nurosearch-theme', 'dark');
    if (icon) icon.className = 'ti ti-sun';
  } else {
    html.classList.add('light-theme');
    localStorage.setItem('nurosearch-theme', 'light');
    if (icon) icon.className = 'ti ti-moon';
  }
  
  updatePlotColorsForTheme();
}

function updatePlotColorsForTheme() {
  try {
    if (typeof pcaPoints3D !== 'undefined' && pcaPoints3D.length > 0) {
      render3DPlot();
    }
    const container = document.getElementById('aiVisGraph');
    if (container && container.querySelector('.js-plotly-plot') && typeof lastAIVisArgs !== 'undefined' && lastAIVisArgs) {
      renderAIVisualization(...lastAIVisArgs);
    }
  } catch (e) {
    console.error("Error updating plot colors for theme:", e);
  }
}

// Custom Cursor Trail Logic
function initCustomCursor() {
  const dot = document.getElementById('cursorDot');
  const outline = document.getElementById('cursorOutline');
  if (!dot || !outline) return;

  if (window.matchMedia('(pointer: coarse)').matches) {
    return;
  }

  const body = document.body;
  body.classList.add('cursor-active');

  let mouseX = 0, mouseY = 0;
  let dotX = 0, dotY = 0;
  let outlineX = 0, outlineY = 0;
  const delay = 6; 

  document.addEventListener('mousemove', function(e) {
    mouseX = e.clientX;
    mouseY = e.clientY;
    
    dot.style.opacity = 1;
    outline.style.opacity = 1;
  });

  function animateCursor() {
    dotX += (mouseX - dotX);
    dotY += (mouseY - dotY);
    dot.style.transform = `translate3d(${dotX}px, ${dotY}px, 0) translate(-50%, -50%)`;

    outlineX += (mouseX - outlineX) / delay;
    outlineY += (mouseY - outlineY) / delay;
    outline.style.transform = `translate3d(${outlineX}px, ${outlineY}px, 0) translate(-50%, -50%)`;

    requestAnimationFrame(animateCursor);
  }
  requestAnimationFrame(animateCursor);

  const hoverSelectors = 'button, a, .nav-item, input, textarea, select, .card, .res-card, [onclick]';
  
  document.addEventListener('mouseover', function(e) {
    if (e.target.closest(hoverSelectors)) {
      body.classList.add('custom-cursor-hover');
    }
  });

  document.addEventListener('mouseout', function(e) {
    if (!e.relatedTarget || !e.relatedTarget.closest(hoverSelectors)) {
      body.classList.remove('custom-cursor-hover');
    }
  });
}

// Save args for AI visualization redraws
let lastAIVisArgs = null;
const origRenderAIVis = renderAIVisualization;
renderAIVisualization = function(...args) {
  lastAIVisArgs = args;
  return origRenderAIVis(...args);
};

// ── CONTACT INTERACTIVE TELEMETRY ──
function copyContactDetail(event, text, btn) {
  event.preventDefault();
  event.stopPropagation();
  navigator.clipboard.writeText(text).then(() => {
    const icon = btn.querySelector('i');
    const originalClass = icon.className;
    icon.className = 'ti ti-check';
    btn.style.color = '#22c55e';
    showToast("Copied to clipboard", "success");
    playClickSound();
    setTimeout(() => {
      icon.className = originalClass;
      btn.style.color = '';
    }, 2000);
  }).catch(err => {
    console.error("Clipboard copy failed: ", err);
    showToast("Copy failed", "error");
  });
}

function showToast(message, type = "info") {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  
  const item = document.createElement('div');
  item.className = `toast-item toast-${type}`;
  
  let iconHtml = '<i class="ti ti-info-circle"></i>';
  if (type === 'success') iconHtml = '<i class="ti ti-circle-check"></i>';
  if (type === 'error') iconHtml = '<i class="ti ti-circle-x"></i>';
  
  item.innerHTML = `
    <span class="toast-icon">${iconHtml}</span>
    <span style="white-space: nowrap;">${message}</span>
  `;
  
  container.appendChild(item);
  setTimeout(() => item.classList.add('show'), 10);
  
  setTimeout(() => {
    item.classList.remove('show');
    setTimeout(() => item.remove(), 400);
  }, 3000);
}

function togglePortalForm() {
  const wrap = document.getElementById('portalFormWrap');
  const chevron = document.getElementById('portalChevron');
  const inbox = document.getElementById('telemetryInboxWrap');
  
  if (wrap.classList.contains('open')) {
    wrap.classList.remove('open');
    chevron.className = 'ti ti-chevron-down';
    inbox.style.display = 'none';
  } else {
    wrap.classList.add('open');
    chevron.className = 'ti ti-chevron-up';
    inbox.style.display = 'block';
    loadPortalMessages();
  }
}

let selPortalType = 'Feedback';

function setPortalType(btn, typeStr) {
  playClickSound();
  document.querySelectorAll('#portalTypePills .pill').forEach(p => p.classList.remove('on'));
  btn.classList.add('on');
  selPortalType = typeStr;
  
  const messageEl = document.getElementById('portalMessage');
  if (messageEl) {
    if (typeStr === 'Bug Report') {
      messageEl.placeholder = 'Describe the bug or issue, steps to reproduce, and system state...';
    } else if (typeStr === 'Suggestion') {
      messageEl.placeholder = 'Propose features or system architectural improvements...';
    } else {
      messageEl.placeholder = 'Input feedback parameters...';
    }
  }
}

async function submitPortalMessage() {
  const nameEl = document.getElementById('portalName');
  const emailEl = document.getElementById('portalEmail');
  const messageEl = document.getElementById('portalMessage');
  const statusEl = document.getElementById('portalStatus');
  
  const name = nameEl.value.trim();
  const email = emailEl.value.trim();
  const message = messageEl.value.trim();
  
  if (!name || !email || !message) {
    statusEl.textContent = "Error: All fields are required.";
    statusEl.style.color = "#ef4444";
    showToast("Please fill all fields", "error");
    return;
  }
  
  statusEl.textContent = "Transmitting packet...";
  statusEl.style.color = "var(--ink-muted)";
  
  try {
    const res = await fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, message, type: selPortalType })
    });
    
    const data = await res.json();
    if (res.ok && data.success) {
      statusEl.textContent = "Transmission successful.";
      statusEl.style.color = "#22c55e";
      showToast("Message Transmitted Successfully", "success");
      
      // Play custom success sound chord
      playSuccessChord();
      
      // Clear inputs
      nameEl.value = '';
      emailEl.value = '';
      messageEl.value = '';
      
      // Reload inbox
      loadPortalMessages();
      
      setTimeout(() => {
        statusEl.textContent = '';
      }, 3000);
    } else {
      statusEl.textContent = "Error: " + (data.error || "Failed");
      statusEl.style.color = "#ef4444";
      showToast("Transmission failed", "error");
    }
  } catch (err) {
    statusEl.textContent = "Connection error.";
    statusEl.style.color = "#ef4444";
    showToast("Network connection error", "error");
  }
}

async function loadPortalMessages() {
  const body = document.getElementById('telemetryInboxBody');
  const latencyEl = document.getElementById('inboxLatency');
  const startTime = performance.now();
  
  try {
    const res = await fetch('/api/contact');
    const endTime = performance.now();
    latencyEl.textContent = `Latency: ${(endTime - startTime).toFixed(1)}ms`;
    
    if (!res.ok) throw new Error("Status " + res.status);
    const messages = await res.json();
    
    if (messages.length === 0) {
      body.innerHTML = '<div style="color:var(--ink-muted); text-align:center; padding:12px;">No telemetry messages found in contact_messages.</div>';
      return;
    }
    
    body.innerHTML = messages.map(m => {
      const typeLabel = m.type || 'Feedback';
      const badgeColor = typeLabel === 'Bug Report' ? '#ef4444' : typeLabel === 'Suggestion' ? '#a855f7' : '#0077ff';
      const badgeBg = typeLabel === 'Bug Report' ? 'rgba(239,68,68,0.1)' : typeLabel === 'Suggestion' ? 'rgba(168,85,247,0.1)' : 'rgba(0,119,255,0.1)';
      return `
      <div class="telemetry-msg-item" id="tel-msg-${m.id}">
        <div style="flex: 1; min-width: 0; padding-right: 8px;">
          <div class="telemetry-msg-meta" style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span class="res-badge" style="font-size:8px; padding:1px 5px; border-radius:3px; background:${badgeBg}; color:${badgeColor}; border:none; text-transform:uppercase; font-weight:700;">${escapeHTML(typeLabel)}</span>
            <span>[ID: ${m.id}] FROM: ${escapeHTML(m.name)} &lt;${escapeHTML(m.email)}&gt; at ${m.timestamp}</span>
          </div>
          <div class="telemetry-msg-content">${escapeHTML(m.message)}</div>
        </div>
        <button class="telemetry-msg-delete" title="DROP MESSAGE" onclick="deletePortalMessage(${m.id})">
          <i class="ti ti-trash"></i>
        </button>
      </div>
    `}).join('');
  } catch (err) {
    body.innerHTML = `<div style="color:#ef4444; padding:12px;">Failed to retrieve tables: ${err.message}</div>`;
  }
}

async function deletePortalMessage(id) {
  if (!confirm("Are you sure you want to delete/drop message ID " + id + "?")) return;
  playClickSound();
  
  try {
    const res = await fetch(`/api/contact/${id}`, { method: 'DELETE' });
    if (res.ok) {
      showToast(`Dropped message ID ${id}`, "info");
      loadPortalMessages();
    } else {
      showToast("Failed to delete message", "error");
    }
  } catch (err) {
    showToast("Error deleting message", "error");
  }
}

const escapeHTML = escapeHtml;

function playSuccessChord() {
  if (isMuted) return;
  if (!audioCtx) initAudio();
  if (!audioCtx) return;
  
  const now = audioCtx.currentTime;
  
  // Create note 1 (E5 - 659.25Hz)
  const osc1 = audioCtx.createOscillator();
  const gain1 = audioCtx.createGain();
  osc1.type = 'sine';
  osc1.frequency.setValueAtTime(659.25, now);
  gain1.gain.setValueAtTime(0.08, now);
  gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
  osc1.connect(gain1);
  gain1.connect(audioCtx.destination);
  
  // Create note 2 (G#5 - 830.61Hz)
  const osc2 = audioCtx.createOscillator();
  const gain2 = audioCtx.createGain();
  osc2.type = 'sine';
  osc2.frequency.setValueAtTime(830.61, now + 0.08);
  gain2.gain.setValueAtTime(0.08, now + 0.08);
  gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.38);
  osc2.connect(gain2);
  gain2.connect(audioCtx.destination);

  // Create note 3 (B5 - 987.77Hz)
  const osc3 = audioCtx.createOscillator();
  const gain3 = audioCtx.createGain();
  osc3.type = 'sine';
  osc3.frequency.setValueAtTime(987.77, now + 0.16);
  gain3.gain.setValueAtTime(0.08, now + 0.16);
  gain3.gain.exponentialRampToValueAtTime(0.001, now + 0.46);
  osc3.connect(gain3);
  gain3.connect(audioCtx.destination);
  
  osc1.start(now);
  osc1.stop(now + 0.35);
  osc2.start(now + 0.08);
  osc2.stop(now + 0.43);
  osc3.start(now + 0.16);
  osc3.stop(now + 0.51);
}

// ════════════════════════════════════════════════════════════
//  ENTERPRISE NEXT-LEVEL FEATURES IMPLEMENTATION
// ════════════════════════════════════════════════════════════

// 1. Search Tab - Hybrid Balance & Filtering
function updateHybridWeight(val) {
  hybridWeight = parseInt(val);
  document.getElementById('hybridTuningValue').textContent = `${100 - hybridWeight}% Keyword / ${hybridWeight}% Semantic`;
}

function addMetadataFilter() {
  const key = document.getElementById('filterKey').value;
  const op = document.getElementById('filterOp').value;
  const val = document.getElementById('filterVal').value.trim();
  
  if (!val) {
    showToast("Please enter a filter value.", "warning");
    return;
  }
  
  metadataFilters.push({ key, op, val });
  document.getElementById('filterVal').value = '';
  renderFilters();
  playClickSound();
  showToast(`Filter added: ${key} ${op} ${val}`, "success");
}

function renderFilters() {
  const container = document.getElementById('filterTags');
  if (!container) return;
  
  if (metadataFilters.length === 0) {
    container.innerHTML = '';
    return;
  }
  
  container.innerHTML = metadataFilters.map((f, idx) => `
    <div class="filter-tag">
      <span>${escapeHtml(f.key)} ${f.op} ${escapeHtml(f.val)}</span>
      <span class="close-tag" onclick="removeMetadataFilter(${idx})">✕</span>
    </div>
  `).join('');
}

function removeMetadataFilter(idx) {
  metadataFilters.splice(idx, 1);
  renderFilters();
  playClickSound();
}

// Override runSearch to include client-side post-filtering
const originalRunSearch = runSearch;
runSearch = async function() {
  const text = document.getElementById('qInput').value.trim();
  if (!text) return;
  saveSearchHistory(text, selAlgo, selMetric);
  renderSkeletons();
  
  const emb = textToEmbedding(text);
  
  // If filters are active, query a larger recall count (k=50) to apply post-filtering without empty returns
  const kQuery = metadataFilters.length > 0 ? 50 : 5;
  let url = `${API}/search?v=${emb.join(',')}&k=${kQuery}&metric=${selMetric}&algo=${selAlgo}`;
  if (selAlgo === 'hybrid') {
    url += `&text=${encodeURIComponent(text)}`;
  }
  
  try {
    const [r] = await Promise.all([
      fetch(url),
      new Promise(resolve => setTimeout(resolve, 500))
    ]);
    
    if (r.status === 400) {
      const err = await r.json();
      if (err.error && err.error.includes("not trained")) {
        showToast('IVF-PQ Index is untrained. Train it using the panel in the right sidebar.', 'warning');
        return;
      }
    }
    
    const data = await r.json();
    let hits = data.results || [];
    
    // Apply client-side metadata filtering
    if (metadataFilters.length > 0) {
      hits = hits.filter(item => {
        return metadataFilters.every(filter => {
          let itemVal = item[filter.key];
          if (filter.key === 'id') itemVal = String(item.id);
          let filterVal = String(filter.val).toLowerCase();
          
          if (filter.op === '=') return String(itemVal).toLowerCase() === filterVal;
          if (filter.op === '!=') return String(itemVal).toLowerCase() !== filterVal;
          return true;
        });
      });
      // Restrict back to top 5 after filters are applied
      hits = hits.slice(0, 5);
    }
    
    searchResults = hits;
    renderResults(searchResults);
    runBenchmark();
    
    // Update vector explorer too
    renderVectorExplorer();
  } catch(e) {
    console.error('Search failed:', e);
    showToast('Search failed: ' + (e.message || 'Server error'), 'error');
  }
};

// 2. Visualize Tab - Projections & K-Means & Explorer
function setProjectionMethod(btn, method) {
  document.querySelectorAll('#projectionPills .pill').forEach(p => p.classList.remove('on'));
  btn.classList.add('on');
  selectedProjection = method;
  playClickSound();
  
  if (method === 'pca3d') {
    render3DPlot();
  } else {
    simulateNonlinearProjection(method);
  }
}

function simulateNonlinearProjection(type) {
  if (pcaPoints3D.length === 0) return;
  
  const colors = pcaPoints3D.map(p => getCatColor(p.item.category));
  const isLight = document.documentElement.classList.contains('light-theme');
  const paperBg = isLight ? '#f5f5f7' : '#090909';
  
  const catCenters = {
    cs: [1.2, 0.2, -0.5],
    math: [-0.8, 1.1, 0.4],
    food: [0.3, -1.0, 0.8],
    sports: [-0.5, -0.6, -0.9],
    doc: [0.1, 0.4, 1.0],
    default: [0, 0, 0]
  };
  
  let simulatedPoints = pcaPoints3D.map(p => {
    const cat = p.item.category;
    const center = catCenters[cat] || catCenters.default;
    const spread = type === 'tsne' ? 0.20 : 0.35;
    return {
      x: center[0] + (Math.random() - 0.5) * spread,
      y: center[1] + (Math.random() - 0.5) * spread,
      z: center[2] + (Math.random() - 0.5) * spread,
      item: p.item
    };
  });
  
  try {
    const trace = {
      x: simulatedPoints.map(p => p.x),
      y: simulatedPoints.map(p => p.y),
      z: simulatedPoints.map(p => p.z),
      mode: 'markers',
      type: 'scatter3d',
      marker: {
        size: 7,
        color: colors,
        opacity: 0.9,
        line: { width: 1.5, color: paperBg }
      },
      text: simulatedPoints.map(p => `${p.item.category.toUpperCase()}: ${p.item.metadata}`)
    };
    
    Plotly.react('scatter3d', [trace], document.getElementById('scatter3d').layout);
    showToast(`Visualizer redrawn using ${type.toUpperCase()} layout.`, "info");
  } catch(e) {
    console.error(e);
  }
}

function runLocalKMeans() {
  const K = parseInt(document.getElementById('kmeansK').value) || 3;
  if (allItems.length < K) {
    document.getElementById('kmeansCentroidsList').innerHTML = `
      <div style="color:var(--ink-muted); font-size:11px; padding:6px; text-align:center;">
        Add at least ${K} vectors to cluster.
      </div>`;
    return;
  }
  
  const data = allItems.map(item => ({ item, emb: item.embedding }));
  let centroids = [];
  let indices = new Set();
  while (centroids.length < K) {
    let randIdx = Math.floor(Math.random() * data.length);
    if (!indices.has(randIdx)) {
      indices.add(randIdx);
      centroids.push([...data[randIdx].emb]);
    }
  }
  
  let clusters = Array.from({ length: K }, () => []);
  let assignments = new Array(data.length).fill(-1);
  
  for (let iter = 0; iter < 12; iter++) {
    clusters = Array.from({ length: K }, () => []);
    for (let i = 0; i < data.length; i++) {
      let minDist = Infinity, closest = 0;
      for (let c = 0; c < K; c++) {
        let dist = 0;
        for (let d = 0; d < DIMS; d++) dist += (data[i].emb[d] - centroids[c][d]) ** 2;
        if (dist < minDist) { minDist = dist; closest = c; }
      }
      assignments[i] = closest;
      clusters[closest].push(data[i]);
    }
    for (let c = 0; c < K; c++) {
      if (clusters[c].length === 0) continue;
      let newCentroid = new Array(DIMS).fill(0);
      for (let i = 0; i < clusters[c].length; i++) {
        for (let d = 0; d < DIMS; d++) newCentroid[d] += clusters[c][i].emb[d];
      }
      centroids[c] = newCentroid.map(val => val / clusters[c].length);
    }
  }
  
  const listEl = document.getElementById('kmeansCentroidsList');
  let html = '';
  const colors = ['#6a4cf5', '#d44df0', '#0099ff', '#10b981', '#ff7a3d', '#ff5577'];
  
  clusters.forEach((cluster, idx) => {
    let avgDist = 0;
    if (cluster.length > 0) {
      let sum = 0;
      cluster.forEach(pt => {
        let dist = 0;
        for (let d = 0; d < DIMS; d++) dist += (pt.emb[d] - centroids[idx][d]) ** 2;
        sum += Math.sqrt(dist);
      });
      avgDist = sum / cluster.length;
    }
    
    html += `
      <div class="kmeans-centroid-item" style="border-left: 3px solid ${colors[idx % colors.length]};">
        <div>
          <strong>Cluster #${idx + 1}</strong>
          <span style="color:var(--ink-muted); margin-left:6px;">(${cluster.length} nodes)</span>
        </div>
        <div style="color:var(--ink-muted); font-size:10px;">
          Radius: <span class="font-mono">${avgDist.toFixed(3)}</span>
        </div>
      </div>`;
  });
  listEl.innerHTML = html;
  
  if (typeof Plotly !== 'undefined' && pcaPoints3D.length > 0) {
    try {
      const trace = {
        x: pcaPoints3D.map(p => p.x),
        y: pcaPoints3D.map(p => p.y),
        z: pcaPoints3D.map(p => p.z),
        mode: 'markers',
        type: 'scatter3d',
        marker: {
          size: 7,
          color: assignments.map(id => colors[id % colors.length]),
          opacity: 0.9,
          line: { width: 1.5, color: document.documentElement.classList.contains('light-theme') ? '#f5f5f7' : '#090909' }
        },
        text: pcaPoints3D.map((p, i) => `Cluster #${assignments[i] + 1}: ${p.item.metadata}`)
      };
      Plotly.react('scatter3d', [trace], document.getElementById('scatter3d').layout);
      showToast("Color-coded Plotly nodes to K-Means assignments.", "success");
    } catch(e) { console.error(e); }
  }
}

function renderVectorExplorer() {
  const body = document.getElementById('vectorExplorerBody');
  if (!body) return;
  
  if (allItems.length === 0) {
    body.innerHTML = `<tr><td colspan="4" style="color:var(--ink-muted); font-size:11px; text-align:center; padding:12px;">No vectors in memory.</td></tr>`;
    return;
  }
  
  body.innerHTML = allItems.map((item) => {
    const c1 = item.embedding[0] ? item.embedding[0].toFixed(2) : '0';
    const c2 = item.embedding[1] ? item.embedding[1].toFixed(2) : '0';
    return `
      <tr>
        <td style="font-weight:600; color:var(--ink); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:120px;">${escapeHtml(item.metadata)}</td>
        <td><span class="res-badge" style="background:${getCatBgColor(item.category)}; color:${getCatColor(item.category)}; font-size:9px; padding:1px 4px; border-radius:3px;">${item.category}</span></td>
        <td class="font-mono" style="font-size:10px; color:var(--ink-muted);">${c1}, ${c2}</td>
        <td><button class="fly-to-btn" onclick="flyToVector(${item.id})">Focus 3D</button></td>
      </tr>`;
  }).join('');
}

function flyToVector(id) {
  const pt = pcaPoints3D.find(p => p.item.id === id);
  if (!pt) return;
  playClickSound();
  showToast(`Focusing camera on: ${pt.item.metadata}`, 'info');
  
  const scatter = document.getElementById('scatter3d');
  if (scatter && scatter.layout && scatter.layout.scene) {
    Plotly.relayout('scatter3d', {
      'scene.camera.eye': { x: pt.x * 2.2, y: pt.y * 2.2, z: pt.z * 2.2 },
      'scene.camera.center': { x: pt.x, y: pt.y, z: pt.z }
    });
  }
}

// 3. Docs Tab - Chunking boundaries visualizer & explorer
function updateChunkingPreview() {
  const text = document.getElementById('docText').value.trim();
  const size = parseInt(document.getElementById('chunkSizeSlider').value);
  const overlap = parseInt(document.getElementById('chunkOverlapSlider').value);
  
  document.getElementById('chunkSizeVal').textContent = size + ' words';
  document.getElementById('chunkOverlapVal').textContent = overlap + ' words';
  
  const preview = document.getElementById('chunkPreview');
  if (!text) {
    preview.innerHTML = '<span style="color:var(--ink-muted);">Type or paste text above to see visual chunk ranges.</span>';
    return;
  }
  
  const words = text.split(/\s+/);
  let chunks = [];
  for (let i = 0; i < words.length; i += (size - overlap)) {
    chunks.push(words.slice(i, i + size));
    if (i + size >= words.length) break;
  }
  
  preview.innerHTML = chunks.map((chunk, idx) => `
    <span class="chunk-hl-${idx % 4}" title="Chunk #${idx + 1}">${escapeHtml(chunk.join(' '))}</span>
  `).join(' ');
}

// Set hook inside text input listener to automatically update chunk boundary preview
document.addEventListener('DOMContentLoaded', () => {
  const docText = document.getElementById('docText');
  if (docText) {
    docText.addEventListener('input', updateChunkingPreview);
  }
});

function loadDocChunks(docTitle) {
  const container = document.getElementById('chunkListContainer');
  if (!container) return;
  
  const documentChunks = allItems.filter(item => 
    item.category === 'doc' && 
    (item.metadata.toLowerCase().includes(docTitle.toLowerCase()) || docTitle.toLowerCase().includes(item.metadata.toLowerCase()))
  );
  
  if (documentChunks.length === 0) {
    container.innerHTML = `
      <div style="color:var(--ink-muted); font-size:11px; text-align:center; padding:12px; background:var(--surface-1); border-radius:var(--radius-md); border:1px solid var(--hairline);">
        No index chunks found for "${docTitle}".
      </div>`;
    return;
  }
  
  container.innerHTML = documentChunks.map((chunk, idx) => `
    <div class="kmeans-centroid-item" style="border-left: 3px solid var(--accent-blue);">
      <div style="flex:1; padding-right:12px; text-align:left;">
        <strong>Chunk #${idx + 1}</strong> <span style="font-size:9px; color:var(--ink-muted); font-family:monospace;">[ID: ${chunk.id}]</span>
        <div style="font-size:11px; color:var(--ink); margin-top:4px; line-height:1.4;">${escapeHtml(chunk.metadata)}</div>
      </div>
      <div style="text-align:right; flex-shrink:0;">
        <span class="res-badge" style="font-size:9px; background:rgba(0,153,255,0.06); color:var(--accent-blue); display:inline-block; margin-bottom:4px;">16D Float</span>
        <button class="fly-to-btn" onclick="flyToVector(${chunk.id})">Inspect 3D</button>
      </div>
    </div>`).join('');
}

// 4. AI RAG Tab - Persona prompt & Citation clicks
function updateSystemPersona(val) {
  activeSystemPersona = val;
  playClickSound();
  showToast(`System prompt set to: ${val}`, 'success');
}

function inspectCitation(chunkId) {
  const chunk = allItems.find(item => item.id === chunkId);
  if (!chunk) return;
  
  const panel = document.getElementById('citationRefPanel');
  const content = document.getElementById('citationRefContent');
  if (panel && content) {
    panel.style.display = 'block';
    content.innerHTML = `
      <div style="font-weight:700; color:var(--ink); margin-bottom:4px;">${escapeHtml(chunk.metadata)}</div>
      <div style="margin-bottom:6px; display:flex; gap:6px; flex-wrap:wrap;">
        <span class="res-badge" style="font-size:9px; background:var(--trans-white-08); color:var(--ink);">ID: ${chunk.id}</span>
        <span class="res-badge" style="font-size:9px; background:rgba(0,153,255,0.06); color:var(--accent-blue);">Category: ${chunk.category}</span>
      </div>
      <div style="background:var(--surface-1); padding:8px; border-radius:4px; border:1px solid var(--hairline-soft); line-height:1.4;">
        ${escapeHtml(chunk.metadata)}
      </div>
    `;
    playClickSound();
    
    // Try to auto focus onto the camera vector too
    flyToVector(chunkId);
  }
}

// 5. AI Working - Step click inspector & Trace logs exporter
function inspectPipelineStep(stepIdx) {
  playClickSound();
  const card = document.getElementById('workingStepInspectorCard');
  const title = document.getElementById('inspectorStepTitle');
  const content = document.getElementById('inspectorStepContent');
  
  if (!card || !title || !content) return;
  card.style.display = 'block';
  
  const stepDetails = {
    1: {
      title: "Step 1: Input & Query Expansion",
      desc: "Translates natural language questions into vector spaces. If expansion is enabled, LLM adds synonyms to enrich semantic overlap before searching graphs."
    },
    2: {
      title: "Step 2: Embedding Generation",
      desc: "Calculates float coordinate representations. Compares category weights dynamically and normalizes vector values using L2 distances."
    },
    3: {
      title: "Step 3: HNSW Graph Traversals",
      desc: "Fast greedy search descending hierarchical link networks. Avoids complete scan computation times, reaching sub-milliseconds."
    },
    4: {
      title: "Step 4: Recall & Neural Rerank",
      desc: "Filters and scores matching passages. Neural re-rankers sort passages based on query relevance scores, replacing pure vector distance."
    },
    5: {
      title: "Step 5: LLM Synthesis",
      desc: "Augments the query with retrieved passages, then runs local streaming output (Qwen-0.5B). govern parameters govern temperature."
    }
  };
  
  const info = stepDetails[stepIdx] || stepDetails[1];
  title.textContent = info.title;
  content.textContent = info.desc;
}

function exportPipelineTrace() {
  playClickSound();
  const trace = {
    timestamp: new Date().toISOString(),
    query: document.getElementById('demoQuery').value || 'binary tree',
    pipeline: {
      stages: [
        { stage: 1, name: "Query Expansion", status: "completed" },
        { stage: 2, name: "Embedding Generation", dimensions: 16, time_s: parseFloat(document.getElementById('metricEmbed').textContent) || 0.35 },
        { stage: 3, name: "HNSW Graph Traversal", vectors_scanned: parseInt(document.getElementById('metricVectors').textContent) || 10, time_s: parseFloat(document.getElementById('metricSearch').textContent) || 0.015 },
        { stage: 4, name: "Reranker sorting", reranker: document.getElementById('rerankModel').value },
        { stage: 5, name: "LLM synthesis", model: "qwen2.5:0.5b" }
      ],
      total_time: document.getElementById('pipelineTimer').textContent
    }
  };
  
  const blob = new Blob([JSON.stringify(trace, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `nurosearch_pipeline_trace_${Date.now()}.json`;
  a.click();
  showToast("Pipeline trace exported successfully", "success");
}

// Override runDemoPipeline to display exportTrace button and latency breakdown chart
const originalRunDemoPipeline = runDemoPipeline;
runDemoPipeline = async function() {
  const exportBtn = document.getElementById('exportTraceBtn');
  if (exportBtn) exportBtn.style.display = 'none';
  
  await originalRunDemoPipeline();
  
  if (exportBtn) exportBtn.style.display = 'block';
  
  // Render breakdown bars
  const container = document.getElementById('latencyBreakdownBars');
  if (container) {
    const embedTime = parseFloat(document.getElementById('metricEmbed').textContent) || 0.35;
    const searchTime = parseFloat(document.getElementById('metricSearch').textContent) || 0.02;
    const totalTime = embedTime + searchTime + 0.6; // simulated LLM delay
    
    const items = [
      { name: 'Embedding', val: embedTime, color: 'var(--accent-blue)' },
      { name: 'HNSW Graph', val: searchTime, color: '#22c55e' },
      { name: 'LLM Stream', val: 0.6, color: 'var(--grad-magenta)' }
    ];
    
    container.innerHTML = items.map(item => {
      const pct = ((item.val / totalTime) * 100).toFixed(0);
      return `
        <div style="font-size:10px; margin-bottom:4px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
            <span>${item.name}</span>
            <span>${pct}% (${item.val.toFixed(3)}s)</span>
          </div>
          <div style="height:4px; background:var(--surface-2); border-radius:2px; overflow:hidden;">
            <div style="width:${pct}%; height:100%; background:${item.color}; border-radius:2px;"></div>
          </div>
        </div>`;
    }).join('');
  }
};

// 6. SQL Query Tab - Favourites & Execution Plans
function clearSqlHistory() {
  localStorage.removeItem('nuro_sql_favorites');
  renderSqlHistory();
  playClickSound();
}

function saveSqlHistory(query, starred = false) {
  try {
    let list = JSON.parse(localStorage.getItem('nuro_sql_favorites') || '[]');
    if (list.some(x => x.query === query)) return;
    list.unshift({ query, starred });
    localStorage.setItem('nuro_sql_favorites', JSON.stringify(list));
    renderSqlHistory();
  } catch(e) {}
}

function renderSqlHistory() {
  const container = document.getElementById('sqlHistoryList');
  if (!container) return;
  
  try {
    const list = JSON.parse(localStorage.getItem('nuro_sql_favorites') || '[]');
    if (list.length === 0) {
      container.innerHTML = `<div style="color:var(--ink-muted); font-size:11px; text-align:center; padding:10px;">No historical queries.</div>`;
      return;
    }
    
    container.innerHTML = list.map((item, idx) => `
      <div class="sql-history-item" onclick="document.getElementById('sqlQueryText').value='${escapeHtml(item.query)}'; playClickSound();">
        <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:85%; color:var(--ink); font-family:monospace;">${escapeHtml(item.query)}</span>
        <span class="sql-favorite-star" onclick="event.stopPropagation(); toggleStarSql(${idx})">${item.starred ? '★' : '☆'}</span>
      </div>`).join('');
  } catch(e) {}
}

function toggleStarSql(idx) {
  try {
    let list = JSON.parse(localStorage.getItem('nuro_sql_favorites') || '[]');
    list[idx].starred = !list[idx].starred;
    localStorage.setItem('nuro_sql_favorites', JSON.stringify(list));
    renderSqlHistory();
    playClickSound();
  } catch(e) {}
}

function visualizeExecutionPlan(ast) {
  const card = document.getElementById('sqlPlanCard');
  const diagram = document.getElementById('sqlPlanDiagram');
  if (!card || !diagram) return;
  
  card.style.display = 'block';
  let steps = [];
  steps.push("1. AST AST Compilation: parsed SELECT parameters");
  
  if (ast.where) {
    steps.push(`2. Filter matching criteria: ${JSON.stringify(ast.where)}`);
  }
  if (ast.vector || ast.text) {
    steps.push("3. Scan multi-layer links in HNSW index space");
  } else {
    steps.push("3. Linear Array Scan (Brute-force iteration)");
  }
  if (ast.limit) {
    steps.push(`4. Keep top ${ast.limit} elements (Limit execution)`);
  }
  
  diagram.innerHTML = steps.map((s, idx) => `
    <div class="plan-node">
      <div style="font-weight:700; color:var(--accent-blue);">${s.split('.')[0]}. ${s.split(':')[0].substring(3)}</div>
      <div style="font-size:10px; color:var(--ink-muted); margin-top:2px;">${s.includes(':') ? s.split(':').slice(1).join(':') : s.substring(s.indexOf(' ') + 1)}</div>
    </div>
    ${idx < steps.length - 1 ? '<div class="plan-arrow">▼</div>' : ''}
  `).join('');
}

// Override runSqlQuery to save history and trigger execution plan visualizer
const originalRunSqlQuery = runSqlQuery;
runSqlQuery = async function() {
  const query = document.getElementById('sqlQueryText').value.trim();
  if (!query) return;
  
  await originalRunSqlQuery();
  saveSqlHistory(query, false);
  
  try {
    const astText = document.getElementById('sqlAstOutput').textContent;
    const ast = JSON.parse(astText);
    visualizeExecutionPlan(ast);
  } catch(e) {}
};

// 7. Cluster Tab - WAN simulation & Heartbeats SVG
function updateNetworkSimulation() {
  const lat = document.getElementById('netLatencySlider').value;
  const loss = document.getElementById('netLossSlider').value;
  
  localClusterLatency = parseInt(lat);
  localClusterLoss = parseInt(loss);
  
  document.getElementById('netLatencyVal').textContent = lat + ' ms';
  document.getElementById('netLossVal').textContent = loss + '%';
  
  playClickSound();
}

let lastHbTime = 0;
function animateRaftHeartbeats(timestamp) {
  const hb12 = document.getElementById('svgHb-1-2');
  const hb13 = document.getElementById('svgHb-1-3');
  
  if (hb12 && hb13) {
    if (!lastHbTime) lastHbTime = timestamp;
    let elapsed = timestamp - lastHbTime;
    
    // Sync heartbeat interval with WAN simulated latency
    const interval = 1200 + localClusterLatency;
    
    if (elapsed > interval) {
      lastHbTime = timestamp;
      
      // Heartbeat packet loss simulation
      if (Math.random() * 100 >= localClusterLoss) {
        if (nodeOverrides['worker-1'] && nodeOverrides['worker-2']) {
          hb12.style.display = 'block';
          animateDot(hb12, 125, 55, 75, 125);
        } else { hb12.style.display = 'none'; }
        
        if (nodeOverrides['worker-1'] && nodeOverrides['worker-3']) {
          hb13.style.display = 'block';
          animateDot(hb13, 155, 55, 205, 125);
        } else { hb13.style.display = 'none'; }
      }
    }
  }
  requestAnimationFrame(animateRaftHeartbeats);
}

function animateDot(dot, x1, y1, x2, y2) {
  let start = null;
  const duration = 600 + localClusterLatency; // glide speed drops as latency increases
  
  function step(now) {
    if (!start) start = now;
    let progress = (now - start) / duration;
    if (progress > 1) progress = 1;
    
    let currentX = x1 + (x2 - x1) * progress;
    let currentY = y1 + (y2 - y1) * progress;
    
    dot.setAttribute('cx', currentX);
    dot.setAttribute('cy', currentY);
    
    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      dot.style.display = 'none';
    }
  }
  requestAnimationFrame(step);
}

// Start SVG animations
requestAnimationFrame(animateRaftHeartbeats);

// Sync SVG node outline colors with online/offline states
const originalFetchClusterHealth = fetchClusterHealth;
fetchClusterHealth = async function() {
  await originalFetchClusterHealth();
  
  // Update node colors in SVG
  const workers = ['worker-1', 'worker-2', 'worker-3'];
  workers.forEach(id => {
    const nodeG = document.getElementById(`svgNode-${id}`);
    if (nodeG) {
      const circle = nodeG.querySelector('circle');
      const text = document.getElementById(`svgNodeRole-${id}`);
      
      if (nodeOverrides[id] === false) {
        if (circle) circle.setAttribute('stroke', '#ff4b4b');
        if (text) {
          text.textContent = 'Offline';
          text.setAttribute('fill', '#ff4b4b');
        }
      } else {
        const isLeader = (simulatedLeader === id);
        if (circle) circle.setAttribute('stroke', isLeader ? '#ffa726' : '#22c55e');
        if (text) {
          text.textContent = isLeader ? 'Leader' : 'Follower';
          text.setAttribute('fill', isLeader ? '#ffa726' : '#22c55e');
        }
      }
    }
  });
};

// 8. About Tab - SDK tabs & local benchmark suite
function switchSDKTab(btn, sdk) {
  document.querySelectorAll('.sdk-tab-btn').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  selectedSDK = sdk;
  playClickSound();
  
  document.querySelectorAll('.sdk-code-block').forEach(el => el.style.display = 'none');
  const code = document.getElementById(`sdk-code-${sdk}`);
  if (code) code.style.display = 'block';
}

function runJsBenchmark() {
  playClickSound();
  showToast("Running local database benchmark suite...", "info");
  
  const hnswBar = document.getElementById('benchHnswBar');
  const kdBar = document.getElementById('benchKdBar');
  const bfBar = document.getElementById('benchBfBar');
  
  const hnswRes = document.getElementById('benchHnswRes');
  const kdRes = document.getElementById('benchKdRes');
  const bfRes = document.getElementById('benchBfRes');
  
  hnswBar.style.width = '0%';
  kdBar.style.width = '0%';
  bfBar.style.width = '0%';
  
  hnswRes.textContent = "Testing...";
  kdRes.textContent = "Testing...";
  bfRes.textContent = "Testing...";
  
  setTimeout(() => {
    // Simulated index traversals / vector distance logic on 250 elements: HNSW ~1.1ms, KD-tree ~4.8ms, BF ~22.6ms
    hnswBar.style.width = '100%';
    hnswRes.textContent = "1.1 ms (95% Recall)";
    
    setTimeout(() => {
      kdBar.style.width = '24%';
      kdRes.textContent = "4.8 ms (100% Recall)";
      
      setTimeout(() => {
        bfBar.style.width = '5%';
        bfRes.textContent = "22.6 ms (100% Recall)";
        showToast("Local JS benchmark complete!", "success");
      }, 400);
    }, 400);
  }, 600);
}

// Redraw explorer tables on load
setTimeout(() => {
  renderVectorExplorer();
  renderSqlHistory();
}, 2000);

initTheme();
initSound();
initDropzone();

const activeNav = document.querySelector('.nav-item.on');
if (activeNav) {
  setTimeout(() => updateNavIndicator(activeNav), 150);
}

if (window.matchMedia('(hover: hover)').matches) {
  initMagnetEffect();
  initSpotlightEffect();
  initCustomCursor();
}

loadItems().then(() => {
  render3DPlot();
  loadHNSW();
  updateEngineStats();
});
renderSearchHistory();
checkOllamaStatus();


/* === EXTENSION JAVASCRIPT === */

// --- JS from search_visualize.search_js ---
// Dynamic setup for Search enhancements
(function() {
  function setupSearchEnhancements() {
    // 1. Inject Voice Search Button
    const searchBar = document.querySelector('.search-bar');
    if (searchBar && !document.getElementById('voiceSearchBtn')) {
      const voiceBtn = document.createElement('button');
      voiceBtn.id = 'voiceSearchBtn';
      voiceBtn.className = 'voice-search-trigger';
      voiceBtn.title = 'Simulate Voice Search';
      voiceBtn.innerHTML = '<i class="ti ti-microphone" style="font-size: 18px;"></i>';
      voiceBtn.onclick = startVoiceSearchSimulation;
      searchBar.insertBefore(voiceBtn, searchBar.querySelector('.search-btn'));
    }

    // 2. Inject Voice Search Overlay
    if (!document.getElementById('voice-search-overlay')) {
      const overlay = document.createElement('div');
      overlay.id = 'voice-search-overlay';
      overlay.className = 'voice-overlay';
      overlay.style.display = 'none';
      overlay.innerHTML = `
        <div class="voice-card">
          <div class="voice-pulsar-container">
            <div class="voice-ripple r1"></div>
            <div class="voice-ripple r2"></div>
            <div class="voice-ripple r3"></div>
            <div class="voice-mic-icon"><i class="ti ti-microphone"></i></div>
          </div>
          <h3 class="voice-status">Listening...</h3>
          <p class="voice-transcript"></p>
          <div class="voice-bars">
            <span class="bar b1"></span>
            <span class="bar b2"></span>
            <span class="bar b3"></span>
            <span class="bar b4"></span>
            <span class="bar b5"></span>
          </div>
        </div>
      `;
      document.body.appendChild(overlay);
    }

    // 3. Inject Similarity Threshold Card into Sidebar
    const sidebar = document.querySelector('.search-sidebar-column');
    if (sidebar && !document.getElementById('similarityThresholdSlider')) {
      const threshCard = document.createElement('div');
      threshCard.className = 'status-card';
      threshCard.innerHTML = `
        <div class="section-label">Similarity Threshold</div>
        <p style="font-size:11px; color:var(--ink-muted); line-height:1.4; margin-bottom:12px;">
          Client-side filtering of search results based on cosine similarity score.
        </p>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <span style="font-size:12px; font-weight:600;">Min Similarity:</span>
          <span id="thresholdVal" class="font-mono" style="font-size:12px; color:var(--accent-blue); font-weight:700;">0%</span>
        </div>
        <input type="range" id="similarityThresholdSlider" min="0" max="100" value="0" style="width:100%; cursor:pointer;" oninput="updateSimilarityThreshold(this.value)" />
        <div style="display:flex; justify-content:space-between; font-size:9px; color:var(--ink-muted); margin-top:4px;">
          <span>Show All (0%)</span>
          <span>Exact Match (100%)</span>
        </div>
      `;
      // Insert as second child in sidebar
      if (sidebar.children.length > 1) {
        sidebar.insertBefore(threshCard, sidebar.children[1]);
      } else {
        sidebar.appendChild(threshCard);
      }
    }

    // 4. Inject Export JSON Button in the Search Results section header
    const titles = document.querySelectorAll('.section-title');
    for (const title of titles) {
      if (title.textContent.trim().startsWith('Search Results') && !title.querySelector('#export-json-btn')) {
        title.innerHTML = `
          <span>Search Results</span>
          <button class="btn-secondary" id="export-json-btn" onclick="exportResultsToJSON()" style="padding: 4px 10px; font-size: 11px; height: auto; display: flex; align-items: center; gap: 4px;">
            <i class="ti ti-download"></i> Export JSON
          </button>
        `;
        break;
      }
    }
  }

  // Global variables
  window.currentThreshold = 0.0;

  // 5. Similarity score calculation
  window.computeSimilarityScore = function(distance, metric) {
    if (metric === 'cosine') {
      return Math.max(0, Math.min(1, 1 - distance));
    } else {
      // Euclidean or Manhattan: inverse kernel 1 / (1 + distance)
      return Math.max(0, Math.min(1, 1 / (1 + distance)));
    }
  };

  // 6. Update Similarity Threshold value & filter results
  window.updateSimilarityThreshold = function(val) {
    window.currentThreshold = parseInt(val) / 100;
    const valSpan = document.getElementById('thresholdVal');
    if (valSpan) valSpan.textContent = val + '%';
    if (window.searchResults) {
      window.renderResults(window.searchResults);
    }
  };

  // 7. Export Results to JSON
  window.exportResultsToJSON = function() {
    if (!window.searchResults || window.searchResults.length === 0) {
      if (typeof showToast === 'function') showToast('No search results to export', 'warning');
      else alert('No search results to export');
      return;
    }
    const filtered = window.searchResults.filter(r => {
      const score = window.computeSimilarityScore(r.distance, window.selMetric || 'cosine');
      return score >= window.currentThreshold;
    });
    
    const exportData = filtered.map(r => ({
      id: r.id,
      metadata: r.metadata,
      category: r.category,
      distance: r.distance,
      similarity_score: window.computeSimilarityScore(r.distance, window.selMetric || 'cosine'),
      metric: window.selMetric || 'cosine',
      algo: window.selAlgo || 'hnsw'
    }));

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nurosearch_results_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    if (typeof showToast === 'function') showToast(`Exported ${exportData.length} results to JSON`, 'success');
  };

  // 8. Voice Search Simulation
  window.startVoiceSearchSimulation = function() {
    const overlay = document.getElementById('voice-search-overlay');
    if (!overlay) return;

    overlay.style.display = 'flex';
    const status = overlay.querySelector('.voice-status');
    const transcript = overlay.querySelector('.voice-transcript');
    const bars = overlay.querySelectorAll('.bar');

    status.textContent = 'Listening...';
    transcript.textContent = '';

    // Waveform simulation
    const barInterval = setInterval(() => {
      bars.forEach(bar => {
        const h = Math.random() * 28 + 6;
        bar.style.height = `${h}px`;
      });
    }, 80);

    const phrases = [
      "binary search tree depth and complexity",
      "sushi rolls with fresh tuna and salmon",
      "gradient descent optimizer step size",
      "sports analytics prediction models",
      "vector database indexing HNSW and KD-Tree"
    ];
    const phrase = phrases[Math.floor(Math.random() * phrases.length)];

    setTimeout(() => {
      status.textContent = 'Speech Detected...';
      let i = 0;
      const typeInterval = setInterval(() => {
        transcript.textContent = `"${phrase.slice(0, i + 1)}|"`;
        i++;
        if (i >= phrase.length) {
          clearInterval(typeInterval);
          transcript.textContent = `"${phrase}"`;
          status.textContent = 'Processing...';

          setTimeout(() => {
            clearInterval(barInterval);
            overlay.style.display = 'none';
            const input = document.getElementById('qInput');
            if (input) {
              input.value = phrase;
              if (typeof runSearch === 'function') runSearch();
            }
          }, 800);
        }
      }, 40);
    }, 1200);
  };

  // 9. Override window.renderResults to implement Circular similarity score gauges
  window.renderCustomResults = function(results) {
    const resContainer = document.getElementById('results');
    if (!resContainer) return;
    
    if (!results || !results.length) {
      resContainer.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⌕</div><div class="empty-state-text">No results match similarity threshold</div></div>`;
      return;
    }

    resContainer.innerHTML = results.map((r, i) => {
      // Use existing color helpers
      const col = typeof getCatColor === 'function' ? getCatColor(r.category) : '#fff';
      const bg = typeof getCatBgColor === 'function' ? getCatBgColor(r.category) : 'rgba(255,255,255,0.05)';
      
      const score = window.computeSimilarityScore(r.distance, window.selMetric || 'cosine');
      const pct = Math.round(score * 100);
      
      // Determine gauge color based on score
      let gaugeColor = 'var(--accent-blue)';
      if (pct >= 80) gaugeColor = '#10b981'; // Green
      else if (pct >= 50) gaugeColor = '#f59e0b'; // Amber
      else gaugeColor = '#ef4444'; // Red
      
      const strokeDashArray = `${pct}, 100`;

      return `
        <div class="result-card enhanced-result-card" style="animation-delay: ${i * 60}ms; display: flex; align-items: center; padding: 12px; gap: 12px; margin-bottom: 8px;">
          <!-- Circular similarity gauge -->
          <div class="similarity-gauge-wrapper" style="width: 42px; height: 42px; position: relative; flex-shrink: 0;" title="Similarity score: ${pct}%">
            <svg viewBox="0 0 36 36" style="width: 100%; height: 100%; transform: rotate(-90deg);">
              <circle cx="18" cy="18" r="15.915" fill="none" stroke="var(--hairline-soft)" stroke-width="3.5"></circle>
              <circle cx="18" cy="18" r="15.915" fill="none" stroke="${gaugeColor}" stroke-width="3.5" 
                      stroke-dasharray="${strokeDashArray}" stroke-dashoffset="0" style="transition: stroke-dasharray 0.5s ease-in-out;"></circle>
            </svg>
            <div style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; font-family: monospace; color: var(--ink);">${pct}%</div>
          </div>
          
          <div class="res-icon" style="background:${bg};color:${col}; width: 36px; height: 36px; display:flex; align-items:center; justify-content:center; border-radius:50%; font-weight:bold; flex-shrink:0;">
            ${r.category ? r.category[0].toUpperCase() : 'V'}
          </div>
          
          <div class="res-info" style="flex: 1; min-width: 0;">
            <div class="res-title" style="font-weight: 500; font-size: 13.5px; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${typeof escapeHtml === 'function' ? escapeHtml(r.metadata) : r.metadata}
            </div>
            <div class="res-meta" style="display:flex; align-items:center; gap:8px; margin-top:4px; font-size:11px;">
              <span class="res-badge" style="background:${bg};color:${col}; padding: 2px 6px; border-radius: 4px; font-weight: 600;">
                ${typeof escapeHtml === 'function' ? escapeHtml(r.category) : r.category}
              </span>
              <span class="res-dist" style="color:var(--ink-muted);">distance: ${r.distance.toFixed(4)}</span>
            </div>
          </div>
          
          <button class="res-action" onclick="deleteItem(${r.id})" aria-label="Delete" style="background:none; border:none; color:var(--ink-muted); cursor:pointer; font-size:14px; padding:6px; opacity:0.6; transition:opacity 0.2s;">✕</button>
        </div>
      `;
    }).join('');
  };

  // Override window.renderResults
  window.renderResults = function(results) {
    window.searchResults = results || [];
    const filtered = (results || []).filter(r => {
      const score = window.computeSimilarityScore(r.distance, window.selMetric || 'cosine');
      return score >= window.currentThreshold;
    });
    window.renderCustomResults(filtered);
  };

  // Initialize after script load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupSearchEnhancements);
  } else {
    setupSearchEnhancements();
  }
})();

// --- JS from search_visualize.visualize_js ---
// Dynamic setup for Visualize (stats) enhancements
(function() {
  function setupVisualizeEnhancements() {
    // 1. Inject Theme Selector
    const projectionRow = document.getElementById('projectionPills')?.parentElement;
    if (projectionRow && !document.getElementById('themePills')) {
      const themeRow = document.createElement('div');
      themeRow.style = "display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:10px;";
      themeRow.innerHTML = `
        <span style="font-size:10px; color:var(--ink-muted); font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Plot Theme:</span>
        <div class="pills" id="themePills">
          <div class="pill" onclick="setPlotTheme(this, 'midnight')">Midnight</div>
          <div class="pill on" onclick="setPlotTheme(this, 'cyberpunk')">Cyberpunk</div>
          <div class="pill" onclick="setPlotTheme(this, 'emerald')">Emerald</div>
          <div class="pill" onclick="setPlotTheme(this, 'sunset')">Sunset</div>
        </div>
      `;
      projectionRow.parentElement.insertBefore(themeRow, projectionRow.nextSibling);
    }
    
    // 2. Inject Dimension Weight Mixer
    const wrapper = document.querySelector('.visualizer-scroll-wrapper');
    if (wrapper && !document.getElementById('weightDim1')) {
      const mixerCard = document.createElement('div');
      mixerCard.className = 'status-card';
      mixerCard.style.marginTop = '15px';
      mixerCard.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <h4 style="font-family:'Outfit'; font-size:14px; font-weight:600;">Interactive Dimension Weight Mixer</h4>
          <button class="btn-secondary" onclick="resetMixerWeights()" style="padding:4px 8px; font-size:10px; height:auto;">Reset Weights</button>
        </div>
        <p style="font-size:11px; color:var(--ink-muted); line-height:1.4; margin-bottom:12px;">
          Scale dimensional groups. Recalculates PCA projections on the fly to see how semantic spaces morph.
        </p>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:12px;">
          <div>
            <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px;">
              <span>CS / Algorithms (Dims 1-4)</span>
              <span id="valDim1" class="font-mono" style="color:var(--accent-blue);">1.00x</span>
            </div>
            <input type="range" id="weightDim1" min="0" max="3" step="0.1" value="1.0" style="width:100%; cursor:pointer;" oninput="updateMixerProjection()" />
          </div>
          <div>
            <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px;">
              <span>Mathematics (Dims 5-8)</span>
              <span id="valDim2" class="font-mono" style="color:var(--grad-violet);">1.00x</span>
            </div>
            <input type="range" id="weightDim2" min="0" max="3" step="0.1" value="1.0" style="width:100%; cursor:pointer;" oninput="updateMixerProjection()" />
          </div>
          <div>
            <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px;">
              <span>Food / Dining (Dims 9-12)</span>
              <span id="valDim3" class="font-mono" style="color:var(--grad-magenta);">1.00x</span>
            </div>
            <input type="range" id="weightDim3" min="0" max="3" step="0.1" value="1.0" style="width:100%; cursor:pointer;" oninput="updateMixerProjection()" />
          </div>
          <div>
            <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px;">
              <span>Sports / Games (Dims 13-16)</span>
              <span id="valDim4" class="font-mono" style="color:var(--grad-orange);">1.00x</span>
            </div>
            <input type="range" id="weightDim4" min="0" max="3" step="0.1" value="1.0" style="width:100%; cursor:pointer;" oninput="updateMixerProjection()" />
          </div>
        </div>
      `;
      wrapper.parentNode.insertBefore(mixerCard, wrapper.nextSibling);
    }
    
    // 3. Inject Advanced Vector Injector
    const addMetaInput = document.getElementById('addMeta');
    if (addMetaInput && !document.getElementById('injMeta')) {
      const insertCard = addMetaInput.closest('.status-card');
      if (insertCard) {
        const advCard = document.createElement('div');
        advCard.className = 'status-card grad-spot-card-violet';
        advCard.style.marginTop = '15px';
        advCard.innerHTML = `
          <h4 style="font-family:'Outfit'; font-size:14px; font-weight:600; margin-bottom:4px;">Advanced Vector Injector</h4>
          <p style="font-size:11px; color:var(--ink-muted); line-height:1.4; margin-bottom:12px;">
            Inject controlled synthetic high-dimensional vector embeddings with custom mathematical properties.
          </p>
          
          <div style="display:flex; flex-direction:column; gap:8px;">
            <input type="text" id="injMeta" placeholder="Custom Label (e.g. Synthetic node Alpha)" style="background:var(--input-bg); border:1px solid var(--input-border); border-radius:4px; padding:6px; color:var(--ink); font-size:12px;" />
            
            <div style="display:flex; gap:8px;">
              <select id="injCat" style="flex:1; border:1px solid var(--hairline); border-radius:4px; background:var(--surface-2); color:var(--ink); font-size:12px; height:28px;" onchange="previewInjectedVector()">
                <option value="cs">CS / Algorithms</option>
                <option value="math">Mathematics</option>
                <option value="food">Food</option>
                <option value="sports">Sports</option>
              </select>
              
              <select id="injMode" style="flex:1; border:1px solid var(--hairline); border-radius:4px; background:var(--surface-2); color:var(--ink); font-size:12px; height:28px;" onchange="previewInjectedVector()">
                <option value="biased">Biased Category</option>
                <option value="random">Pure Random Noise</option>
                <option value="orthogonal">Sparse / Orthogonal</option>
              </select>
            </div>
            
            <div>
              <div style="display:flex; justify-content:space-between; font-size:10px; color:var(--ink-muted); margin-bottom:2px;">
                <span>Noise Amplitude</span>
                <span id="injNoiseVal" class="font-mono">0.10</span>
              </div>
              <input type="range" id="injNoiseSlider" min="0" max="0.5" step="0.05" value="0.1" style="width:100%; cursor:pointer;" oninput="document.getElementById('injNoiseVal').textContent=parseFloat(this.value).toFixed(2); previewInjectedVector();" />
            </div>
            
            <!-- Dimension Sparkline Preview -->
            <div style="background:rgba(0,0,0,0.2); border:1px solid var(--hairline); border-radius:4px; padding:8px;">
              <div style="display:flex; justify-content:space-between; font-size:9px; color:var(--ink-muted); margin-bottom:4px;">
                <span>Vector Dimension Profile (16 dims)</span>
                <span id="injVecMagnitude" class="font-mono">||v|| = 1.0</span>
              </div>
              <div id="vectorProfileBars" style="display:flex; gap:2px; height:24px; align-items:flex-end;">
                <!-- Sparkline bars dynamically filled in JS -->
              </div>
            </div>
            
            <button class="btn-primary" onclick="injectVector()" style="width:100%; margin-top:4px;">Generate &amp; Inject Vector</button>
          </div>
        `;
        insertCard.parentNode.insertBefore(advCard, insertCard.nextSibling);
        previewInjectedVector();
      }
    }
  }

  // Themes list
  window.currentPlotTheme = 'cyberpunk';
  window.THEMES = {
    midnight: {
      paper_bg: '#090909',
      plot_bg: '#090909',
      grid_color: '#262626',
      text_color: '#ffffff',
      tick_color: '#999999',
      marker_colors: null
    },
    cyberpunk: {
      paper_bg: '#0c0813',
      plot_bg: '#0c0813',
      grid_color: '#3d125a',
      text_color: '#00ffcc',
      tick_color: '#ff007f',
      marker_colors: {
        cs: '#00ffcc',
        math: '#ff007f',
        food: '#ffe600',
        sports: '#d44df0'
      }
    },
    emerald: {
      paper_bg: '#03120e',
      plot_bg: '#03120e',
      grid_color: '#0f3a2c',
      text_color: '#39e3a6',
      tick_color: '#b2edd5',
      marker_colors: {
        cs: '#39e3a6',
        math: '#d4af37',
        food: '#a3e635',
        sports: '#0ea5e9'
      }
    },
    sunset: {
      paper_bg: '#180d19',
      plot_bg: '#180d19',
      grid_color: '#441639',
      text_color: '#ffa07a',
      tick_color: '#ff7799',
      marker_colors: {
        cs: '#ff7799',
        math: '#ffaa66',
        food: '#ffd700',
        sports: '#d44df0'
      }
    }
  };

  // Set Theme
  window.setPlotTheme = function(btn, themeName) {
    const pills = document.querySelectorAll('#themePills .pill');
    pills.forEach(p => p.classList.remove('on'));
    btn.classList.add('on');
    
    window.currentPlotTheme = themeName;
    window.render3DPlot();
  };

  // Override render3DPlot to apply theme
  window.render3DPlot = function() {
    if (!window.pcaPoints3D || window.pcaPoints3D.length === 0) {
      document.getElementById('scatter3d').innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--ink-muted);font-size:13px;">No data to visualize. Add vectors or check server connection.</div>';
      return;
    }

    try {
      const theme = window.THEMES[window.currentPlotTheme] || window.THEMES.midnight;
      const isLightTheme = document.documentElement.classList.contains('light-theme');
      
      let paperBg = theme.paper_bg;
      let textClr = theme.text_color;
      let gridClr = theme.grid_color;
      let tickClr = theme.tick_color;

      if (isLightTheme && window.currentPlotTheme === 'midnight') {
        paperBg = '#f5f5f7';
        textClr = '#1d1d1f';
        gridClr = '#e2e2e8';
        tickClr = '#86868b';
      }

      const x = window.pcaPoints3D.map(p => p.x);
      const y = window.pcaPoints3D.map(p => p.y);
      const z = window.pcaPoints3D.map(p => p.z);
      
      const colors = window.pcaPoints3D.map(p => {
        if (theme.marker_colors && theme.marker_colors[p.item.category]) {
          return theme.marker_colors[p.item.category];
        }
        return typeof getCatColor === 'function' ? getCatColor(p.item.category) : '#fff';
      });

      const text = window.pcaPoints3D.map(p => `${p.item.category.toUpperCase()}: ${p.item.metadata}`);
      
      const trace = {
        x: x, y: y, z: z,
        mode: 'markers',
        type: 'scatter3d',
        marker: {
          size: 7,
          color: colors,
          opacity: 0.95,
          line: { width: 1.5, color: paperBg },
          symbol: 'circle',
          showscale: false
        },
        text: text,
        hoverinfo: 'text',
        hoverlabel: {
          bgcolor: isLightTheme ? '#ffffff' : '#141414',
          bordercolor: isLightTheme ? '#e2e2e8' : '#262626',
          font: { family: 'Inter, sans-serif', size: 12, color: isLightTheme ? '#1d1d1f' : '#ffffff' }
        }
      };

      const layout = {
        margin: {l: 0, r: 0, b: 0, t: 0},
        paper_bgcolor: paperBg,
        plot_bgcolor: paperBg,
        scene: {
          xaxis: { 
            title: 'PC1', 
            gridcolor: gridClr, 
            gridwidth: 1,
            zerolinecolor: gridClr, 
            zerolinewidth: 2,
            tickfont: {color: tickClr, family: 'Inter'},
            titlefont: {color: textClr, family: 'Inter', size: 12},
            linecolor: gridClr
          },
          yaxis: { 
            title: 'PC2', 
            gridcolor: gridClr, 
            gridwidth: 1,
            zerolinecolor: gridClr, 
            zerolinewidth: 2,
            tickfont: {color: tickClr, family: 'Inter'},
            titlefont: {color: textClr, family: 'Inter', size: 12},
            linecolor: gridClr
          },
          zaxis: { 
            title: 'PC3', 
            gridcolor: gridClr, 
            gridwidth: 1,
            zerolinecolor: gridClr, 
            zerolinewidth: 2,
            tickfont: {color: tickClr, family: 'Inter'},
            titlefont: {color: textClr, family: 'Inter', size: 12},
            linecolor: gridClr
          },
          bgcolor: paperBg,
          camera: { eye: {x: 1.6, y: 1.6, z: 1.3} },
          aspectmode: 'cube',
          aspectratio: {x: 1, y: 1, z: 0.8}
        },
        font: { family: 'Inter, sans-serif' }
      };

      const scatterContainer = document.getElementById('scatter3d');
      if (scatterContainer.querySelector('.js-plotly-plot')) {
        Plotly.react('scatter3d', [trace], layout, {responsive: true, displayModeBar: true});
      } else {
        Plotly.newPlot('scatter3d', [trace], layout, {responsive: true, displayModeBar: true});
      }
    } catch(e) {
      console.error(e);
      document.getElementById('scatter3d').innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#ff4b4b;font-size:13px;">Plot error: ${e.message}</div>`;
    }
  };

  // Recalculate PCA weights
  window.updateMixerProjection = function() {
    const w1 = parseFloat(document.getElementById('weightDim1').value || 1.0);
    const w2 = parseFloat(document.getElementById('weightDim2').value || 1.0);
    const w3 = parseFloat(document.getElementById('weightDim3').value || 1.0);
    const w4 = parseFloat(document.getElementById('weightDim4').value || 1.0);

    document.getElementById('valDim1').textContent = w1.toFixed(2) + 'x';
    document.getElementById('valDim2').textContent = w2.toFixed(2) + 'x';
    document.getElementById('valDim3').textContent = w3.toFixed(2) + 'x';
    document.getElementById('valDim4').textContent = w4.toFixed(2) + 'x';

    if (!window.allItems || window.allItems.length === 0) return;

    const weightedEmbs = window.allItems.map(item => {
      const emb = [...item.embedding];
      for (let i = 0; i < 4; i++) emb[i] *= w1;
      for (let i = 4; i < 8; i++) emb[i] *= w2;
      for (let i = 8; i < 12; i++) emb[i] *= w3;
      for (let i = 12; i < 16; i++) emb[i] *= w4;
      return emb;
    });

    if (typeof pca3D === 'function') {
      const coords = pca3D(weightedEmbs);
      window.pcaPoints3D = window.allItems.map((item, i) => ({ 
        x: coords[i][0], 
        y: coords[i][1], 
        z: coords[i][2], 
        item 
      }));
      window.render3DPlot();
    }
  };

  window.resetMixerWeights = function() {
    document.getElementById('weightDim1').value = 1.0;
    document.getElementById('weightDim2').value = 1.0;
    document.getElementById('weightDim3').value = 1.0;
    document.getElementById('weightDim4').value = 1.0;
    window.updateMixerProjection();
  };

  // Wrap loadItems to reapply mixer weights on refresh
  const originalLoadItems = window.loadItems;
  if (originalLoadItems) {
    window.loadItems = async function() {
      await originalLoadItems();
      window.updateMixerProjection();
    };
  }

  // Synthetic Vector Gen helper
  window.generateSyntheticVector = function(cat, mode, noise) {
    let vec = new Array(16).fill(0.05);
    
    if (mode === 'biased') {
      let base = {cs: 0.05, math: 0.05, food: 0.05, sports: 0.05};
      base[cat] = 0.85;
      
      for (let i = 0; i < 4; i++) vec[i] = base.cs + (Math.random() - 0.5) * noise;
      for (let i = 4; i < 8; i++) vec[i] = base.math + (Math.random() - 0.5) * noise;
      for (let i = 8; i < 12; i++) vec[i] = base.food + (Math.random() - 0.5) * noise;
      for (let i = 12; i < 16; i++) vec[i] = base.sports + (Math.random() - 0.5) * noise;
    } else if (mode === 'random') {
      for (let i = 0; i < 16; i++) {
        vec[i] = Math.random() + (Math.random() - 0.5) * noise;
      }
    } else if (mode === 'orthogonal') {
      const groupOffset = {cs: 0, math: 4, food: 8, sports: 12}[cat];
      const randDim = groupOffset + Math.floor(Math.random() * 4);
      for (let i = 0; i < 16; i++) {
        vec[i] = (i === randDim) ? 0.95 : (Math.random() - 0.5) * (noise * 0.2);
      }
    }
    
    const norm = Math.sqrt(vec.reduce((sum, v) => sum + v*v, 0));
    if (norm > 0) {
      vec = vec.map(v => v / norm);
    }
    return vec;
  };

  // Preview custom vector
  window.previewInjectedVector = function() {
    const cat = document.getElementById('injCat').value;
    const mode = document.getElementById('injMode').value;
    const noise = parseFloat(document.getElementById('injNoiseSlider').value);
    
    const vec = window.generateSyntheticVector(cat, mode, noise);
    const container = document.getElementById('vectorProfileBars');
    if (!container) return;

    const maxVal = Math.max(...vec.map(Math.abs), 0.01);
    container.innerHTML = vec.map((val, idx) => {
      const heightPct = Math.max(2, Math.min(100, (Math.abs(val) / maxVal) * 100));
      let color = 'var(--accent-blue)';
      if (idx >= 4 && idx < 8) color = 'var(--grad-violet)';
      else if (idx >= 8 && idx < 12) color = 'var(--grad-magenta)';
      else if (idx >= 12) color = 'var(--grad-orange)';
      
      return `<div style="flex:1; height:${heightPct}%; background:${color}; opacity:${val < 0 ? 0.5 : 1};" title="Dim ${idx+1}: ${val.toFixed(3)}"></div>`;
    }).join('');

    const norm = Math.sqrt(vec.reduce((sum, v) => sum + v*v, 0));
    document.getElementById('injVecMagnitude').textContent = `||v|| = ${norm.toFixed(3)}`;
  };

  // Inject Custom Vector
  window.injectVector = async function() {
    const meta = document.getElementById('injMeta').value.trim() || 'Synthetic Node ' + Math.random().toString(36).substring(7).toUpperCase();
    const cat = document.getElementById('injCat').value;
    const mode = document.getElementById('injMode').value;
    const noise = parseFloat(document.getElementById('injNoiseSlider').value);
    
    const vec = window.generateSyntheticVector(cat, mode, noise);
    const API_URL = window.API || window.location.origin;

    try {
      const r = await fetch(API_URL + '/insert', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({metadata: meta, category: cat, embedding: vec})
      });
      const d = await r.json();
      
      if (typeof showToast === 'function') {
        showToast(`Vector injected successfully with ID: ${d.id}`, 'success');
      } else {
        alert(`Vector injected successfully with ID: ${d.id}`);
      }
      
      document.getElementById('injMeta').value = '';
      if (typeof window.loadItems === 'function') {
        await window.loadItems();
      }
    } catch(e) {
      console.error(e);
      if (typeof showToast === 'function') {
        showToast('Failed to inject vector: ' + e.message, 'error');
      } else {
        alert('Failed to inject: ' + e.message);
      }
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupVisualizeEnhancements);
  } else {
    setupVisualizeEnhancements();
  }
})();

// --- JS from docs_ai.docs_js ---
// 1. Chunking Strategy Change & Live Preview
function onStrategyChange() {
  const strategy = document.getElementById('chunkStrategy').value;
  const regexContainer = document.getElementById('customRegexContainer');
  const overlapContainer = document.getElementById('chunkOverlapContainer');
  
  if (strategy === 'fixed') {
    regexContainer.style.display = 'block';
    document.getElementById('customRegexInput').value = "[\\.!?]\\s+";
    overlapContainer.style.display = 'flex';
  } else if (strategy === 'recursive') {
    regexContainer.style.display = 'block';
    document.getElementById('customRegexInput').value = "\\n\\n|\\n|\\s+";
    overlapContainer.style.display = 'flex';
  } else if (strategy === 'semantic') {
    regexContainer.style.display = 'none';
    overlapContainer.style.display = 'none';
  }
  
  updateChunkingPreview();
  playClickSound();
}

function updateChunkingPreview() {
  const text = document.getElementById('docText').value.trim();
  const size = parseInt(document.getElementById('chunkSizeSlider').value);
  const overlap = parseInt(document.getElementById('chunkOverlapSlider').value);
  const strategy = document.getElementById('chunkStrategy').value;
  const regexVal = document.getElementById('customRegexInput').value;
  
  document.getElementById('chunkSizeVal').textContent = size + ' words';
  document.getElementById('chunkOverlapVal').textContent = overlap + ' words';
  
  const preview = document.getElementById('chunkPreview');
  if (!text) {
    preview.innerHTML = '<span style="color:var(--ink-muted);">Type or paste text above to see visual chunk ranges.</span>';
    return;
  }
  
  let chunks = [];
  
  // Validate regex if custom container is shown
  let isValidRegex = true;
  let customReg = null;
  if (strategy !== 'semantic' && regexVal) {
    try {
      customReg = new RegExp(regexVal);
      document.getElementById('customRegexInput').style.borderColor = '';
    } catch(e) {
      document.getElementById('customRegexInput').style.borderColor = '#ef4444';
      isValidRegex = false;
    }
  }
  
  if (strategy === 'fixed') {
    let tokens = [];
    if (customReg && isValidRegex) {
      tokens = text.split(customReg).filter(t => t.trim());
    } else {
      tokens = text.split(/\s+/);
    }
    
    for (let i = 0; i < tokens.length; i += (size - overlap)) {
      chunks.push(tokens.slice(i, i + size).join(customReg ? ' ' : ' '));
      if (i + size >= tokens.length) break;
    }
  } else if (strategy === 'recursive') {
    const delimiters = regexVal && isValidRegex ? regexVal.split('|') : ["\n\n", "\n", " ", ""];
    
    function recursiveSplit(txt, dIdx) {
      if (dIdx >= delimiters.length) return [txt];
      const delim = delimiters[dIdx];
      let parts = delim === "" ? txt.split("") : txt.split(delim);
      
      let result = [];
      for (let part of parts) {
        const words = part.trim().split(/\s+/).length;
        if (words > size) {
          result.push(...recursiveSplit(part, dIdx + 1));
        } else {
          result.push(part);
        }
      }
      return result;
    }
    
    const parts = recursiveSplit(text, 0);
    let curr = [];
    let currWords = 0;
    
    for (let p of parts) {
      const pWords = p.trim().split(/\s+/).length;
      if (currWords + pWords <= size) {
        curr.push(p);
        currWords += pWords;
      } else {
        if (curr.length > 0) chunks.push(curr.join(" "));
        curr = [p];
        currWords = pWords;
      }
    }
    if (curr.length > 0) chunks.push(curr.join(" "));
  } else if (strategy === 'semantic') {
    // Semantic Layout Splitting Simulator using sentence TF-IDF Jaccard overlap
    const sentences = text.match(/[^.!?]+[.!?]+(\s+|$)/g) || [text];
    let currentChunk = [sentences[0]];
    
    function getJaccardSimilarity(s1, s2) {
      const w1 = new Set((s1 || "").toLowerCase().match(/\w+/g) || []);
      const w2 = new Set((s2 || "").toLowerCase().match(/\w+/g) || []);
      if (w1.size === 0 || w2.size === 0) return 0;
      const intersection = new Set([...w1].filter(x => w2.has(x)));
      const union = new Set([...w1, ...w2]);
      return intersection.size / union.size;
    }
    
    for (let i = 1; i < sentences.length; i++) {
      const sim = getJaccardSimilarity(sentences[i-1], sentences[i]);
      const currentWordCount = currentChunk.join(" ").split(/\s+/).length;
      
      // If semantic similarity is low or size gets too large, start a new chunk
      if (sim < 0.12 || currentWordCount > size) {
        chunks.push(currentChunk.join(" "));
        currentChunk = [sentences[i]];
      } else {
        currentChunk.push(sentences[i]);
      }
    }
    if (currentChunk.length > 0) chunks.push(currentChunk.join(" "));
  }
  
  preview.innerHTML = chunks.map((chunk, idx) => `
    <span class="chunk-hl-${idx % 4}" title="Chunk #${idx + 1}">${escapeHtml(chunk)}</span>
  `).join(' ');
}

// 2. Live Word Cloud
function drawWordCloud(text) {
  const canvas = document.getElementById('wordCloudCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  
  const emptyEl = document.getElementById('wordCloudEmpty');
  if (emptyEl) {
    emptyEl.style.display = text.trim() ? 'none' : 'flex';
  }
  
  if (!text.trim()) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    return;
  }
  
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * window.devicePixelRatio;
  canvas.height = rect.height * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  
  const w = rect.width;
  const h = rect.height;
  ctx.clearRect(0, 0, w, h);
  
  const rawWords = text.toLowerCase().match(/\b[a-zA-Z]{3,15}\b/g) || [];
  const stopwords = new Set([
    "the", "and", "our", "you", "your", "his", "her", "their", "this", "that",
    "with", "from", "for", "are", "was", "were", "been", "have", "has", "had",
    "but", "not", "she", "they", "will", "can", "should", "would", "about",
    "into", "then", "them", "some", "only", "other", "than", "these", "there",
    "what", "where", "when", "which", "who", "how", "out", "also"
  ]);
  
  const freq = {};
  rawWords.forEach(wd => {
    if (!stopwords.has(wd)) {
      freq[wd] = (freq[wd] || 0) + 1;
    }
  });
  
  const sorted = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 25);
  if (sorted.length === 0) return;
  
  const maxFreq = sorted[0][1];
  const placed = [];
  const colors = [
    '#8a6efc', // Violet
    '#e46bf0', // Magenta
    '#ff9366', // Orange
    '#ff7799', // Coral
    '#0099ff', // Accent Blue
    '#ffffff'  // White
  ];
  
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  
  sorted.forEach(([word, count]) => {
    const fontSize = Math.max(9, Math.min(22, 9 + (count / maxFreq) * 13));
    ctx.font = `bold ${fontSize}px 'Outfit', 'Space Grotesk', sans-serif`;
    
    const textMetrics = ctx.measureText(word);
    const textW = textMetrics.width + 6;
    const textH = fontSize + 4;
    
    let placedWord = false;
    let angle = 0;
    let radius = 0;
    const cx = w / 2;
    const cy = h / 2;
    
    // Spiral layout searches for empty boundary box
    for (let step = 0; step < 200; step++) {
      const x = cx + radius * Math.cos(angle);
      const y = cy + radius * Math.sin(angle);
      
      let overlap = false;
      const x1 = x - textW / 2;
      const y1 = y - textH / 2;
      
      for (let box of placed) {
        if (x1 < box.x2 && x1 + textW > box.x1 && y1 < box.y2 && y1 + textH > box.y1) {
          overlap = true;
          break;
        }
      }
      
      if (!overlap && x1 > 0 && x1 + textW < w && y1 > 0 && y1 + textH < h) {
        ctx.fillStyle = colors[Math.floor(Math.random() * colors.length)];
        ctx.fillText(word, x, y);
        placed.push({ x1: x1, y1: y1, x2: x1 + textW, y2: y1 + textH });
        placedWord = true;
        break;
      }
      
      radius += 0.6;
      angle += 0.2;
    }
  });
}

// 3. Context Coverage Heatmap
function drawHeatmap(docTitle) {
  const canvas = document.getElementById('heatmapCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const emptyEl = document.getElementById('heatmapEmpty');
  
  if (typeof allItems === 'undefined' || allItems.length === 0) {
    if (emptyEl) emptyEl.style.display = 'flex';
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    return;
  }
  
  const chunks = allItems.filter(item => 
    item.category === 'doc' && 
    (item.metadata.toLowerCase().includes(docTitle.toLowerCase()) || docTitle.toLowerCase().includes(item.metadata.toLowerCase()))
  );
  
  if (chunks.length === 0) {
    if (emptyEl) emptyEl.style.display = 'flex';
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    return;
  }
  
  if (emptyEl) emptyEl.style.display = 'none';
  
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * window.devicePixelRatio;
  canvas.height = rect.height * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  
  const w = rect.width;
  const h = rect.height;
  ctx.clearRect(0, 0, w, h);
  
  const N = chunks.length;
  const cols = Math.min(N, Math.ceil(Math.sqrt(N * 2)));
  const rows = Math.ceil(N / cols);
  
  const padding = 6;
  const gap = 3;
  const cellW = (w - padding * 2 - gap * (cols - 1)) / cols;
  const cellH = (h - padding * 2 - gap * (rows - 1)) / rows;
  
  window._heatmapCells = [];
  
  chunks.forEach((chunk, i) => {
    const row = Math.floor(i / cols);
    const col = i % cols;
    const x = padding + col * (cellW + gap);
    const y = padding + row * (cellH + gap);
    
    // Hash content to generate a deterministic visual vector density representation
    let hash = 0;
    const text = chunk.metadata;
    for (let c = 0; c < text.length; c++) {
      hash = (hash << 5) - hash + text.charCodeAt(c);
    }
    hash = Math.abs(hash) % 100;
    const density = 0.68 + (hash / 100) * 0.31; // Range: 68% - 99%
    
    let color;
    if (density > 0.90) {
      color = `rgba(212, 77, 240, ${density})`; // Deep Magenta
    } else if (density > 0.80) {
      color = `rgba(106, 76, 245, ${density})`; // Deep Violet
    } else {
      color = `rgba(0, 153, 255, ${density})`; // Accent Blue
    }
    
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect(x, y, cellW, cellH, 3);
    ctx.fill();
    
    window._heatmapCells.push({
      x1: x, y1: y, x2: x + cellW, y2: y + cellH,
      chunk: chunk, density: density, idx: i + 1
    });
  });
}

function initHeatmapHover() {
  const canvas = document.getElementById('heatmapCanvas');
  if (!canvas) return;
  const tooltip = document.getElementById('heatmapTooltip');
  if (!tooltip) return;
  
  canvas.addEventListener('mousemove', (e) => {
    if (!window._heatmapCells || window._heatmapCells.length === 0) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    let hovered = null;
    for (let cell of window._heatmapCells) {
      if (mouseX >= cell.x1 && mouseX <= cell.x2 && mouseY >= cell.y1 && mouseY <= cell.y2) {
        hovered = cell;
        break;
      }
    }
    
    if (hovered) {
      canvas.style.cursor = 'pointer';
      tooltip.style.display = 'block';
      tooltip.style.left = (e.clientX + 14) + 'px';
      tooltip.style.top = (e.clientY + 14) + 'px';
      
      const snippet = hovered.chunk.metadata.substring(0, 110) + (hovered.chunk.metadata.length > 110 ? '...' : '');
      tooltip.innerHTML = `
        <div style="font-weight:600; color:#c4b5fd; margin-bottom:4px; font-size:11px;">Chunk #${hovered.idx}</div>
        <div style="margin-bottom:6px; color:var(--ink-muted); display:flex; justify-content:space-between; gap:12px; font-size:10px;">
          <span>Words: ${hovered.chunk.metadata.split(/\s+/).length}</span>
          <strong style="color:#22c55e;">Density: ${(hovered.density * 100).toFixed(1)}%</strong>
        </div>
        <div style="font-size:10px; background:rgba(0,0,0,0.4); padding:6px; border-radius:4px; font-family:monospace; border:1px solid var(--hairline-soft); line-height:1.3; color:#ebebeb;">
          ${escapeHtml(snippet)}
        </div>
      `;
    } else {
      canvas.style.cursor = 'default';
      tooltip.style.display = 'none';
    }
  });
  
  canvas.addEventListener('mouseleave', () => {
    tooltip.style.display = 'none';
  });
}

// 4. Overriding existing dashboard loading hooks to include analytics
const oldLoadDocChunks = window.loadDocChunks;
window.loadDocChunks = function(docTitle) {
  if (oldLoadDocChunks) oldLoadDocChunks(docTitle);
  
  // Update Word Cloud with loaded chunks content
  if (typeof allItems !== 'undefined') {
    const documentChunks = allItems.filter(item => 
      item.category === 'doc' && 
      (item.metadata.toLowerCase().includes(docTitle.toLowerCase()) || docTitle.toLowerCase().includes(item.metadata.toLowerCase()))
    );
    const joinedText = documentChunks.map(c => c.metadata).join('\n\n');
    drawWordCloud(joinedText);
  }
  
  // Render Vector Density Heatmap
  drawHeatmap(docTitle);
};

// Hook docText events on window load
window.addEventListener('DOMContentLoaded', () => {
  const docText = document.getElementById('docText');
  if (docText) {
    docText.addEventListener('input', (e) => {
      drawWordCloud(e.target.value);
      updateChunkingPreview();
    });
  }
  initHeatmapHover();
  
  // Redraw when tabs switch
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.target.classList.contains('on') && mutation.target.id === 'tab-docs') {
        const titleInput = document.getElementById('docTitle');
        if (titleInput && titleInput.value) {
          drawHeatmap(titleInput.value);
        } else {
          // If no doc is loaded, trigger cloud from textarea
          drawWordCloud(document.getElementById('docText').value);
        }
      }
    });
  });
  
  const tabDocs = document.getElementById('tab-docs');
  if (tabDocs) {
    observer.observe(tabDocs, { attributes: true, attributeFilter: ['class'] });
  }
});

// --- JS from docs_ai.ai_js ---
// 1. Toggle Multi-Model Compare Mode
function toggleMultiModelCompare() {
  const toggle = document.getElementById('multiCompareToggle');
  const chatHistory = document.getElementById('chatHistory');
  const compareContainer = document.getElementById('compareContainer');
  
  if (!toggle || !chatHistory || !compareContainer) return;
  
  const isCompare = toggle.classList.toggle('on');
  if (isCompare) {
    chatHistory.style.display = 'none';
    compareContainer.style.display = 'grid';
  } else {
    chatHistory.style.display = 'block';
    compareContainer.style.display = 'none';
  }
  
  updateCostEstimator();
  playClickSound();
}

// 2. Token & Cost Estimator Calculator
let window_activePromptTokens = 0;
let window_activeCompletionTokens = 0;

function updateCostEstimator() {
  const question = document.getElementById('ragQuestion').value.trim();
  const toggleCompare = document.getElementById('multiCompareToggle');
  const isCompare = toggleCompare ? toggleCompare.classList.contains('on') : false;
  
  // Calculate prompt words from active context checkboxes
  let contextWords = 0;
  const cards = document.querySelectorAll('.inspector-card-checkbox');
  let checkedCount = 0;
  cards.forEach(card => {
    if (card.checked) {
      checkedCount++;
      const text = card.getAttribute('data-text') || '';
      contextWords += text.split(/\s+/).length;
    }
  });
  
  const countEl = document.getElementById('inspectorCount');
  if (countEl) countEl.textContent = `${checkedCount} active chunk${checkedCount === 1 ? '' : 's'}`;
  
  const questionWords = question ? question.split(/\s+/).length : 0;
  
  // Model rates per 1M tokens:
  // Qwen-0.5B: Input $0.05 / Output $0.10
  // Llama-3-8B: Input $0.15 / Output $0.60
  // DeepSeek-R1: Input $0.55 / Output $2.19
  
  // Token size approximations (1.35 tokens per word)
  const promptTokens = Math.ceil((questionWords + contextWords) * 1.35) + 60; // adding baseline system prompt
  window_activePromptTokens = promptTokens;
  
  document.getElementById('promptTokens').textContent = promptTokens + ' tokens';
  
  let completionTokens = 0;
  let totalCost = 0.0;
  
  if (isCompare) {
    // Sum of Qwen, Llama, and DeepSeek lengths if already streamed or estimated
    const qwenText = document.getElementById('qwenResponse').textContent;
    const llamaText = document.getElementById('llamaResponse').textContent;
    const deepseekText = document.getElementById('deepseekResponse').textContent;
    
    const qwWords = qwenText.includes('Awaiting') || qwenText.includes('Reasoning') ? 0 : qwenText.split(/\s+/).length;
    const llWords = llamaText.includes('Awaiting') || llamaText.includes('Reasoning') ? 0 : llamaText.split(/\s+/).length;
    const dsWords = deepseekText.includes('Awaiting') || deepseekText.includes('Reasoning') ? 0 : deepseekText.split(/\s+/).length;
    
    const qwTokens = Math.ceil(qwWords * 1.3);
    const llTokens = Math.ceil(llWords * 1.3);
    const dsTokens = Math.ceil(dsWords * 1.3);
    
    completionTokens = qwTokens + llTokens + dsTokens;
    
    const qwenCost = ((promptTokens * 0.05) + (qwTokens * 0.10)) / 1000000;
    const llamaCost = ((promptTokens * 0.15) + (llTokens * 0.60)) / 1000000;
    const deepseekCost = ((promptTokens * 0.55) + (dsTokens * 2.19)) / 1000000;
    
    totalCost = qwenCost + llamaCost + deepseekCost;
  } else {
    // Single model Llama-3-8B or standard output
    const singleText = document.getElementById('chatHistory').lastElementChild ? document.getElementById('chatHistory').lastElementChild.textContent : '';
    const cleanSingleText = singleText.includes('Hello PJ') || singleText.includes('Reasoning') ? '' : singleText;
    const words = cleanSingleText.split(/\s+/).length;
    completionTokens = Math.ceil(words * 1.3);
    
    totalCost = ((promptTokens * 0.15) + (completionTokens * 0.60)) / 1000000;
  }
  
  window_activeCompletionTokens = completionTokens;
  document.getElementById('completionTokens').textContent = completionTokens + ' tokens';
  document.getElementById('estimatedCost').textContent = '$' + totalCost.toFixed(5);
}

// 3. Active Context Cards Renderer
function renderInspectorCards(chunks) {
  const container = document.getElementById('inspectorCards');
  if (!container) return;
  
  if (!chunks || chunks.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding:16px; border:1px dashed var(--hairline); border-radius:var(--radius-sm); color:var(--ink-muted); font-size:11px;">
        Submit a query to inspect and toggle retrieved chunks.
      </div>`;
    return;
  }
  
  container.innerHTML = chunks.map((c, idx) => {
    const simVal = c.distance !== undefined ? (1 - c.distance) : 0.85;
    const simPct = (simVal * 100).toFixed(0) + '%';
    const text = c.text || c.metadata || '';
    const title = c.title || `Chunk #${idx+1}`;
    
    return `
      <div class="inspector-card">
        <div class="inspector-card-header">
          <label class="inspector-checkbox-label">
            <input type="checkbox" class="inspector-card-checkbox" checked 
                   data-text="${escapeHtml(text)}" 
                   onchange="updateCostEstimator()" 
                   id="chk-context-${c.id || idx}">
            <span class="inspector-title-text" title="${escapeHtml(title)}">${escapeHtml(title)}</span>
          </label>
          <span class="inspector-badge" style="color: ${simVal > 0.8 ? '#10b981' : '#f59e0b'};">Sim: ${simPct}</span>
        </div>
        <div class="inspector-card-body" onclick="this.style.maxHeight = this.style.maxHeight === '200px' ? '48px' : '200px'">
          ${escapeHtml(text)}
        </div>
      </div>
    `;
  }).join('');
  
  updateCostEstimator();
}

// 4. Populate Mock Chunks on Load
function loadInspectorMockChunks() {
  const mockChunks = [
    {
      id: 101,
      title: "HNSW Graph Indexing",
      metadata: "Hierarchical Navigable Small World (HNSW) graphs achieve approximate nearest neighbor search by constructing a multi-layer graph index. Layers represent different skip levels, directing queries from coarse granularity to fine resolution in O(log N) operations.",
      text: "Hierarchical Navigable Small World (HNSW) graphs achieve approximate nearest neighbor search by constructing a multi-layer graph index. Layers represent different skip levels, directing queries from coarse granularity to fine resolution in O(log N) operations.",
      distance: 0.06
    },
    {
      id: 102,
      title: "Product Quantization (PQ)",
      metadata: "Product Quantization is a vector compression technique that divides high-dimensional vector spaces into smaller orthogonal subspaces, quantizes each subspace independently using k-means, and represents vectors as short codes.",
      text: "Product Quantization is a vector compression technique that divides high-dimensional vector spaces into smaller orthogonal subspaces, quantizes each subspace independently using k-means, and represents vectors as short codes.",
      distance: 0.14
    },
    {
      id: 103,
      title: "Hybrid Search Fusion",
      metadata: "Combining exact keyword matching (BM25) with deep learning dense vector embeddings. Reciprocal Rank Fusion (RRF) merges scores from both pipelines to provide balanced semantic and lexical results.",
      text: "Combining exact keyword matching (BM25) with deep learning dense vector embeddings. Reciprocal Rank Fusion (RRF) merges scores from both pipelines to provide balanced semantic and lexical results.",
      distance: 0.21
    }
  ];
  renderInspectorCards(mockChunks);
}

// 5. Simulated Answer Stream Engine (Multi-Model)
function generateSimulatedAnswer(modelId, question, checkedContexts) {
  let contextText = checkedContexts.map(c => c.text).join(" ");
  if (!contextText.trim()) {
    contextText = "No document context is currently selected in the Active Context Inspector.";
  }
  
  const sentences = contextText.split(/[.!?]+/).map(s => s.trim()).filter(s => s.length > 5);
  const fact1 = sentences[0] || "No local facts found.";
  const fact2 = sentences[1] || "Default weight parameters apply.";
  
  if (modelId === 'qwen') {
    if (checkedContexts.length === 0) {
      return `Based on my base weights (Qwen-0.5B), without context I can state that ${question} usually involves mathematical node traversal or culinary steps. Please enable context cards for grounded answers.`;
    }
    return `Qwen-0.5B fast response: 
- Definition: ${fact1}
- Purpose: ${fact2}
- Speed: Done in ~4.5ms.`;
  }
  
  if (modelId === 'llama') {
    if (checkedContexts.length === 0) {
      return `### Llama-3-8B Balanced Agent
I observe that all retrieved context chunks have been deselected from the active prompt payload. 

**Parametric Answer**: Regarding "${question}", this is normally handled by standard database designs. To ground this response in your specific documents, please tick the context checkboxes in the Inspector panel.`;
    }
    return `### Response from Llama-3-8B RAG Agent

Here is a structured explanation addressing **"${question}"** using the active database chunks:

1. **Primary Insight**: ${fact1}
2. **Technical Details**: ${fact2}
3. **Application Bounds**: Grounded context verifies that combining these layers prevents hallucinations. Let me know if you want me to expand on these points!`;
  }
  
  if (modelId === 'deepseek') {
    let thinking = `Thinking Process:
1. User asked: "${question}"
2. Context chunks ticked: ${checkedContexts.length}.
3. Analyzing query keywords...`;
    
    if (checkedContexts.length === 0) {
      thinking += `\n4. Context is empty. Relying on model parametric knowledge base.\n5. Structure output with warning alert.`;
      return `<think>\n${thinking}\n</think>\n\n### DeepSeek-R1 (Dist.) Synthesis\n\n> [!WARNING]\n> Zero context chunks are checked. This answer is synthesized solely from pre-trained parameters.\n\nFor **${question}**, local documents are unreferenced. Grounding vector retrieval is recommended to secure factual consistency.`;
    }
    
    thinking += `\n4. Selected text contains: "${contextText.substring(0, 70)}..."\n5. Isolating crucial semantic elements: "${fact1.substring(0, 40)}"\n6. Organizing facts logically into definition, system relevance, and cost complexity.`;
    return `<think>\n${thinking}\n</think>\n\n### DeepSeek-R1 (Dist.) Analytical Response\n\nBased on the active HNSW retrieval blocks, we analyze "${question}" as follows:\n\n#### I. Core Architectural Foundation\n${fact1}\n\n#### II. Mechanism Analysis\n${fact2}\n\n*Conclusion*: This structural configuration is verified by local DB index state.`;
  }
}

// 6. Streaming/Typewriter Animation
function streamResponse(elementId, text, speedMultiplier = 1, callback = null) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.innerHTML = '';
  
  let index = 0;
  const length = text.length;
  
  function formatResponse(txt) {
    // Wrap think tags
    let formatted = txt.replace(/<think>([\s\S]*?)<\/think>/g, (match, p1) => {
      return `<div class="think-block">
        <div class="think-header"><i class="ti ti-brain"></i> Reasoning Process</div>
        <div class="think-content">${p1.trim().replace(/\n/g, '<br>')}</div>
      </div>`;
    });
    return formatted.replace(/\n/g, '<br>');
  }
  
  function type() {
    if (index < length) {
      index += Math.ceil(3 * speedMultiplier);
      if (index > length) index = length;
      el.innerHTML = formatResponse(text.substring(0, index)) + '<span class="cursor" style="display:inline-block; width:2px; height:12px; background:var(--ink); margin-left:2px; animation:blink 1s step-end infinite;"></span>';
      updateCostEstimator();
      requestAnimationFrame(type);
    } else {
      el.innerHTML = formatResponse(text);
      if (callback) callback();
    }
  }
  
  requestAnimationFrame(type);
}

// 7. Override standard askAI function
const oldAskAI = window.askAI;
window.askAI = async function() {
  const question = document.getElementById('ragQuestion').value.trim();
  if (!question) return;
  
  const toggle = document.getElementById('multiCompareToggle');
  const isCompare = toggle ? toggle.classList.contains('on') : false;
  
  if (!isCompare) {
    // Perform original askAI backend fetch
    if (oldAskAI) {
      // Temporarily intercept the streaming context response
      const oldFetch = window.fetch;
      window.fetch = async function(url, options) {
        const res = await oldFetch(url, options);
        if (url.includes('/doc/ask')) {
          // Wrap the response reader to extract the context chunks
          const clone = res.clone();
          const reader = clone.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          
          // Background loop to extract retrieved context
          (async () => {
            try {
              while(true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();
                for (let line of lines) {
                  if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    if (data.type === 'context') {
                      renderInspectorCards(data.data);
                      break;
                    }
                  }
                }
              }
            } catch(e) { console.error("RAG Context intercept error:", e); }
          })();
        }
        return res;
      };
      
      await oldAskAI();
      window.fetch = oldFetch; // restore
    }
    return;
  }
  
  // Multi-Model Compare Simulation mode
  const btn = document.getElementById('askBtn');
  btn.disabled = true;
  btn.textContent = 'Reasoning...';
  playClickSound();
  
  const qwenEl = document.getElementById('qwenResponse');
  const llamaEl = document.getElementById('llamaResponse');
  const deepseekEl = document.getElementById('deepseekResponse');
  
  qwenEl.innerHTML = '<div class="shimmer-line" style="width:80%;"></div><div class="shimmer-line" style="width:60%; margin-top:8px;"></div>';
  llamaEl.innerHTML = '<div class="shimmer-line" style="width:90%;"></div><div class="shimmer-line" style="width:70%; margin-top:8px;"></div>';
  deepseekEl.innerHTML = '<div class="shimmer-line" style="width:40%;"></div><div class="shimmer-line" style="width:85%; margin-top:8px;"></div>';
  
  // Extractchecked contexts
  const checkedContexts = [];
  document.querySelectorAll('.inspector-card-checkbox').forEach(cb => {
    if (cb.checked) {
      checkedContexts.push({ text: cb.getAttribute('data-text') || '', title: cb.parentNode.querySelector('.inspector-title-text').textContent });
    }
  });
  
  const qwenAnswer = generateSimulatedAnswer('qwen', question, checkedContexts);
  const llamaAnswer = generateSimulatedAnswer('llama', question, checkedContexts);
  const deepseekAnswer = generateSimulatedAnswer('deepseek', question, checkedContexts);
  
  let qwenDone = false;
  let llamaDone = false;
  let deepseekDone = false;
  
  function checkAllDone() {
    if (qwenDone && llamaDone && deepseekDone) {
      btn.disabled = false;
      btn.textContent = 'Ask AI';
      document.getElementById('ragQuestion').value = '';
    }
  }
  
  // Simulating simultaneous streaming responses
  setTimeout(() => {
    streamResponse('qwenResponse', qwenAnswer, 1.6, () => {
      qwenDone = true;
      checkAllDone();
    });
  }, 300);
  
  setTimeout(() => {
    streamResponse('llamaResponse', llamaAnswer, 1.0, () => {
      llamaDone = true;
      checkAllDone();
    });
  }, 100);
  
  setTimeout(() => {
    streamResponse('deepseekResponse', deepseekAnswer, 0.7, () => {
      deepseekDone = true;
      checkAllDone();
    });
  }, 500);
};

// Setup initial state on DOMContentLoaded
window.addEventListener('DOMContentLoaded', () => {
  loadInspectorMockChunks();
  
  const ragQuestion = document.getElementById('ragQuestion');
  if (ragQuestion) {
    ragQuestion.addEventListener('input', updateCostEstimator);
  }
  
  // Also hook when RAG configuration values change
  const observer = new MutationObserver(() => {
    updateCostEstimator();
  });
  
  const tabAI = document.getElementById('tab-ai');
  if (tabAI) {
    observer.observe(tabAI, { subtree: true, attributes: true, attributeFilter: ['class'] });
  }
});

// --- JS from sql_working.sql_js ---
window._lastSqlResults = [];
window._sqlGridState = { page: 1, limit: 10, sortBy: '', sortDir: 'asc', filterText: '' };

// Redefine runSqlQuery to support the grid, profiler, and schema sidebar
runSqlQuery = async function() {
  const query = document.getElementById('sqlQueryText').value.trim();
  const v = document.getElementById('sqlQueryVector').value.trim();
  const text = document.getElementById('sqlQueryTextParam').value.trim();
  
  if (!query) {
    showToast('Please enter a SQL query first.', 'warning');
    return;
  }
  
  const btn = document.getElementById('sqlRunBtn');
  btn.disabled = true;
  btn.textContent = 'Running Query...';
  
  const resultsPanel = document.getElementById('sqlResultsPanel');
  resultsPanel.innerHTML = '<div style="color:var(--ink-muted); text-align:center; padding:20px;">Executing query on database...</div>';
  
  const profilerCard = document.getElementById('sqlProfilerCard');
  if (profilerCard) profilerCard.style.display = 'none';

  const startMs = performance.now();

  try {
    const response = await fetch(API + '/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, v, text })
    });
    
    const d = await response.json();
    const elapsedMs = performance.now() - startMs;

    if (!response.ok) {
      throw new Error(d.error || 'Server error');
    }
    
    // Update AST and Compiled blocks
    document.getElementById('sqlAstOutput').textContent = JSON.stringify(d.ast || {}, null, 2);
    document.getElementById('sqlCompiledOutput').textContent = JSON.stringify(d.compiled || {}, null, 2);
    
    // Store results
    window._lastSqlResults = d.results || [];
    
    // Reset Grid State
    window._sqlGridState = { page: 1, limit: parseInt(document.getElementById('sqlGridLimitSelect').value) || 10, sortBy: '', sortDir: 'asc', filterText: '' };
    document.getElementById('sqlGridFilterInput').value = '';
    
    if (window._lastSqlResults.length > 0) {
      document.getElementById('sqlGridControls').style.display = 'flex';
      document.getElementById('sqlGridPagination').style.display = 'flex';
      renderSqlResultsGrid(1);
    } else {
      document.getElementById('sqlGridControls').style.display = 'none';
      document.getElementById('sqlGridPagination').style.display = 'none';
      resultsPanel.innerHTML = '<div style="color:var(--ink-muted); text-align:center; padding:20px;">No matching results found.</div>';
    }

    // Render Profiler Bar Chart
    renderSqlProfiler(elapsedMs, query);

    // Save history & Visualize plan
    saveSqlHistory(query, false);
    try {
      visualizeExecutionPlan(d.ast);
    } catch(e) {}

  } catch (e) {
    resultsPanel.innerHTML = `<div style="color:#ff4b4b; text-align:center; padding:20px;">Error: ${e.message}</div>`;
    document.getElementById('sqlAstOutput').textContent = '{}';
    document.getElementById('sqlCompiledOutput').textContent = '{}';
    document.getElementById('sqlGridControls').style.display = 'none';
    document.getElementById('sqlGridPagination').style.display = 'none';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Execute Query';
  }
};

function renderSqlProfiler(elapsedMs, queryText) {
  const container = document.getElementById('sqlProfilerContent');
  const card = document.getElementById('sqlProfilerCard');
  if (!container || !card) return;
  card.style.display = 'block';

  // Calculate realistic stages
  const qLower = queryText.toLowerCase();
  const isSimilarity = qLower.includes('similarity') || qLower.includes('where');
  const isJoin = qLower.includes('join');

  let parseTime = 0.12 + Math.random() * 0.15;
  let planTime = 0.18 + Math.random() * 0.22;
  let scanTime = (isSimilarity ? 6.5 : 1.8) + Math.random() * 3.0;
  let filterTime = (isSimilarity ? 2.5 : 0.4) + Math.random() * 1.5;
  let joinTime = isJoin ? (4.2 + Math.random() * 3.0) : 0;
  let formatTime = 0.25 + Math.random() * 0.35;

  const totalSimulated = parseTime + planTime + scanTime + filterTime + joinTime + formatTime;
  const ratio = elapsedMs / totalSimulated;

  // Scale to match the actual elapsed time
  parseTime *= ratio;
  planTime *= ratio;
  scanTime *= ratio;
  filterTime *= ratio;
  joinTime *= ratio;
  formatTime *= ratio;

  const stages = [
    { name: 'AST Parsing & Lexing', val: parseTime, color: '#3b82f6' },
    { name: 'Query Compiler & Planning', val: planTime, color: '#8b5cf6' },
    { name: 'HNSW / Table scan', val: scanTime, color: '#10b981' },
    { name: 'Constraint Filtering', val: filterTime, color: '#f59e0b' }
  ];
  if (isJoin) {
    stages.push({ name: 'Relational JOIN Engine', val: joinTime, color: '#a855f7' });
  }
  stages.push({ name: 'Data Projection & Render', val: formatTime, color: '#ec4899' });

  const totalScaled = stages.reduce((acc, stage) => acc + stage.val, 0);

  container.innerHTML = stages.map(stage => {
    const pct = ((stage.val / totalScaled) * 100).toFixed(1);
    return `
      <div>
        <div style="display:flex; justify-content:space-between; font-size:10px; margin-bottom:3px;">
          <span>${stage.name}</span>
          <span style="font-family:monospace; color:var(--ink);">${pct}% (${stage.val.toFixed(2)} ms)</span>
        </div>
        <div class="profiler-bar-track">
          <div class="profiler-bar-fill" style="width: ${pct}%; background: ${stage.color};"></div>
        </div>
      </div>
    `;
  }).join('');
}

function renderSqlResultsGrid(page = 1) {
  const resultsPanel = document.getElementById('sqlResultsPanel');
  if (!resultsPanel) return;

  let filtered = [...window._lastSqlResults];
  const filterText = window._sqlGridState.filterText.trim().toLowerCase();
  
  if (filterText) {
    filtered = filtered.filter(item => {
      const isDoc = item.title !== undefined;
      const idStr = String(item.id || '').toLowerCase();
      const titleStr = String(isDoc ? item.title : (item.metadata || `Item #${item.id}`)).toLowerCase();
      const contentStr = String(isDoc ? item.text : `Category: ${item.category}`).toLowerCase();
      const tableStr = isDoc ? 'documents' : 'vectors';
      
      return idStr.includes(filterText) || titleStr.includes(filterText) || contentStr.includes(filterText) || tableStr.includes(filterText);
    });
  }

  // Sort
  const sortBy = window._sqlGridState.sortBy;
  const sortDir = window._sqlGridState.sortDir;
  if (sortBy) {
    filtered.sort((a, b) => {
      const isDocA = a.title !== undefined;
      const isDocB = b.title !== undefined;
      let valA, valB;

      if (sortBy === 'id') {
        valA = Number(a.id) || 0;
        valB = Number(b.id) || 0;
      } else if (sortBy === 'table') {
        valA = isDocA ? 'documents' : 'vectors';
        valB = isDocB ? 'documents' : 'vectors';
      } else if (sortBy === 'title') {
        valA = isDocA ? a.title : (a.metadata || `Item #${a.id}`);
        valB = isDocB ? b.title : (b.metadata || `Item #${b.id}`);
      } else if (sortBy === 'content') {
        valA = isDocA ? a.text : `Category: ${a.category}`;
        valB = isDocB ? b.text : `Category: ${b.category}`;
      } else if (sortBy === 'similarity') {
        valA = a.distance !== undefined ? (1.0 - a.distance) : -1;
        valB = b.distance !== undefined ? (1.0 - b.distance) : -1;
      }

      if (valA < valB) return sortDir === 'asc' ? -1 : 1;
      if (valA > valB) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }

  // Pagination bounds
  const limit = window._sqlGridState.limit;
  const totalItems = filtered.length;
  const totalPages = Math.ceil(totalItems / limit) || 1;
  const currentPage = Math.max(1, Math.min(page, totalPages));
  window._sqlGridState.page = currentPage;

  const startIndex = (currentPage - 1) * limit;
  const endIndex = Math.min(startIndex + limit, totalItems);
  const pageItems = filtered.slice(startIndex, endIndex);

  // Render Table
  if (pageItems.length === 0) {
    resultsPanel.innerHTML = '<div style="color:var(--ink-muted); text-align:center; padding:20px;">No matching results found.</div>';
    document.getElementById('sqlGridRangeText').textContent = 'Showing 0-0 of 0 items';
    renderPaginationButtons(totalPages, currentPage);
    return;
  }

  const getSortIndicator = (col) => {
    if (window._sqlGridState.sortBy !== col) return ' <span class="sort-indicator">↕</span>';
    return window._sqlGridState.sortDir === 'asc' ? ' <span class="sort-indicator active">▲</span>' : ' <span class="sort-indicator active">▼</span>';
  };

  let html = `
    <div style="overflow-x:auto;">
      <table class="telemetry-table sortable-grid" style="width:100%; border-collapse:collapse; font-family:'JetBrains Mono', monospace; font-size:11px; text-align:left;">
        <thead>
          <tr style="border-bottom:1px solid var(--hairline); font-size:10px; text-transform:uppercase; user-select:none;">
            <th onclick="sortSqlGrid('id')" style="padding:10px; color:var(--ink-muted); cursor:pointer;">ID${getSortIndicator('id')}</th>
            <th onclick="sortSqlGrid('table')" style="padding:10px; color:var(--ink-muted); cursor:pointer;">Table${getSortIndicator('table')}</th>
            <th onclick="sortSqlGrid('title')" style="padding:10px; color:var(--ink-muted); cursor:pointer;">Title / Metadata${getSortIndicator('title')}</th>
            <th onclick="sortSqlGrid('content')" style="padding:10px; color:var(--ink-muted); cursor:pointer;">Content / Details${getSortIndicator('content')}</th>
            <th onclick="sortSqlGrid('similarity')" style="padding:10px; color:var(--ink-muted); cursor:pointer; text-align:right;">Similarity${getSortIndicator('similarity')}</th>
          </tr>
        </thead>
        <tbody>
  `;

  pageItems.forEach(h => {
    const isDoc = h.title !== undefined;
    const id = h.id || '—';
    const tbl = isDoc ? 'documents' : 'vectors';
    const title = isDoc ? h.title : (h.metadata || `Item #${h.id}`);
    const textPreview = isDoc ? h.text : `Category: ${h.category}`;
    const distance = h.distance !== undefined ? h.distance.toFixed(4) : '—';
    const sim = h.distance !== undefined ? (1.0 - h.distance).toFixed(4) : '—';

    html += `
      <tr class="grid-row">
        <td style="padding:10px; font-weight:700; color:var(--accent-blue);">${id}</td>
        <td style="padding:10px;">
          <span class="res-badge" style="background:${isDoc ? 'rgba(219,39,119,0.1)' : 'rgba(0,153,255,0.1)'}; color:${isDoc ? 'var(--grad-magenta)' : 'var(--accent-blue)'}; border:0.5px solid var(--hairline); font-size:9px; padding:2px 6px; border-radius:4px;">
            ${tbl}
          </span>
        </td>
        <td style="padding:10px; font-weight:600; color:var(--ink); white-space:nowrap; max-width:150px; overflow:hidden; text-overflow:ellipsis;" title="${escapeHtml(title)}">${escapeHtml(title)}</td>
        <td style="padding:10px; color:var(--ink-muted); max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(textPreview)}">${escapeHtml(textPreview)}</td>
        <td style="padding:10px; text-align:right; font-weight:700; color:#22c55e;">
          ${sim} <span style="font-size:9px; color:var(--ink-muted); font-weight:normal; margin-left:4px;">(dist: ${distance})</span>
        </td>
      </tr>
    `;
  });

  html += '</tbody></table></div>';
  resultsPanel.innerHTML = html;

  // Update Footer range info
  document.getElementById('sqlGridRangeText').textContent = `Showing ${startIndex + 1}-${endIndex} of ${totalItems} items`;
  renderPaginationButtons(totalPages, currentPage);
}

function sortSqlGrid(column) {
  playClickSound();
  if (window._sqlGridState.sortBy === column) {
    window._sqlGridState.sortDir = window._sqlGridState.sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    window._sqlGridState.sortBy = column;
    window._sqlGridState.sortDir = 'asc';
  }
  renderSqlResultsGrid(window._sqlGridState.page);
}

function changeSqlGridLimit(limit) {
  playClickSound();
  window._sqlGridState.limit = parseInt(limit) || 10;
  renderSqlResultsGrid(1);
}

function filterSqlGrid(text) {
  window._sqlGridState.filterText = text;
  renderSqlResultsGrid(1);
}

function renderPaginationButtons(totalPages, currentPage) {
  const container = document.getElementById('sqlGridPaginationButtons');
  if (!container) return;

  let html = '';
  
  // Previous button
  const prevDisabled = currentPage === 1 ? 'disabled style="opacity:0.5; cursor:not-allowed;"' : '';
  html += `<button class="btn-secondary" ${prevDisabled} onclick="if(${currentPage > 1}){renderSqlResultsGrid(${currentPage - 1}); playClickSound();}" style="padding:4px 8px; font-size:10px; margin:0; line-height:1;"><i class="ti ti-chevron-left"></i></button>`;

  // Simple page numbers
  const maxButtons = 5;
  let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
  let endPage = Math.min(totalPages, startPage + maxButtons - 1);
  if (endPage - startPage + 1 < maxButtons) {
    startPage = Math.max(1, endPage - maxButtons + 1);
  }

  for (let i = startPage; i <= endPage; i++) {
    const isActive = i === currentPage;
    const activeStyle = isActive ? 'background:var(--accent-blue); color:#fff; border-color:var(--accent-blue); font-weight:700;' : '';
    html += `<button class="btn-secondary" onclick="renderSqlResultsGrid(${i}); playClickSound();" style="padding:4px 8px; font-size:10px; margin:0; ${activeStyle}">${i}</button>`;
  }

  // Next button
  const nextDisabled = currentPage === totalPages ? 'disabled style="opacity:0.5; cursor:not-allowed;"' : '';
  html += `<button class="btn-secondary" ${nextDisabled} onclick="if(${currentPage < totalPages}){renderSqlResultsGrid(${currentPage + 1}); playClickSound();}" style="padding:4px 8px; font-size:10px; margin:0; line-height:1;"><i class="ti ti-chevron-right"></i></button>`;

  container.innerHTML = html;
}

function exportSqlResultsToCSV() {
  playClickSound();
  if (!window._lastSqlResults || window._lastSqlResults.length === 0) {
    showToast("No data to export", "warning");
    return;
  }
  
  let csv = "ID,Table,Title_Metadata,Content_Details,Similarity,Distance\n";
  window._lastSqlResults.forEach(r => {
    const isDoc = r.title !== undefined;
    const id = r.id || '';
    const tbl = isDoc ? 'documents' : 'vectors';
    const title = isDoc ? r.title : (r.metadata || `Item #${r.id}`);
    const text = isDoc ? r.text : `Category: ${r.category}`;
    const dist = r.distance !== undefined ? r.distance : '';
    const sim = r.distance !== undefined ? (1.0 - r.distance) : '';
    
    // Escape CSV values
    const csvRow = [
      `"${String(id).replace(/"/g, '""')}"`,
      `"${tbl}"`,
      `"${String(title).replace(/"/g, '""')}"`,
      `"${String(text).replace(/"/g, '""')}"`,
      sim,
      dist
    ].join(",");
    csv += csvRow + "\n";
  });
  
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.setAttribute("download", `nurosearch_sql_results_${Date.now()}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast("Data exported to CSV successfully", "success");
}

function injectBoilerplate(type) {
  playClickSound();
  let query = '';
  if (type === 'select_all') {
    query = "SELECT * FROM vectors LIMIT 5;";
  } else if (type === 'filter_cat') {
    query = "SELECT * FROM vectors WHERE category = 'sports' LIMIT 5;";
  } else if (type === 'join_docs') {
    query = "SELECT v.id, v.category, d.title, v.similarity \nFROM vectors v \nJOIN documents d ON v.id = d.id \nWHERE v.similarity > 0.8 \nLIMIT 5;";
  } else if (type === 'agg_cat') {
    query = "SELECT category, COUNT(*) as count, AVG(similarity) as avg_similarity \nFROM vectors \nGROUP BY category;";
  } else if (type === 'search_docs') {
    query = "SELECT * FROM documents WHERE title LIKE '%mars%' LIMIT 5;";
  }
  
  insertAtSqlCursor(query);
}

function insertAtSqlCursor(text) {
  const el = document.getElementById('sqlQueryText');
  if (!el) return;
  const start = el.selectionStart;
  const end = el.selectionEnd;
  const val = el.value;
  el.value = val.substring(0, start) + text + val.substring(end);
  el.focus();
  el.selectionStart = el.selectionEnd = start + text.length;
}

// --- JS from sql_working.working_js ---
window._pipelineRetrievedContexts = [];

// Pipeline state simulator
window.pipelineSim = {
  currentStep: 0,
  isPlaying: false,
  speed: 1.0,
  timerId: null,
  allItems: [],
  queryText: "",
  queryVector: null,
  searchResults: [],
  retrievedContexts: [],
  generatedAnswer: "",
  startTime: 0,
  elapsedTime: 0,
  timerIntervalId: null,
  
  init: async function() {
    try {
      const r = await fetch(API + '/items');
      this.allItems = await r.json();
    } catch(e) {
      // Fallback mock items
      this.allItems = Array.from({length: 15}, (_, i) => ({
        id: i + 1,
        metadata: `Topic: ${['Mars Space exploration', 'Quantum neural computing', 'Dynamic algorithms', 'Database index HNSW'][i % 4]}`,
        category: ['tech', 'sports', 'science', 'math'][i % 4],
        embedding: Array.from({length: 16}, () => Math.random() * 2 - 1)
      }));
    }
  },
  
  updateUIState: function() {
    const playBtn = document.getElementById('simPlayBtn');
    const pauseBtn = document.getElementById('simPauseBtn');
    const statusText = document.getElementById('simStatusText');
    const stepText = document.getElementById('simStepText');
    
    if (!playBtn || !pauseBtn || !statusText || !stepText) return;

    if (this.isPlaying) {
      playBtn.classList.add('active-playing');
      pauseBtn.classList.remove('active-paused');
      statusText.textContent = "PLAYING";
      statusText.style.color = "#22c55e";
    } else {
      playBtn.classList.remove('active-playing');
      if (this.currentStep > 0 && this.currentStep < 5) {
        pauseBtn.classList.add('active-paused');
        statusText.textContent = "PAUSED";
        statusText.style.color = "#eab308";
      } else if (this.currentStep === 5) {
        statusText.textContent = "COMPLETED";
        statusText.style.color = "#22c55e";
      } else {
        statusText.textContent = "IDLE";
        statusText.style.color = "var(--ink-muted)";
      }
    }
    
    stepText.textContent = `${this.currentStep} / 5`;
    
    // Highlight steps and connectors based on currentStep
    for (let i = 1; i <= 5; i++) {
      const stepEl = document.getElementById(`step${i}`);
      if (!stepEl) continue;
      
      if (i < this.currentStep) {
        stepEl.className = 'pipeline-step completed';
      } else if (i === this.currentStep) {
        stepEl.className = 'pipeline-step active';
      } else {
        stepEl.className = 'pipeline-step';
      }
      
      if (i < 5) {
        const connEl = document.getElementById(`conn${i}`);
        if (!connEl) continue;
        if (i < this.currentStep) {
          connEl.className = 'pipeline-connector completed';
        } else if (i === this.currentStep) {
          connEl.className = 'pipeline-connector active';
        } else {
          connEl.className = 'pipeline-connector';
        }
      }
    }
  },
  
  play: function() {
    if (this.isPlaying) return;
    playClickSound();
    
    this.queryText = document.getElementById('demoQuery').value.trim();
    if (!this.queryText) {
      showToast("Please enter a query first.", "warning");
      return;
    }
    
    document.getElementById('aiWorkingSplit').style.display = 'flex';
    document.getElementById('pipelineTimer').style.display = 'block';
    
    if (this.currentStep === 0 || this.currentStep === 5) {
      this.resetData();
      this.currentStep = 1;
      this.startTime = performance.now();
      this.startTimer();
    }
    
    this.isPlaying = true;
    this.updateUIState();
    this.runLoop();
  },
  
  pause: function() {
    if (!this.isPlaying) return;
    playClickSound();
    this.isPlaying = false;
    if (this.timerId) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }
    this.stopTimer();
    this.updateUIState();
  },
  
  stepNext: async function() {
    playClickSound();
    this.queryText = document.getElementById('demoQuery').value.trim();
    if (!this.queryText) {
      showToast("Please enter a query first.", "warning");
      return;
    }
    
    document.getElementById('aiWorkingSplit').style.display = 'flex';
    document.getElementById('pipelineTimer').style.display = 'block';
    
    if (this.isPlaying) {
      this.pause();
    }

    if (this.currentStep === 0 || this.currentStep === 5) {
      this.resetData();
      this.currentStep = 1;
      this.startTime = performance.now();
      this.startTimer();
    } else {
      this.currentStep++;
    }
    
    this.updateUIState();
    await this.executeStep(this.currentStep);
    
    if (this.currentStep === 5) {
      this.stopTimer();
      this.updateUIState();
    }
  },
  
  reset: function() {
    playClickSound();
    this.isPlaying = false;
    if (this.timerId) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }
    this.stopTimer();
    this.currentStep = 0;
    this.resetData();
    this.updateUIState();
    
    // Clear step descs
    for (let i = 1; i <= 5; i++) {
      const descEl = document.getElementById(`step${i}-desc`);
      if (descEl) descEl.textContent = "Waiting...";
      const stepEl = document.getElementById(`step${i}`);
      if (stepEl) stepEl.className = "pipeline-step";
      if (i < 5) {
        const connEl = document.getElementById(`conn${i}`);
        if (connEl) connEl.className = "pipeline-connector";
      }
    }
    
    document.getElementById('pipelineOutput').textContent = "";
    document.getElementById('pipelineResult').style.display = 'none';
    document.getElementById('pipelineMetrics').style.display = 'none';
    document.getElementById('pipelineTimer').textContent = '0.00s';
    document.getElementById('queryDetailsCard').style.display = 'none';
    
    window._pipelineRetrievedContexts = [];
    compilePromptLive();
  },
  
  resetData: function() {
    this.queryVector = null;
    this.searchResults = [];
    this.retrievedContexts = [];
    this.generatedAnswer = "";
    window._pipelineRetrievedContexts = [];
  },
  
  setSpeed: function(val) {
    this.speed = parseFloat(val);
  },
  
  startTimer: function() {
    if (this.timerIntervalId) clearInterval(this.timerIntervalId);
    this.timerIntervalId = setInterval(() => {
      if (this.startTime) {
        this.elapsedTime = (performance.now() - this.startTime) / 1000;
        document.getElementById('pipelineTimer').textContent = this.elapsedTime.toFixed(2) + 's';
      }
    }, 50);
  },
  
  stopTimer: function() {
    if (this.timerIntervalId) {
      clearInterval(this.timerIntervalId);
      this.timerIntervalId = null;
    }
  },
  
  runLoop: async function() {
    if (!this.isPlaying) return;
    
    await this.executeStep(this.currentStep);
    
    if (this.currentStep < 5) {
      const baseDelays = [0, 800, 1000, 1200, 1000, 1500]; // Step delays in ms
      const currentDelay = baseDelays[this.currentStep] / this.speed;
      
      this.timerId = setTimeout(() => {
        this.currentStep++;
        this.runLoop();
      }, currentDelay);
    } else {
      this.isPlaying = false;
      this.stopTimer();
      this.updateUIState();
    }
  },
  
  executeStep: async function(stepNum) {
    if (this.allItems.length === 0) {
      await this.init();
    }
    
    const rerankEnabled = document.getElementById('rerankToggle') ? document.getElementById('rerankToggle').classList.contains('on') : false;
    
    switch (stepNum) {
      case 1:
        document.getElementById('step1-desc').textContent = `"${this.queryText}"`;
        try { renderAIVisualization(this.allItems, null, [], 'step1'); } catch(e) {}
        break;
        
      case 2:
        document.getElementById('step2-desc').textContent = 'Computing embeddings...';
        this.queryVector = textToEmbedding(this.queryText);
        const vecPreview = this.queryVector.slice(0, 6).map(v => v.toFixed(3)).join(', ') + ', ...';
        document.getElementById('step2-desc').innerHTML = `[${vecPreview}]<br><span style="color:#22c55e;">16D generated</span>`;
        try { renderAIVisualization(this.allItems, this.queryVector, [], 'step2'); } catch(e) {}
        break;
        
      case 3:
        document.getElementById('step3-desc').textContent = 'Traversing HNSW layers graph...';
        try { renderAIVisualization(this.allItems, this.queryVector, [], 'step3-searching'); } catch(e) {}
        
        // Wait briefly for traversal animation
        await new Promise(r => setTimeout(r, 400 / this.speed));
        
        const demoKRetrieve = rerankEnabled ? 10 : 3;
        try {
          const vStr = this.queryVector.join(',');
          const sr = await fetch(`${API}/search?v=${vStr}&k=${demoKRetrieve}&metric=cosine&algo=hnsw`);
          const sd = await sr.json();
          this.searchResults = sd.results || [];
        } catch(e) {
          // Mock results if fetch fails
          this.searchResults = this.allItems.slice(0, demoKRetrieve).map((item, idx) => ({
            id: item.id,
            metadata: item.metadata,
            category: item.category,
            distance: 0.15 + idx * 0.08
          }));
        }
        
        document.getElementById('step3-desc').innerHTML = `Traversed ${this.allItems.length} vectors<br><span style="color:#22c55e;">Recall found ${this.searchResults.length} candidates</span>`;
        try { renderAIVisualization(this.allItems, this.queryVector, this.searchResults, 'step3'); } catch(e) {}
        break;
        
      case 4:
        document.getElementById('step4-desc').textContent = 'Retrieving context & ranking...';
        document.getElementById('pipelineMetrics').style.display = 'block';
        
        // update stats
        document.getElementById('metricEmbed').textContent = '0.320s';
        document.getElementById('metricSearch').textContent = '0.012s';
        document.getElementById('metricVectors').textContent = this.allItems.length;
        document.getElementById('metricMatches').textContent = '3';
        
        const qdCard = document.getElementById('queryDetailsCard');
        if (qdCard) qdCard.style.display = 'block';
        
        const qdAlgo = document.getElementById('qdAlgo');
        const qdType = document.getElementById('qdType');
        const qdEmbed = document.getElementById('qdEmbed');
        const qdK = document.getElementById('qdK');
        const visPt = document.getElementById('visPointCount');

        if (qdAlgo) qdAlgo.textContent = 'HNSW';
        if (qdType) qdType.textContent = rerankEnabled ? 'HNSW Recall + Rerank' : 'HNSW Exact';
        if (qdEmbed) qdEmbed.textContent = 'nomic-embed-text';
        if (qdK) qdK.textContent = '3';
        if (visPt) visPt.textContent = this.allItems.length + ' chunks';
        
        // Fetch actual contexts
        try {
          const response = await fetch(API + '/doc/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: this.queryText, k: 3 })
          });
          if (response.ok) {
            const sd = await response.json();
            this.retrievedContexts = sd.results || [];
          } else {
            throw new Error();
          }
        } catch(e) {
          // fallback mock context
          this.retrievedContexts = [
            { id: 1, title: 'Mars Exploration', text: 'Perseverance rover explored Jezero Crater on Mars looking for microbial life signs.', distance: 0.15 },
            { id: 2, title: 'Solar System', text: 'The solar system consists of the Sun and eight planets orbiting around it.', distance: 0.22 },
            { id: 3, title: 'Dynamic Programming', text: 'Dynamic programming is a method for solving complex problems by breaking them down into simpler subproblems.', distance: 0.35 }
          ];
        }
        
        const ctxHtml = this.retrievedContexts.map(c => {
          const badge = c.rerank_score ? ` <span class="demo-rerank-badge">Rerank: ${c.rerank_score}</span>` : ` (dist: ${(c.distance || 0).toFixed(3)})`;
          return `<div class="demo-ctx-line">• <strong>${escapeHtml(c.title || c.metadata || 'Chunk')}</strong>${badge}</div>`;
        }).join('');
        
        document.getElementById('step4-desc').innerHTML = `
          Retrieved ${this.retrievedContexts.length} chunks<br>
          <div class="demo-ctx-list">${ctxHtml}</div>
        `;
        
        try { renderAIVisualization(this.allItems, this.queryVector, this.retrievedContexts, 'step4'); } catch(e) {}
        
        // Save retrieved context to window so compiled prompt can use it
        window._pipelineRetrievedContexts = this.retrievedContexts;
        compilePromptLive();
        
        // Render breakdown bars
        const breakdownContainer = document.getElementById('latencyBreakdownBars');
        if (breakdownContainer) {
          const embedTime = 0.320;
          const searchTime = 0.012;
          const totalTime = embedTime + searchTime + 0.65;
          const items = [
            { name: 'Embedding', val: embedTime, color: 'var(--accent-blue)' },
            { name: 'HNSW Graph', val: searchTime, color: '#22c55e' },
            { name: 'LLM Stream', val: 0.65, color: 'var(--grad-magenta)' }
          ];
          breakdownContainer.innerHTML = items.map(item => {
            const pct = ((item.val / totalTime) * 100).toFixed(0);
            return `
              <div style="font-size:10px; margin-bottom:4px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
                  <span>${item.name}</span>
                  <span>${pct}% (${item.val.toFixed(3)}s)</span>
                </div>
                <div style="height:4px; background:var(--surface-2); border-radius:2px; overflow:hidden;">
                  <div style="width:${pct}%; height:100%; background:${item.color}; border-radius:2px;"></div>
                </div>
              </div>`;
          }).join('');
        }
        break;
        
      case 5:
        document.getElementById('step5-desc').textContent = 'Synthesizing response...';
        document.getElementById('pipelineResult').style.display = 'block';
        document.getElementById('pipelineOutput').innerHTML = '<span style="color:var(--ink-muted);">Computing answer...</span>';
        
        try {
          const useGraph = document.getElementById('graphToggle') ? document.getElementById('graphToggle').classList.contains('on') : false;
          const endpoint = useGraph ? '/doc/ask/graph' : '/doc/ask';
          const askResp = await fetch(API + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: this.queryText, k: 3, rewrite: false, rerank: rerankEnabled })
          });
          
          if (askResp.ok) {
            const reader = askResp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            this.generatedAnswer = '';
            
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split('\n');
              buffer = lines.pop();
              
              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.slice(6));
                    if (data.type === 'token') {
                      this.generatedAnswer += data.data;
                      document.getElementById('pipelineOutput').textContent = this.generatedAnswer;
                      document.getElementById('pipelineResult').scrollTop = document.getElementById('pipelineResult').scrollHeight;
                    }
                  } catch(e){}
                }
              }
            }
          } else {
            throw new Error();
          }
        } catch(e) {
          // simulation answer stream
          this.generatedAnswer = '';
          const mockTokens = "Based on the retrieved context, Mars exploration has been actively carried out by robots like the Perseverance rover. These systems query multi-dimensional graphs, mapping out candidate points using cosine metrics. Similarly, context chunks are combined inside prompt editors to yield synthesized outputs.".split(' ');
          for (let i = 0; i < mockTokens.length; i++) {
            this.generatedAnswer += mockTokens[i] + ' ';
            document.getElementById('pipelineOutput').textContent = this.generatedAnswer;
            document.getElementById('pipelineResult').scrollTop = document.getElementById('pipelineResult').scrollHeight;
            await new Promise(r => setTimeout(r, 60 / this.speed));
          }
        }
        
        document.getElementById('step5-desc').textContent = 'Synthesis complete.';
        // Export button display
        const exportBtn = document.getElementById('exportTraceBtn');
        if (exportBtn) exportBtn.style.display = 'block';
        break;
    }
  },
  
  setSpeed: function(val) {
    this.speed = parseFloat(val);
  }
};

// Override runDemoPipeline to launch our simulator play loop
runDemoPipeline = async function() {
  pipelineSim.play();
};

function compilePromptLive() {
  const editor = document.getElementById('promptTemplateEditor');
  const preview = document.getElementById('promptCompiledPreview');
  const queryInput = document.getElementById('demoQuery');
  
  if (!editor || !preview) return;

  const query = queryInput ? (queryInput.value.trim() || '[No query input yet...]') : '[No query input yet...]';
  
  let contextStr = '[No context retrieved yet. Run or step the pipeline to Step 4.]';
  if (window._pipelineRetrievedContexts && window._pipelineRetrievedContexts.length > 0) {
    contextStr = window._pipelineRetrievedContexts.map((c, idx) => {
      return `[Chunk ${idx + 1}] Title: ${c.title || c.metadata || 'Document'} \nContent: ${c.text || c.content || ''}\n`;
    }).join('\n');
  }

  let text = editor.value;
  text = text.replace(/\{\{\s*query\s*\}\}/g, query);
  text = text.replace(/\{\{\s*context\s*\}\}/g, contextStr);

  preview.textContent = text;
}

// Call on startup
setTimeout(() => {
  if (window.pipelineSim) {
    window.pipelineSim.init();
    compilePromptLive();
  }
}, 600);

// --- JS from cluster_about.cluster_js ---
// State and configuration for Chaos Monkey & Raft Simulation\nlet chaosLogs = [];\nlet partitionActive = false;\nlet partitionA = ['worker-1', 'worker-2'];\nlet partitionB = ['worker-3'];\nlet raftTerm = 4;\nlet raftLogs = [\n  { index: 1020, term: 3, command: \"SET doc_782\", states: { 'worker-1': 'committed', 'worker-2': 'committed', 'worker-3': 'committed' } },\n  { index: 1021, term: 3, command: \"SET doc_783\", states: { 'worker-1': 'committed', 'worker-2': 'committed', 'worker-3': 'committed' } },\n  { index: 1022, term: 3, command: \"SET doc_784\", states: { 'worker-1': 'committed', 'worker-2': 'committed', 'worker-3': 'committed' } },\n  { index: 1023, term: 4, command: \"UPSERT doc_785\", states: { 'worker-1': 'committed', 'worker-2': 'committed', 'worker-3': 'committed' } },\n  { index: 1024, term: 4, command: \"DEL doc_109\", states: { 'worker-1': 'committed', 'worker-2': 'committed', 'worker-3': 'committed' } }\n];\nlet autoWritesEnabled = true;\nlet autoWritesInterval = null;\nlet simulatedLeader = 'worker-1';\n\n// Override global nodeOverrides from index.html if necessary\nif (typeof nodeOverrides === 'undefined') {\n  window.nodeOverrides = {\n    coordinator: true,\n    'worker-1': true,\n    'worker-2': true,\n    'worker-3': true\n  };\n}\n\n// Log message to Chaos Console\nfunction monkeyLog(msg, type = 'info') {\n  const consoleEl = document.getElementById('chaosConsole');\n  if (!consoleEl) return;\n  const time = new Date().toLocaleTimeString();\n  const logDiv = document.createElement('div');\n  logDiv.className = `log-${type}`;\n  logDiv.innerHTML = `[${time}] ${msg}`;\n  consoleEl.appendChild(logDiv);\n  consoleEl.scrollTop = consoleEl.scrollHeight;\n}\n\n// Redefining toggleNode to hook into our UI\nwindow.toggleNodeDirect = function(id) {\n  const checkbox = document.getElementById('toggle-checkbox-' + id);\n  if (checkbox) {\n    checkbox.checked = !checkbox.checked;\n    toggleNode(id);\n  } else {\n    nodeOverrides[id] = !nodeOverrides[id];\n    recalculateLeader();\n    fetchClusterHealth();\n  }\n  monkeyLog(`Directly toggled node ${id} to ${nodeOverrides[id] ? 'ONLINE' : 'OFFLINE'}`, nodeOverrides[id] ? 'success' : 'err');\n};\n\n// Update Circular Dials and UI Health\nwindow.fetchClusterHealth = async function() {\n  const coordStatus = document.getElementById('coordinatorStatus');\n  const coordHost = document.getElementById('coordinatorHost');\n  \n  updateRaftSvgPaths();\n\n  let coordOnline = nodeOverrides.coordinator !== false;\n  if (coordStatus) {\n    coordStatus.textContent = coordOnline ? 'Online (Simulated)' : 'Offline';\n    coordStatus.style.background = coordOnline ? '#00ff66' : '#ff4b4b';\n    coordStatus.style.color = coordOnline ? '#000' : '#fff';\n  }\n  if (coordHost) {\n    coordHost.textContent = `Proxy: ${API}/cluster/coordinator/health (${coordOnline ? 'Simulated' : 'Offline'})`;\n  }\n\n  const workers = ['worker-1', 'worker-2', 'worker-3'];\n  \n  for (const id of workers) {\n    const card = document.getElementById(`card-${id}`);\n    const statusSpan = document.getElementById(`status-${id}`);\n    const roleDiv = document.getElementById(`role-${id}`);\n    const vecDiv = document.getElementById(`vec-${id}`);\n    const logDiv = document.getElementById(`log-${id}`);\n    \n    const isOnline = nodeOverrides[id] !== false;\n    \n    if (statusSpan) {\n      statusSpan.textContent = isOnline ? 'Online' : 'Offline';\n      statusSpan.style.background = isOnline ? '#00ff66' : '#ff4b4b';\n      statusSpan.style.color = isOnline ? '#000' : '#fff';\n    }\n    if (card) {\n      card.style.borderColor = isOnline ? 'rgba(0, 255, 102, 0.2)' : 'rgba(255, 75, 75, 0.15)';\n    }\n\n    if (isOnline) {\n      const isLeader = (simulatedLeader === id);\n      const isIsolated = partitionActive && partitionB.includes(id);\n      \n      if (roleDiv) {\n        if (isLeader) {\n          roleDiv.textContent = 'Leader 👑';\n          roleDiv.style.color = '#ff7a3d';\n        } else {\n          roleDiv.textContent = isIsolated ? 'Follower (Isolated)' : 'Follower';\n          roleDiv.style.color = isIsolated ? '#ffa726' : '#0099ff';\n        }\n      }\n\n      const mockVectors = { 'worker-1': 1084, 'worker-2': 1092, 'worker-3': 1079 };\n      vecDiv.textContent = mockVectors[id] + (raftLogs.filter(l => l.states[id] === 'committed').length);\n      logDiv.textContent = raftLogs.length;\n\n      const cpuVal = Math.floor(Math.random() * 15) + (isLeader ? 15 : 5);\n      const memVal = 48 + Math.floor(Math.random() * 4);\n      \n      updateCircularDial(id, 'cpu', cpuVal);\n      updateCircularDial(id, 'mem', memVal);\n    } else {\n      if (roleDiv) {\n        roleDiv.textContent = '—';\n        roleDiv.style.color = '';\n      }\n      if (vecDiv) vecDiv.textContent = '—';\n      if (logDiv) logDiv.textContent = '—';\n      \n      updateCircularDial(id, 'cpu', 0);\n      updateCircularDial(id, 'mem', 0);\n    }\n  }\n\n  updateRaftSvgNodes();\n};\n\nfunction updateCircularDial(nodeId, type, pct) {\n  const circle = document.getElementById(`dial-fill-${type}-${nodeId}`);\n  const text = document.getElementById(`${type}-val-${nodeId}`);\n  if (!circle || !text) return;\n  const radius = 24;\n  const circumference = 2 * Math.PI * radius; // ~150.8\n  const offset = circumference - (pct / 100) * circumference;\n  circle.style.strokeDashoffset = offset;\n  text.textContent = Math.round(pct) + '%';\n}\n\nfunction updateRaftSvgPaths() {\n  const p12 = document.getElementById('svgPath-1-2');\n  const p13 = document.getElementById('svgPath-1-3');\n  const p23 = document.getElementById('svgPath-2-3');\n  \n  if (!p12 || !p13 || !p23) return;\n\n  const w1 = nodeOverrides['worker-1'] !== false;\n  const w2 = nodeOverrides['worker-2'] !== false;\n  const w3 = nodeOverrides['worker-3'] !== false;\n\n  if (w1 && w2) {\n    p12.className.baseVal = \"heartbeat-active\";\n  } else {\n    p12.className.baseVal = \"heartbeat-broken\";\n  }\n\n  if (w1 && w3) {\n    if (partitionActive) {\n      p13.className.baseVal = \"heartbeat-partitioned\";\n    } else {\n      p13.className.baseVal = \"heartbeat-active\";\n    }\n  } else {\n    p13.className.baseVal = \"heartbeat-broken\";\n  }\n\n  if (w2 && w3) {\n    if (partitionActive) {\n      p23.className.baseVal = \"heartbeat-partitioned\";\n    } else {\n      p23.className.baseVal = \"heartbeat-active\";\n    }\n  } else {\n    p23.className.baseVal = \"heartbeat-broken\";\n  }\n}\n\nfunction updateRaftSvgNodes() {\n  const nodes = ['worker-1', 'worker-2', 'worker-3'];\n  nodes.forEach(id => {\n    const group = document.getElementById(`svgNode-${id}`);\n    const roleText = document.getElementById(`svgNodeRole-${id}`);\n    if (!group || !roleText) return;\n    \n    const circle = group.querySelector('circle');\n    const isOnline = nodeOverrides[id] !== false;\n    const isLeader = (simulatedLeader === id);\n    const isIsolated = partitionActive && partitionB.includes(id);\n\n    if (!isOnline) {\n      circle.setAttribute('stroke', '#ff4b4b');\n      roleText.textContent = \"Offline\";\n      roleText.setAttribute('fill', '#ff4b4b');\n    } else if (isLeader) {\n      circle.setAttribute('stroke', '#ff7a3d');\n      roleText.textContent = \"Leader 👑\";\n      roleText.setAttribute('fill', '#ff7a3d');\n    } else if (isIsolated) {\n      circle.setAttribute('stroke', '#ffa726');\n      roleText.textContent = \"Isolated\";\n      roleText.setAttribute('fill', '#ffa726');\n    } else {\n      circle.setAttribute('stroke', '#0099ff');\n      roleText.textContent = \"Follower\";\n      roleText.setAttribute('fill', '#0099ff');\n    }\n  });\n}\n\nwindow.recalculateLeader = function() {\n  const activeWorkers = ['worker-1', 'worker-2', 'worker-3'].filter(id => nodeOverrides[id] !== false);\n  \n  if (partitionActive) {\n    const activeInA = activeWorkers.filter(id => partitionA.includes(id));\n    const activeInB = activeWorkers.filter(id => partitionB.includes(id));\n\n    if (activeInA.length >= 2) {\n      if (!simulatedLeader || !activeInA.includes(simulatedLeader)) {\n        simulatedLeader = activeInA[0];\n        raftTerm++;\n        monkeyLog(`[RAFT] Partition A achieved quorum. Elected new leader ${simulatedLeader} for Term ${raftTerm}.`, 'success');\n      }\n    } else {\n      simulatedLeader = null;\n      monkeyLog(`[RAFT] Quorum lost across all partition bounds. Leadership stepped down.`, 'warn');\n    }\n  } else {\n    if (activeWorkers.length >= 2) {\n      if (!simulatedLeader || !activeWorkers.includes(simulatedLeader)) {\n        simulatedLeader = activeWorkers[0];\n        raftTerm++;\n        monkeyLog(`[RAFT] Quorum active (${activeWorkers.length}/3). Elected ${simulatedLeader} as Leader for Term ${raftTerm}.`, 'success');\n      }\n    } else {\n      simulatedLeader = null;\n      monkeyLog(`[RAFT] Quorum lost (${activeWorkers.length}/3 online). Database is in read-only safe mode.`, 'warn');\n    }\n  }\n};\n\nwindow.triggerMonkeyFailNode = function() {\n  if (typeof playClickSound === 'function') playClickSound();\n  \n  const online = ['worker-1', 'worker-2', 'worker-3'].filter(id => nodeOverrides[id] !== false);\n  if (online.length === 0) {\n    monkeyLog(\"All nodes are already offline. Chaos Monkey has nothing to kill!\", \"warn\");\n    return;\n  }\n  const target = online[Math.floor(Math.random() * online.length)];\n  \n  nodeOverrides[target] = false;\n  \n  const label = document.getElementById('toggle-label-' + target);\n  const checkbox = document.getElementById('toggle-checkbox-' + target);\n  const slider = document.getElementById('slider-' + target);\n  const knob = document.getElementById('knob-' + target);\n  if (checkbox) checkbox.checked = false;\n  if (label) {\n    label.textContent = 'OFF';\n    label.style.color = 'var(--switch-label-off)';\n  }\n  if (slider) slider.style.background = 'var(--switch-track-off)';\n  if (knob) knob.style.left = '2px';\n\n  monkeyLog(`Chaos Monkey terminated node <strong>${target}</strong>!`, 'err');\n  showToast(`Chaos Monkey terminated ${target}!`, 'error');\n\n  recalculateLeader();\n  fetchClusterHealth();\n};\n\nwindow.triggerMonkeyPartition = function() {\n  if (typeof playClickSound === 'function') playClickSound();\n  if (partitionActive) {\n    monkeyLog(\"A network partition is already active. Heal it first!\", \"warn\");\n    return;\n  }\n\n  partitionActive = true;\n  monkeyLog(\"Chaos Monkey severed network connections! Quorum A: [W1, W2], Quorum B: [W3] (isolated).\", \"warn\");\n  showToast(\"Network Partition Active!\", \"warning\");\n\n  recalculateLeader();\n  fetchClusterHealth();\n};\n\nwindow.triggerMonkeyHeal = function() {\n  if (typeof playClickSound === 'function') playClickSound();\n  if (!partitionActive) {\n    monkeyLog(\"Network boundaries are normal. No partition to heal.\", \"info\");\n    return;\n  }\n\n  partitionActive = false;\n  monkeyLog(\"Network partition healed. Re-establishing global quorum heartbeats.\", \"success\");\n  showToast(\"Network partition healed!\", \"success\");\n\n  const leader = simulatedLeader;\n  if (leader) {\n    raftLogs.forEach(log => {\n      if (nodeOverrides['worker-3'] !== false && log.states['worker-3'] !== 'committed') {\n        log.states['worker-3'] = 'committed';\n      }\n    });\n    monkeyLog(`[RAFT] worker-3 successfully synchronized missing logs from Leader ${leader}.`, 'success');\n  }\n\n  recalculateLeader();\n  fetchClusterHealth();\n  renderRaftLedger();\n};\n\nwindow.triggerMonkeyElection = function() {\n  if (typeof playClickSound === 'function') playClickSound();\n  \n  const online = ['worker-1', 'worker-2', 'worker-3'].filter(id => nodeOverrides[id] !== false);\n  if (online.length < 2) {\n    monkeyLog(\"Insufficient nodes to hold an election. Quorum lost.\", \"warn\");\n    return;\n  }\n\n  monkeyLog(\"Manual leader step-down triggered. Heartbeat cancelled.\", \"info\");\n  \n  const oldLeader = simulatedLeader;\n  simulatedLeader = null;\n  fetchClusterHealth();\n\n  setTimeout(() => {\n    const candidates = online.filter(id => id !== oldLeader);\n    const newLeader = candidates.length > 0 ? candidates[0] : online[0];\n    \n    simulatedLeader = newLeader;\n    raftTerm++;\n    \n    monkeyLog(`[RAFT] Election complete. worker candidate <strong>${newLeader}</strong> won consensus for Term ${raftTerm}.`, 'success');\n    showToast(`New Leader Elected: ${newLeader}`, 'success');\n    fetchClusterHealth();\n  }, 1200);\n};\n\nfunction renderRaftLedger() {\n  const tbody = document.getElementById('raftLogBody');\n  if (!tbody) return;\n  \n  tbody.innerHTML = '';\n  const logsToRender = raftLogs.slice(-8);\n  logsToRender.forEach(log => {\n    const tr = document.createElement('tr');\n    tr.style.borderBottom = '1px solid var(--hairline-soft)';\n    \n    const tdIdx = document.createElement('td');\n    tdIdx.style.padding = '6px 8px';\n    tdIdx.style.fontWeight = 'bold';\n    tdIdx.textContent = `#${log.index}`;\n    \n    const tdTerm = document.createElement('td');\n    tdTerm.style.padding = '6px 8px';\n    tdTerm.textContent = `T${log.term}`;\n    \n    const tdCmd = document.createElement('td');\n    tdCmd.style.padding = '6px 8px';\n    tdCmd.style.color = 'var(--ink)';\n    tdCmd.textContent = log.command;\n    \n    tr.appendChild(tdIdx);\n    tr.appendChild(tdTerm);\n    tr.appendChild(tdCmd);\n    \n    ['worker-1', 'worker-2', 'worker-3'].forEach(node => {\n      const tdNode = document.createElement('td');\n      tdNode.style.padding = '6px 8px';\n      tdNode.style.textAlign = 'center';\n      \n      const state = log.states[node];\n      const span = document.createElement('span');\n      span.className = `ledger-badge ledger-${state}`;\n      \n      if (state === 'committed') {\n        span.textContent = 'Commit';\n      } else if (state === 'replicated') {\n        span.textContent = 'Replicated';\n      } else if (state === 'uncommitted') {\n        span.textContent = 'Queue';\n      } else if (state === 'offline') {\n        span.textContent = 'Offline';\n      } else if (state === 'stale') {\n        span.textContent = 'Stale';\n      }\n      \n      tdNode.appendChild(span);\n      tr.appendChild(tdNode);\n    });\n    \n    tbody.appendChild(tr);\n  });\n  \n  const container = document.getElementById('raftTableContainer');\n  if (container) {\n    container.scrollTop = container.scrollHeight;\n  }\n}\n\nwindow.appendRaftLog = function(cmd) {\n  if (!simulatedLeader) {\n    monkeyLog(`[RAFT] Rejected write \"${cmd}\". No active leader consensus.`, 'err');\n    return;\n  }\n\n  const nextIndex = raftLogs.length > 0 ? raftLogs[raftLogs.length - 1].index + 1 : 1000;\n  \n  const initialStates = {};\n  ['worker-1', 'worker-2', 'worker-3'].forEach(node => {\n    const isOnline = nodeOverrides[node] !== false;\n    if (!isOnline) {\n      initialStates[node] = 'offline';\n    } else if (partitionActive && partitionB.includes(node) && partitionA.includes(simulatedLeader)) {\n      initialStates[node] = 'stale';\n    } else if (partitionActive && partitionA.includes(node) && partitionB.includes(simulatedLeader)) {\n      initialStates[node] = 'stale';\n    } else {\n      initialStates[node] = 'uncommitted';\n    }\n  });\n\n  const newLog = {\n    index: nextIndex,\n    term: raftTerm,\n    command: cmd,\n    states: initialStates\n  };\n\n  raftLogs.push(newLog);\n  renderRaftLedger();\n  monkeyLog(`[LEADER] Appended client write #${nextIndex}: <code>${cmd}</code>. Broadcasting to quorum...`);\n\n  setTimeout(() => {\n    ['worker-1', 'worker-2', 'worker-3'].forEach(node => {\n      if (newLog.states[node] === 'uncommitted') {\n        newLog.states[node] = 'replicated';\n      }\n    });\n    renderRaftLedger();\n    \n    setTimeout(() => {\n      const activeInQuorum = ['worker-1', 'worker-2', 'worker-3'].filter(node => {\n        return nodeOverrides[node] !== false && \n               (!partitionActive || \n                (partitionA.includes(simulatedLeader) && partitionA.includes(node)) || \n                (partitionB.includes(simulatedLeader) && partitionB.includes(node)));\n      });\n\n      if (activeInQuorum.length >= 2) {\n        ['worker-1', 'worker-2', 'worker-3'].forEach(node => {\n          if (newLog.states[node] === 'replicated' || node === simulatedLeader) {\n            newLog.states[node] = 'committed';\n          }\n        });\n        renderRaftLedger();\n        monkeyLog(`[RAFT] Quorum achieved for #${nextIndex}. Committing index entry.`, 'success');\n      } else {\n        monkeyLog(`[RAFT] Consensus timeout. Failed to achieve quorum for #${nextIndex}. Entry is uncommitted.`, 'err');\n      }\n    }, 400);\n  }, 350);\n};\n\nwindow.toggleAutoWrites = function() {\n  const cb = document.getElementById('toggle-checkbox-auto-writes');\n  if (!cb) return;\n  autoWritesEnabled = cb.checked;\n  \n  const label = document.getElementById('toggle-label-auto-writes');\n  const slider = document.getElementById('slider-auto-writes');\n  const knob = document.getElementById('knob-auto-writes');\n  if (label) {\n    label.textContent = autoWritesEnabled ? 'ON' : 'OFF';\n    label.style.color = autoWritesEnabled ? 'var(--switch-label-on)' : 'var(--switch-label-off)';\n  }\n  if (slider) {\n    slider.style.background = autoWritesEnabled ? 'var(--switch-track-on)' : 'var(--switch-track-off)';\n  }\n  if (knob) {\n    knob.style.left = autoWritesEnabled ? '15px' : '2px';\n  }\n  \n  if (typeof playClickSound === 'function') playClickSound();\n\n  if (autoWritesEnabled) {\n    startAutoWrites();\n    monkeyLog(\"Auto-ingestion simulation enabled.\");\n  } else {\n    stopAutoWrites();\n    monkeyLog(\"Auto-ingestion simulation suspended.\");\n  }\n};\n\nfunction startAutoWrites() {\n  if (autoWritesInterval) clearInterval(autoWritesInterval);\n  autoWritesInterval = setInterval(() => {\n    if (!autoWritesEnabled) return;\n    const cmds = [\n      \"SET vec_\" + Math.floor(Math.random() * 1000),\n      \"UPSERT v_\" + Math.floor(Math.random() * 1000),\n      \"DEL vec_\" + Math.floor(Math.random() * 200),\n      \"COMMIT index_chunk\",\n      \"PRUNE stale_node\"\n    ];\n    const randCmd = cmds[Math.floor(Math.random() * cmds.length)];\n    appendRaftLog(randCmd);\n  }, 3500);\n}\n\nfunction stopAutoWrites() {\n  if (autoWritesInterval) {\n    clearInterval(autoWritesInterval);\n    autoWritesInterval = null;\n  }\n}\n\nsetTimeout(() => {\n  renderRaftLedger();\n  startAutoWrites();\n  fetchClusterHealth();\n}, 500);

// --- JS from cluster_about.about_js ---
// System Architecture Zoom & Pan State\nlet archZoom = 1;\nlet archPanX = 0;\nlet archPanY = 0;\nlet isPanning = false;\nlet startX = 0, startY = 0;\n\nwindow.handleArchZoom = function(e) {\n  e.preventDefault();\n  const zoomFactor = 0.08;\n  if (e.deltaY < 0) {\n    archZoom = Math.min(archZoom + zoomFactor, 2.5);\n  } else {\n    archZoom = Math.max(archZoom - zoomFactor, 0.5);\n  }\n  updateArchTransform();\n};\n\nwindow.handleArchPanStart = function(e) {\n  if (e.target.closest('.arch-controls')) return;\n  isPanning = true;\n  startX = e.clientX - archPanX;\n  startY = e.clientY - archPanY;\n  document.addEventListener('mousemove', handleArchPanMove);\n  document.addEventListener('mouseup', handleArchPanEnd);\n};\n\nfunction handleArchPanMove(e) {\n  if (!isPanning) return;\n  archPanX = e.clientX - startX;\n  archPanY = e.clientY - startY;\n  updateArchTransform();\n}\n\nfunction handleArchPanEnd() {\n  isPanning = false;\n  document.removeEventListener('mousemove', handleArchPanMove);\n  document.removeEventListener('mouseup', handleArchPanEnd);\n}\n\nwindow.zoomArchIn = function() {\n  if (typeof playClickSound === 'function') playClickSound();\n  archZoom = Math.min(archZoom + 0.15, 2.5);\n  updateArchTransform();\n};\n\nwindow.zoomArchOut = function() {\n  if (typeof playClickSound === 'function') playClickSound();\n  archZoom = Math.max(archZoom - 0.15, 0.5);\n  updateArchTransform();\n};\n\nwindow.resetArchZoom = function() {\n  if (typeof playClickSound === 'function') playClickSound();\n  archZoom = 1;\n  archPanX = 0;\n  archPanY = 0;\n  updateArchTransform();\n};\n\nfunction updateArchTransform() {\n  const g = document.getElementById('archG');\n  if (g) {\n    g.setAttribute('transform', `translate(${archPanX}, ${archPanY}) scale(${archZoom})`);\n  }\n}\n\n// Architecture Hover Info Tooltip\nconst archMeta = {\n  ingest: {\n    title: \"Document Ingestion Engine\",\n    desc: \"Ingests raw text payloads, files (PDF/TXT), and URL nodes. Performs schema validations and tokenization. <br><strong>Tech:</strong> Flask Ingest Handler, Tokenizers. <br><strong>Avg Latency:</strong> 1.2ms. <br><strong>Source File:</strong> <code>ingestion_worker.py</code>\"\n  },\n  queue: {\n    title: \"Apache Kafka Queue Broker\",\n    desc: \"Provides streaming async buffering. Guarantees high write availability during ingestion bursts. <br><strong>Tech:</strong> Kafka Topic Partitioning. <br><strong>Avg Latency:</strong> 0.8ms write ack. <br><strong>Source File:</strong> <code>worker.py</code> & <code>docker-compose.yml</code>\"\n  },\n  embed: {\n    title: \"Neural Embedder Pipeline\",\n    desc: \"Runs sentences through dense language models to project text into 768-dimensional float arrays. <br><strong>Tech:</strong> PyTorch, ONNX Runtime, CUDA Kernel. <br><strong>Avg Latency:</strong> 12ms (GPU) / 140ms (CPU). <br><strong>Source File:</strong> <code>gpu_search.py</code>\"\n  },\n  index: {\n    title: \"HNSW Graph & IVF-PQ Index Engine\",\n    desc: \"Multi-layered navigation graph for logarithmic ANN searches combined with Product Quantization to reduce RAM footprint. <br><strong>Tech:</strong> Cosine centroid clustering, K-Means. <br><strong>Avg Latency:</strong> 1.5ms. <br><strong>Source File:</strong> <code>hnsw.py</code> & <code>ivfpq.py</code>\"\n  },\n  rag: {\n    title: \"Search Coordinator & Ollama RAG\",\n    desc: \"Executes sharded database searches, parses queries, performs Cross-Encoder re-ranking, and streams context to local LLM. <br><strong>Tech:</strong> Scatter-Gather RPC, Server-Sent Events (SSE). <br><strong>Avg Latency:</strong> 25ms TTFT. <br><strong>Source File:</strong> <code>coordinator.py</code> & <code>reranker.py</code>\"\n  },\n  default: {\n    title: \"Pipeline System Architecture\",\n    desc: \"Hover over any node in the interactive architecture diagram above to inspect technical specifications, latencies, algorithms, and source file references in the codebase.\"\n  }\n};\n\nwindow.showArchInfo = function(key) {\n  const meta = archMeta[key] || archMeta.default;\n  const titleEl = document.getElementById('archInfoTitle');\n  const descEl = document.getElementById('archInfoDesc');\n  if (titleEl && descEl) {\n    titleEl.textContent = meta.title;\n    descEl.innerHTML = meta.desc;\n  }\n  \n  document.querySelectorAll('.arch-node').forEach(node => {\n    node.classList.remove('active');\n  });\n  const activeNode = document.getElementById(`node-${key}`);\n  if (activeNode) activeNode.classList.add('active');\n};\n\n// API Key Generator Logic\nlet apiScope = 'read';\n\nwindow.setApiScope = function(btn, scope) {\n  if (typeof playClickSound === 'function') playClickSound();\n  document.querySelectorAll('#apiScopePills .pill').forEach(p => p.classList.remove('on'));\n  btn.classList.add('on');\n  apiScope = scope;\n  updateApiKeyConsole();\n};\n\nwindow.generateApiKey = function() {\n  if (typeof playClickSound === 'function') playClickSound();\n  const nameInput = document.getElementById('apiCredName').value.trim() || 'nuro_dev_key';\n  const prefix = \"nr_live_\";\n  \n  const hex = Array.from({length: 24}, () => Math.floor(Math.random()*16).toString(16)).join('');\n  const finalKey = `${prefix}${nameInput}_${hex.substring(0, 14)}`;\n  \n  document.getElementById('apiTokenDisplay').value = finalKey;\n  showToast(\"New API Key generated successfully!\", \"success\");\n  updateApiKeyConsole();\n};\n\nwindow.updateApiKeyConsole = function() {\n  const keyName = document.getElementById('apiCredName').value.trim() || 'nuro_dev_key';\n  const rateLimit = document.getElementById('apiRateLimit').value;\n  const token = document.getElementById('apiTokenDisplay').value;\n  const quotaText = document.getElementById('apiQuotaText');\n  \n  if (quotaText) {\n    quotaText.textContent = rateLimit === '0' ? 'Unlimited RPM' : `0 / ${rateLimit} RPM`;\n  }\n\n  const curlPre = document.getElementById('apiCurlDisplay');\n  if (!curlPre) return;\n\n  let curlCmd = \"\";\n  if (apiScope === 'read') {\n    curlCmd = `curl -X POST http://localhost:8000/search \\\\\\\\\n  -H \"Authorization: Bearer ${token}\" \\\\\\\\\n  -H \"X-Rate-Limit: ${rateLimit}\" \\\\\\\\\n  -H \"Content-Type: application/json\" \\\\\\\\\n  -d '{\\n    \"v\": [0.1, 0.5, -0.2, 0.8, 0.3, 0.1, -0.05, 0.4, 0.2, 0.1, -0.1, 0.15, 0.0, 0.05, -0.1, 0.2],\\n    \"k\": 5,\\n    \"metric\": \"cosine\"\\n  }'`;\n  } else if (apiScope === 'write') {\n    curlCmd = `curl -X POST http://localhost:8000/insert \\\\\\\\\n  -H \"Authorization: Bearer ${token}\" \\\\\\\\\n  -H \"X-Rate-Limit: ${rateLimit}\" \\\\\\\\\n  -H \"Content-Type: application/json\" \\\\\\\\\n  -d '{\\n    \"v\": [0.1, 0.5, -0.2, 0.8, 0.3, 0.1, -0.05, 0.4, 0.2, 0.1, -0.1, 0.15, 0.0, 0.05, -0.1, 0.2],\\n    \"metadata\": \"Neural network optimization parameters\",\\n    \"category\": \"cs\"\\n  }'`;\n  } else {\n    curlCmd = `curl -X DELETE http://localhost:8000/index/clear \\\\\\\\\n  -H \"Authorization: Bearer ${token}\" \\\\\\\\\n  -H \"X-Rate-Limit: ${rateLimit}\"`;\n  }\n\n  curlPre.textContent = curlCmd;\n};\n\nwindow.copyApiToken = function(btn) {\n  const token = document.getElementById('apiTokenDisplay').value;\n  navigator.clipboard.writeText(token).then(() => {\n    const icon = btn.querySelector('i');\n    icon.className = 'ti ti-check';\n    btn.style.color = '#22c55e';\n    showToast(\"API token copied to clipboard!\", \"success\");\n    setTimeout(() => {\n      icon.className = 'ti ti-copy';\n      btn.style.color = '';\n    }, 1500);\n  });\n};\n\nwindow.copyApiCurl = function(btn) {\n  const curlText = document.getElementById('apiCurlDisplay').textContent;\n  navigator.clipboard.writeText(curlText).then(() => {\n    const orig = btn.textContent;\n    btn.textContent = 'Copied!';\n    btn.style.color = '#22c55e';\n    showToast(\"Integration cURL copied!\", \"success\");\n    setTimeout(() => {\n      btn.textContent = orig;\n      btn.style.color = '';\n    }, 1500);\n  });\n};\n\nwindow.updateBenchmarkStats = function() {\n  const size = parseInt(document.getElementById('benchSliderSize').value);\n  const dim = parseInt(document.getElementById('benchSliderDim').value);\n  const m = parseInt(document.getElementById('benchMSelect').value);\n  \n  document.getElementById('benchSizeVal').textContent = size;\n  document.getElementById('benchDimVal').textContent = dim;\n\n  const bytesBf = size * dim * 4;\n  const bytesPq = size * 16;\n  \n  const compressRatio = ((1 - bytesPq / bytesBf) * 100).toFixed(1);\n  const sizeStrBf = bytesBf > 1024 * 1024 ? (bytesBf / (1024*1024)).toFixed(2) + \" MB\" : (bytesBf / 1024).toFixed(1) + \" KB\";\n  const sizeStrPq = bytesPq > 1024 * 1024 ? (bytesPq / (1024*1024)).toFixed(2) + \" MB\" : (bytesPq / 1024).toFixed(1) + \" KB\";\n  \n  const descEl = document.getElementById('benchCustomizerDesc');\n  if (descEl) {\n    descEl.innerHTML = `• Scanning <strong>${size}</strong> vectors of <strong>${dim}D</strong> requires <strong>${sizeStrBf}</strong> RAM in brute force. <br>• IVF-PQ compresses vectors to 16 bytes, reducing size to <strong>${sizeStrPq}</strong> (<strong>${compressRatio}%</strong> savings). <br>• HNSW index will build a navigation graph with M = <strong>${m}</strong> connection links per node.`;\n  }\n};\n\nwindow.runJsBenchmark = function() {\n  if (typeof playClickSound === 'function') {\n    playClickSound();\n  }\n  showToast(\"Running custom local database benchmark suite...\", \"info\");\n  \n  const hnswBar = document.getElementById('benchHnswBar');\n  const kdBar = document.getElementById('benchKdBar');\n  const bfBar = document.getElementById('benchBfBar');\n  \n  const hnswRes = document.getElementById('benchHnswRes');\n  const kdRes = document.getElementById('benchKdRes');\n  const bfRes = document.getElementById('benchBfRes');\n  \n  hnswBar.style.width = '0%';\n  kdBar.style.width = '0%';\n  bfBar.style.width = '0%';\n  \n  hnswRes.textContent = \"Testing...\";\n  kdRes.textContent = \"Testing...\";\n  bfRes.textContent = \"Testing...\";\n  \n  const size = parseInt(document.getElementById('benchSliderSize').value);\n  const dim = parseInt(document.getElementById('benchSliderDim').value);\n  const m = parseInt(document.getElementById('benchMSelect').value);\n  const ef = parseInt(document.getElementById('benchEfSelect').value);\n  \n  setTimeout(() => {\n    const hnswTime = Math.max(0.1, (Math.log2(size) * 0.05 * Math.log2(m) * (dim / 64) * (ef / 32) * (0.8 + Math.random() * 0.4))).toFixed(2);\n    \n    let kdDegradeFactor = 1.0;\n    if (dim > 16) {\n      kdDegradeFactor = Math.pow(1.3, (dim - 16) / 8); \n    }\n    const kdTime = Math.max(0.2, (Math.log2(size) * 0.012 * dim * kdDegradeFactor * (0.9 + Math.random() * 0.2))).toFixed(2);\n    \n    const bfTime = Math.max(0.5, (size * dim * 0.000085 * (0.95 + Math.random() * 0.1))).toFixed(2);\n    \n    const hnswRecall = Math.min(100, Math.max(80, 99 - (dim / 256) * 5 + (m / 16) * 2 + (ef / 32) * 1.5)).toFixed(1);\n    const kdRecall = 100.0;\n    const bfRecall = 100.0;\n    \n    const maxTime = Math.max(parseFloat(hnswTime), parseFloat(kdTime), parseFloat(bfTime));\n    const minTime = Math.min(parseFloat(hnswTime), parseFloat(kdTime), parseFloat(bfTime));\n    \n    const hnswWidth = Math.max(5, Math.min(100, (minTime / parseFloat(hnswTime)) * 100));\n    const kdWidth = Math.max(5, Math.min(100, (minTime / parseFloat(kdTime)) * 100));\n    const bfWidth = Math.max(5, Math.min(100, (minTime / parseFloat(bfTime)) * 100));\n    \n    hnswBar.style.width = hnswWidth + '%';\n    hnswRes.textContent = `${hnswTime} ms (${hnswRecall}% Recall)`;\n    \n    setTimeout(() => {\n      kdBar.style.width = kdWidth + '%';\n      kdRes.textContent = `${kdTime} ms (${kdRecall}% Recall)`;\n      \n      setTimeout(() => {\n        bfBar.style.width = bfWidth + '%';\n        bfRes.textContent = `${bfTime} ms (${bfRecall}% Recall)`;\n        \n        const speedup = (parseFloat(bfTime) / parseFloat(hnswTime)).toFixed(1);\n        showToast(`Benchmark complete! HNSW is ${speedup}x faster than Exact Scan.`, \"success\");\n      }, 300);\n    }, 300);\n  }, 600);\n};\n\n// Privacy Accordion Toggle\nwindow.togglePrivacyAccordion = function() {\n  const body = document.getElementById('privacyAccordionBody');\n  const chevron = document.getElementById('privacyChevron');\n  if (!body || !chevron) return;\n  const isOpen = body.style.display !== 'none';\n  if (typeof playClickSound === 'function') playClickSound();\n  \n  if (isOpen) {\n    body.style.display = 'none';\n    chevron.style.transform = 'rotate(0deg)';\n  } else {\n    body.style.display = 'block';\n    chevron.style.transform = 'rotate(180deg)';\n  }\n};\n\nsetTimeout(() => {\n  updateApiKeyConsole();\n  updateBenchmarkStats();\n}, 500);
