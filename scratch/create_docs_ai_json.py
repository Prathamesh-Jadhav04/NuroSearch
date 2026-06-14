import json
import os

docs_html = """<!-- Stored Contexts Header -->
<span class="section-badge">Stored Contexts</span>
<h2 class="display-header">Documents &amp; Corpus Management</h2>
<p class="section-sub">Upload PDF/TXT documents or insert raw paragraphs. Text is automatically chunked, embedded, and indexed.</p>

<div class="search-grid">
  <!-- Left Column: Add, Upload & Settings -->
  <div class="left-column-container" style="display:flex; flex-direction:column; gap:16px;">
    <!-- Add Document Text -->
    <div class="status-card">
      <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600; margin-bottom:12px;">Add Document Text</h4>
      <input type="text" id="docTitle" placeholder="Document Title (e.g. HNSW Overview)" />
      <textarea id="docText" placeholder="Paste document content paragraphs here..." style="margin-bottom: 8px; min-height: 120px;"></textarea>
      <div class="input-suggestions" style="margin-bottom:12px; display:flex; flex-wrap:wrap; gap:6px; font-size:11px; align-items:center;">
        <span style="color:var(--ink-muted);">Dummy Doc:</span>
        <span class="suggestion-chip" onclick="fillDoc('Binary Tree In CS', 'A binary tree is a tree data structure in which each node has at most two children, which are referred to as the left child and the right child. It is commonly used for efficient searching, expression trees, and binary heaps.')">Binary Tree</span>
        <span class="suggestion-chip" onclick="fillDoc('Sushi History', 'Sushi is a Japanese dish of prepared vinegared rice, usually with some sugar and salt, accompanying a variety of ingredients, such as seafood, often raw, and vegetables. Styles of sushi and its presentation vary widely.')">Sushi</span>
        <span class="suggestion-chip" onclick="fillDoc('HNSW Graph Search', 'Hierarchical Navigable Small World (HNSW) graphs are state-of-the-art structure for approximate nearest neighbor search. It builds a multi-layer graph where layers correspond to different skip list levels, achieving logarithmic search complexity.')">HNSW Search</span>
      </div>
      <button class="btn-primary" id="insertDocBtn" onclick="insertDocument()" style="width:100%; margin-bottom:12px;">
        Embed &amp; Insert Text
      </button>
      
      <div style="border-top:1px solid var(--hairline-soft); margin:12px 0; position:relative;">
        <span style="position:absolute; top: -9px; left:50%; transform:translateX(-50%); background:var(--surface-1); padding:0 10px; font-size:10px; color:var(--ink-muted); text-transform:uppercase;">or</span>
      </div>
      
      <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600; margin-bottom:10px;">Upload File Context</h4>
      <div class="dropzone" id="dropzone" onclick="document.getElementById('docFile').click()">
        <i class="ti ti-cloud-upload" style="font-size:32px; color:var(--accent-blue); margin-bottom:8px;"></i>
        <div class="dropzone-text">Drag &amp; drop PDF/TXT file here</div>
        <div class="dropzone-sub">or click to browse local files (max 10MB)</div>
        <input type="file" id="docFile" accept=".pdf,.txt" style="display:none;" onchange="handleFileSelect(this)" />
      </div>
      <div id="fileInfo" style="display:none; font-size:11px; margin-top:8px; background:var(--surface-2); padding:6px 10px; border-radius:4px; border:1px dashed var(--hairline); justify-content:space-between; align-items:center;">
        <span id="fileName" style="color:var(--ink); font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:80%;">No file selected</span>
        <button class="connect-action-btn" onclick="clearFileSelect(event)" style="color:#ef4444; opacity:1; padding:2px;"><i class="ti ti-x"></i></button>
      </div>
      <button class="btn-secondary" id="uploadDocBtn" onclick="uploadDocument()" style="width:100%; margin-top:10px;">
        Upload &amp; Embed File
      </button>
      
      <div id="insertStatus" style="font-size:11px; color:var(--accent-blue); margin-top:10px; text-align:center;"></div>
    </div>

    <!-- Chunking Configuration -->
    <div class="status-card">
      <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600; margin-bottom:4px;">Chunking Strategy &amp; Bounds</h4>
      <p style="font-size:11px; color:var(--ink-muted); margin-bottom:12px;">Configure document splitting strategies and observe block boundaries in real-time.</p>
      
      <div style="display:flex; flex-direction:column; gap:10px; margin-bottom:12px;">
        <div>
          <div class="section-label" style="margin-bottom:6px;">Chunking Strategy</div>
          <select id="chunkStrategy" onchange="onStrategyChange()" style="width:100%;">
            <option value="fixed" selected>Fixed Size Splitting</option>
            <option value="recursive">Recursive Character Splitting</option>
            <option value="semantic">Semantic Layout Splitting (Simulated)</option>
          </select>
        </div>

        <div id="customRegexContainer" style="display:none;">
          <div class="section-label" style="margin-bottom:6px;">Custom Regex Splitter</div>
          <input type="text" id="customRegexInput" value="[\\.!?]\\s+" placeholder="Regex pattern (e.g. [\\.!?]\\s+)" style="width:100%; font-family: monospace;" oninput="updateChunkingPreview()" />
          <div style="font-size:10px; color:var(--ink-muted); margin-top:3px;">Matches punctuation followed by space to split sentences.</div>
        </div>

        <div class="rag-slider-group">
          <div class="rag-slider-label">
            <span>Chunk Size (words)</span>
            <span id="chunkSizeVal" class="font-mono">15 words</span>
          </div>
          <input type="range" class="rag-input-slider" id="chunkSizeSlider" min="5" max="100" value="15" oninput="updateChunkingPreview()" />
        </div>
        
        <div class="rag-slider-group" id="chunkOverlapContainer">
          <div class="rag-slider-label">
            <span>Overlap (words)</span>
            <span id="chunkOverlapVal" class="font-mono">3 words</span>
          </div>
          <input type="range" class="rag-input-slider" id="chunkOverlapSlider" min="0" max="30" value="3" oninput="updateChunkingPreview()" />
        </div>
      </div>
      
      <div class="section-label" style="margin-bottom:6px;">Live Chunking Preview</div>
      <div class="chunking-preview-box" id="chunkPreview">
        Type or paste text above to see visual chunk ranges.
      </div>
    </div>
  </div>

  <!-- Right Column: Stored Documents, Chunks, Word Cloud, Heatmap -->
  <div style="display:flex; flex-direction:column; gap:16px;">
    <!-- Stored Documents -->
    <div class="status-card" style="margin-bottom:0;">
      <div class="section-title" style="margin-top:0;">Stored Documents</div>
      <div id="docList" style="max-height: 200px; overflow-y: auto; padding-right: 6px; margin-bottom: 0;">
        <div style="color:var(--ink-muted); font-size:13px; text-align:center; padding:16px; background:var(--surface-1); border-radius:var(--radius-xl); border:1px solid var(--hairline);">
          No documents found.
        </div>
      </div>
    </div>

    <!-- Document Analytics: Word Cloud & Heatmap -->
    <div class="status-card" style="margin-bottom:0;">
      <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600; margin-bottom:4px;">Document Analytics</h4>
      <p style="font-size:11px; color:var(--ink-muted); margin-bottom:12px;">Visual analytics of document terms and vector space density.</p>
      
      <div style="display:flex; flex-direction:column; gap:12px;">
        <div>
          <div class="section-label" style="margin-bottom:6px;">Live Word Cloud</div>
          <div class="word-cloud-wrapper" style="position:relative;">
            <canvas id="wordCloudCanvas" style="width:100%; height:140px; background:rgba(0,0,0,0.2); border-radius:var(--radius-md); border:1px solid var(--hairline); display:block;"></canvas>
            <div id="wordCloudEmpty" style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center; color:var(--ink-muted); font-size:12px; pointer-events:none;">Type document text to generate word cloud</div>
          </div>
        </div>

        <div>
          <div class="section-label" style="margin-bottom:6px;">Context Coverage Heatmap (Vector Density)</div>
          <div class="heatmap-wrapper" style="position:relative;">
            <canvas id="heatmapCanvas" style="width:100%; height:120px; background:rgba(0,0,0,0.2); border-radius:var(--radius-md); border:1px solid var(--hairline); display:block;"></canvas>
            <div id="heatmapEmpty" style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center; color:var(--ink-muted); font-size:12px; pointer-events:none;">Select a document to visualize chunk vector density</div>
            <div id="heatmapTooltip" class="heatmap-tooltip" style="display:none; position:fixed; background:rgba(15,15,15,0.95); border:1px solid var(--hairline); border-radius:6px; padding:8px 12px; z-index:1000; pointer-events:none; font-size:11px; color:var(--ink); box-shadow:var(--shadow-premium); max-width:250px; line-height:1.4;"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Chunk Explorer -->
    <div class="status-card" style="margin-bottom:0;">
      <div class="section-title" style="margin-top:0;">Corpus Chunks Explorer</div>
      <p class="section-sub">Browse embedded passages, their SQLite indices, word counts, and raw vector properties.</p>
      <div id="chunkListContainer" style="max-height: 200px; overflow-y: auto; padding-right: 6px;">
        <div style="color:var(--ink-muted); font-size:12px; text-align:center; padding:16px; background:var(--surface-1); border-radius:var(--radius-md); border:1px solid var(--hairline);">
          Select a document above to browse its chunks.
        </div>
      </div>
    </div>
  </div>
</div>"""

docs_js = """// 1. Chunking Strategy Change & Live Preview
function onStrategyChange() {
  const strategy = document.getElementById('chunkStrategy').value;
  const regexContainer = document.getElementById('customRegexContainer');
  const overlapContainer = document.getElementById('chunkOverlapContainer');
  
  if (strategy === 'fixed') {
    regexContainer.style.display = 'block';
    document.getElementById('customRegexInput').value = "[\\\\.!?]\\\\s+";
    overlapContainer.style.display = 'flex';
  } else if (strategy === 'recursive') {
    regexContainer.style.display = 'block';
    document.getElementById('customRegexInput').value = "\\\\n\\\\n|\\\\n|\\\\s+";
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
      tokens = text.split(/\\s+/);
    }
    
    for (let i = 0; i < tokens.length; i += (size - overlap)) {
      chunks.push(tokens.slice(i, i + size).join(customReg ? ' ' : ' '));
      if (i + size >= tokens.length) break;
    }
  } else if (strategy === 'recursive') {
    const delimiters = regexVal && isValidRegex ? regexVal.split('|') : ["\\n\\n", "\\n", " ", ""];
    
    function recursiveSplit(txt, dIdx) {
      if (dIdx >= delimiters.length) return [txt];
      const delim = delimiters[dIdx];
      let parts = delim === "" ? txt.split("") : txt.split(delim);
      
      let result = [];
      for (let part of parts) {
        const words = part.trim().split(/\\s+/).length;
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
      const pWords = p.trim().split(/\\s+/).length;
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
    const sentences = text.match(/[^.!?]+[.!?]+(\\s+|$)/g) || [text];
    let currentChunk = [sentences[0]];
    
    function getJaccardSimilarity(s1, s2) {
      const w1 = new Set((s1 || "").toLowerCase().match(/\\w+/g) || []);
      const w2 = new Set((s2 || "").toLowerCase().match(/\\w+/g) || []);
      if (w1.size === 0 || w2.size === 0) return 0;
      const intersection = new Set([...w1].filter(x => w2.has(x)));
      const union = new Set([...w1, ...w2]);
      return intersection.size / union.size;
    }
    
    for (let i = 1; i < sentences.length; i++) {
      const sim = getJaccardSimilarity(sentences[i-1], sentences[i]);
      const currentWordCount = currentChunk.join(" ").split(/\\s+/).length;
      
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
  
  const rawWords = text.toLowerCase().match(/\\b[a-zA-Z]{3,15}\\b/g) || [];
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
          <span>Words: ${hovered.chunk.metadata.split(/\\s+/).length}</span>
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
    const joinedText = documentChunks.map(c => c.metadata).join('\\n\\n');
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
});"""

ai_html = """<!-- Local RAG Agent Header -->
<span class="section-badge">Local RAG Agent</span>
<h2 class="display-header">Ask Local AI (RAG Pipeline)</h2>
<p class="section-sub">Query your document corpus. The local AI will answer using retrieved HNSW context chunks.</p>

<div class="rag-layout">
  <!-- RAG Chat Core Column -->
  <div>
    <!-- Single Chat View & Side-by-Side Compare View Wrapper -->
    <div id="chatStageContainer" style="position:relative; width:100%;">
      <!-- Standard Single Model Chat -->
      <div class="status-card chat-history-container" id="chatHistory" style="height: 380px;">
        <div class="chat-bubble ai">
          Hello PJ! Ask a question about your uploaded documents or NuroSearch capabilities...
        </div>
      </div>
      
      <!-- Side-by-Side Compare Mode Panel -->
      <div id="compareContainer" class="compare-container" style="display:none;">
        <!-- Qwen-0.5B -->
        <div class="compare-column">
          <div class="model-header">
            <div class="model-name">
              <i class="ti ti-cpu"></i> Qwen-0.5B
            </div>
            <span class="model-badge qwen-badge">Compact / Fast</span>
          </div>
          <div class="model-response-container" id="qwenResponse">
            <div style="color:var(--ink-muted); font-style:italic;">Awaiting question...</div>
          </div>
        </div>
        
        <!-- Llama-3-8B -->
        <div class="compare-column">
          <div class="model-header">
            <div class="model-name">
              <i class="ti ti-layers-difference"></i> Llama-3-8B
            </div>
            <span class="model-badge llama-badge">Balanced</span>
          </div>
          <div class="model-response-container" id="llamaResponse">
            <div style="color:var(--ink-muted); font-style:italic;">Awaiting question...</div>
          </div>
        </div>
        
        <!-- DeepSeek-R1 Dist. -->
        <div class="compare-column">
          <div class="model-header">
            <div class="model-name">
              <i class="ti ti-brain"></i> DeepSeek-R1 (Dist.)
            </div>
            <span class="model-badge deepseek-badge">Reasoning</span>
          </div>
          <div class="model-response-container" id="deepseekResponse">
            <div style="color:var(--ink-muted); font-style:italic;">Awaiting question...</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Input Box Card -->
    <div style="background: var(--surface-trans); border: 1px solid var(--border-trans); border-radius: var(--radius-xl); padding: 16px; margin-top: 12px; box-shadow: var(--shadow-premium);">
      <textarea id="ragQuestion" rows="2" placeholder="Type your question... (e.g. Explain binary tree or how does HNSW work?)" style="margin-bottom: 8px;"></textarea>
      <div class="input-suggestions" style="margin-bottom:12px; display:flex; flex-wrap:wrap; gap:6px; font-size:11px; align-items:center;">
        <span style="color:var(--ink-muted);">Ask:</span>
        <span class="suggestion-chip" onclick="fillRAG('Explain binary tree')">Explain binary tree</span>
        <span class="suggestion-chip" onclick="fillRAG('What is sushi?')">What is sushi?</span>
        <span class="suggestion-chip" onclick="fillRAG('How does HNSW work?')">How does HNSW work?</span>
      </div>
      <div style="display:flex; gap:10px;">
        <button class="btn-primary" id="askBtn" onclick="askAI()" style="flex:1;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          Ask AI
        </button>
      </div>
    </div>
  </div>
  
  <!-- RAG Controls Column -->
  <div class="status-card">
    <h4 style="font-family:'Outfit'; font-size:14px; font-weight:600; margin-bottom:14px;">RAG Configuration</h4>
    
    <!-- Multi-Model Compare mode -->
    <div class="toggle-container" style="padding:10px; margin-bottom:10px;">
      <div class="toggle-switch" id="multiCompareToggle" onclick="toggleMultiModelCompare()"></div>
      <span class="toggle-label">
        <strong>Multi-Model Compare</strong>
        Compare 3 local LLMs side-by-side
      </span>
    </div>

    <!-- Query Rewriting Toggle -->
    <div class="toggle-container" style="padding:10px; margin-bottom:10px;">
      <div class="toggle-switch" id="rewriteToggle" onclick="this.classList.toggle('on')"></div>
      <span class="toggle-label">
        <strong>Query Expansion</strong>
        LLM expands query for better search
      </span>
    </div>
    
    <!-- GraphRAG Toggle -->
    <div class="toggle-container" style="padding:10px; margin-bottom:10px;">
      <div class="toggle-switch" id="graphToggle" onclick="this.classList.toggle('on')"></div>
      <span class="toggle-label">
        <strong>GraphRAG (Neo4j)</strong>
        Enrich context with Knowledge Graph facts
      </span>
    </div>
    
    <!-- Cross-Encoder Re-ranking Toggle -->
    <div class="toggle-container" style="padding:10px; margin-bottom:14px;">
      <div class="toggle-switch" id="rerankToggle" onclick="this.classList.toggle('on')"></div>
      <span class="toggle-label">
        <strong>Cross-Encoder Re-ranking</strong>
        Neural precision re-sorting
      </span>
    </div>
    
    <!-- Live Cost and Token Estimator -->
    <div class="estimator-panel" style="margin-bottom:16px;">
      <div style="font-family:'Outfit'; font-size:11px; font-weight:600; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
        <span style="color:var(--ink-muted); text-transform:uppercase; letter-spacing:0.5px;">Token &amp; Cost Estimator</span>
        <span class="res-badge" style="font-size:9px; background:rgba(0,153,255,0.08); color:var(--accent-blue); padding:1px 6px;">Live</span>
      </div>
      <div style="display:flex; flex-direction:column; gap:5px; font-size:11px;">
        <div style="display:flex; justify-content:space-between;">
          <span style="color:var(--ink-muted);">Prompt Tokens:</span>
          <span id="promptTokens" class="font-mono">0 tokens</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
          <span style="color:var(--ink-muted);">Completion Tokens:</span>
          <span id="completionTokens" class="font-mono">0 tokens</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-top:1px solid var(--hairline-soft); padding-top:5px; font-weight:600; font-size:11.5px; margin-top:2px;">
          <span style="color:var(--primary);">Est. Cost:</span>
          <span id="estimatedCost" class="font-mono" style="color:#10b981;">$0.00000</span>
        </div>
      </div>
    </div>

    <!-- Active Context Inspector -->
    <div class="active-context-inspector" style="margin-bottom:14px; border-top:1px solid var(--hairline-soft); padding-top:14px;">
      <h4 style="font-family:'Outfit'; font-size:12px; font-weight:600; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;">
        <span>Active Context Inspector</span>
        <span id="inspectorCount" style="font-size:9px; color:var(--ink-muted); font-weight:normal; font-family:monospace;">3 active chunks</span>
      </h4>
      <p style="font-size:10px; color:var(--ink-muted); margin-bottom:8px; line-height:1.3;">Retrieved passages. Toggle checkbox to inject or purge from context payload.</p>
      <div id="inspectorCards" style="max-height:170px; overflow-y:auto; display:flex; flex-direction:column; gap:6px; padding-right:4px;">
        <!-- Filled on startup or when RAG search executes -->
      </div>
    </div>
    
    <div class="section-label">Context Limit (Top-K Chunks)</div>
    <select id="ragK" style="margin-bottom:12px;">
      <option value="2">Retrieve Top 2</option>
      <option value="3" selected>Retrieve Top 3</option>
      <option value="5">Retrieve Top 5</option>
    </select>
    
    <div class="section-label">First-Stage Recall Count</div>
    <select id="ragKRetrieve" style="margin-bottom:12px;">
      <option value="10">Recall 10 chunks</option>
      <option value="20" selected>Recall 20 chunks</option>
      <option value="30">Recall 30 chunks</option>
      <option value="50">Recall 50 chunks</option>
    </select>
    
    <div class="section-label">Neural Reranker Model</div>
    <select id="rerankModel" style="margin-bottom:12px;">
      <option value="bge-reranker-base">BAAI/bge-reranker-base</option>
      <option value="jina-reranker-v1-turbo">jina-reranker-v1-turbo</option>
    </select>

    <!-- Prompt Templates -->
    <div class="section-label">System Prompt Persona</div>
    <select id="systemPromptTemplate" onchange="updateSystemPersona(this.value)" style="margin-bottom: 12px;">
      <option value="standard">Standard RAG Assistant</option>
      <option value="programmer">Guru Software Engineer</option>
      <option value="summarizer">Concise Academic Editor</option>
      <option value="sql_expert">Database / SQL Expert</option>
    </select>

    <!-- RAG Parameters Panel -->
    <div class="rag-param-panel" style="margin-bottom: 12px;">
      <div class="rag-slider-group">
        <div class="rag-slider-label">
          <span>LLM Temperature</span>
          <span id="ragTempLabel" class="font-mono">0.3</span>
        </div>
        <input type="range" class="rag-input-slider" id="ragTempSlider" min="0.0" max="1.0" step="0.1" value="0.3" oninput="document.getElementById('ragTempLabel').textContent=this.value" />
      </div>
      <div class="rag-slider-group">
        <div class="rag-slider-label">
          <span>Top-P Sampling</span>
          <span id="ragTopPLabel" class="font-mono">0.85</span>
        </div>
        <input type="range" class="rag-input-slider" id="ragTopPSlider" min="0.5" max="1.0" step="0.05" value="0.85" oninput="document.getElementById('ragTopPLabel').textContent=this.value" />
      </div>
    </div>

    <!-- Citation Source Reference Panel -->
    <div class="citation-reference-panel" id="citationRefPanel" style="display:none;">
      <h4 style="font-family:'Outfit'; font-size:12px; font-weight:600; margin-bottom:6px; color:var(--accent-blue);">Citation Source Inspector</h4>
      <div id="citationRefContent" style="font-size:11px; line-height:1.4; color:var(--ink-muted);">
        Click any citation link in the AI answer to inspect its original document source context.
      </div>
    </div>
  </div>
</div>"""

ai_js = """// 1. Toggle Multi-Model Compare Mode
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
      contextWords += text.split(/\\s+/).length;
    }
  });
  
  const countEl = document.getElementById('inspectorCount');
  if (countEl) countEl.textContent = `${checkedCount} active chunk${checkedCount === 1 ? '' : 's'}`;
  
  const questionWords = question ? question.split(/\\s+/).length : 0;
  
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
    
    const qwWords = qwenText.includes('Awaiting') || qwenText.includes('Reasoning') ? 0 : qwenText.split(/\\s+/).length;
    const llWords = llamaText.includes('Awaiting') || llamaText.includes('Reasoning') ? 0 : llamaText.split(/\\s+/).length;
    const dsWords = deepseekText.includes('Awaiting') || deepseekText.includes('Reasoning') ? 0 : deepseekText.split(/\\s+/).length;
    
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
    const words = cleanSingleText.split(/\\s+/).length;
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
      thinking += `\\n4. Context is empty. Relying on model parametric knowledge base.\\n5. Structure output with warning alert.`;
      return `<think>\\n${thinking}\\n</think>\\n\\n### DeepSeek-R1 (Dist.) Synthesis\\n\\n> [!WARNING]\\n> Zero context chunks are checked. This answer is synthesized solely from pre-trained parameters.\\n\\nFor **${question}**, local documents are unreferenced. Grounding vector retrieval is recommended to secure factual consistency.`;
    }
    
    thinking += `\\n4. Selected text contains: "${contextText.substring(0, 70)}..."\\n5. Isolating crucial semantic elements: "${fact1.substring(0, 40)}"\\n6. Organizing facts logically into definition, system relevance, and cost complexity.`;
    return `<think>\\n${thinking}\\n</think>\\n\\n### DeepSeek-R1 (Dist.) Analytical Response\\n\\nBased on the active HNSW retrieval blocks, we analyze "${question}" as follows:\\n\\n#### I. Core Architectural Foundation\\n${fact1}\\n\\n#### II. Mechanism Analysis\\n${fact2}\\n\\n*Conclusion*: This structural configuration is verified by local DB index state.`;
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
    let formatted = txt.replace(/<think>([\\s\\S]*?)<\\/think>/g, (match, p1) => {
      return `<div class="think-block">
        <div class="think-header"><i class="ti ti-brain"></i> Reasoning Process</div>
        <div class="think-content">${p1.trim().replace(/\\n/g, '<br>')}</div>
      </div>`;
    });
    return formatted.replace(/\\n/g, '<br>');
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
                const lines = buffer.split('\\n');
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
});"""

css = """/* Word Cloud Canvas Styling */
.word-cloud-wrapper {
  margin-top: 6px;
  position: relative;
  overflow: hidden;
}
#wordCloudCanvas {
  transition: border-color 0.2s ease;
}
#wordCloudCanvas:hover {
  border-color: var(--trans-white-08);
}

/* Heatmap Grid & Tooltip Styling */
.heatmap-wrapper {
  margin-top: 6px;
  position: relative;
  overflow: hidden;
}
#heatmapCanvas {
  transition: border-color 0.2s ease;
}
#heatmapCanvas:hover {
  border-color: var(--trans-white-08);
}
.heatmap-tooltip {
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-color: var(--hairline-soft);
  animation: fadeIn 0.15s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

/* Multi-Model Compare Layout */
.compare-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  width: 100%;
  box-sizing: border-box;
}
@media (max-width: 900px) {
  .compare-container {
    grid-template-columns: 1fr;
    height: auto;
    max-height: 800px;
    overflow-y: auto;
  }
}
.compare-column {
  background: var(--surface-1);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 380px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}
.model-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--hairline-soft);
  padding-bottom: 8px;
  margin-bottom: 12px;
}
.model-name {
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
  font-size: 13px;
  color: var(--primary);
  display: flex;
  align-items: center;
  gap: 6px;
}
.model-badge {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: var(--radius-pill);
  font-family: monospace;
}
.qwen-badge { background: rgba(0, 153, 255, 0.1); color: #0099ff; }
.llama-badge { background: rgba(106, 76, 245, 0.1); color: #8a6efc; }
.deepseek-badge { background: rgba(212, 77, 240, 0.1); color: #e46bf0; }

.model-response-container {
  flex: 1;
  overflow-y: auto;
  font-size: 12px;
  line-height: 1.5;
  color: var(--ink);
  padding-right: 4px;
}

/* DeepSeek Reason/Think Block styling */
.think-block {
  background: rgba(106, 76, 245, 0.04);
  border-left: 3px solid var(--grad-violet);
  border-radius: var(--radius-xs);
  padding: 10px 12px;
  margin-bottom: 12px;
  font-size: 11px;
}
.think-header {
  font-weight: 600;
  color: #a78bfa;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'Outfit', sans-serif;
}
.think-content {
  color: var(--ink-muted);
  font-style: italic;
}

/* Estimator Panel */
.estimator-panel {
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-md);
  margin-top: 10px;
}

/* Active Context Inspector Cards styling */
.active-context-inspector {
  margin-bottom: 14px;
}
.inspector-card {
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid var(--hairline-soft);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.inspector-card:hover {
  border-color: var(--hairline);
  background: rgba(255, 255, 255, 0.03);
}
.inspector-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.inspector-checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--primary);
  cursor: pointer;
  user-select: none;
  min-width: 0;
}
.inspector-checkbox-label input[type="checkbox"] {
  accent-color: var(--accent-blue);
  cursor: pointer;
}
.inspector-title-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 140px;
}
.inspector-card-body {
  font-size: 10px;
  color: var(--ink-muted);
  line-height: 1.4;
  max-height: 48px;
  overflow-y: hidden;
  padding-left: 19px;
  cursor: pointer;
  transition: max-height 0.2s ease-out;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}
.inspector-card-body:hover {
  color: var(--ink);
}
.inspector-badge {
  font-size: 9px;
  font-family: monospace;
  font-weight: bold;
}

/* Shimmer Loading animation for Multi-Model */
.shimmer-line {
  height: 12px;
  background: linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.03) 75%);
  background-size: 200% 100%;
  animation: loadingShimmer 1.5s infinite;
  border-radius: var(--radius-xs);
}
@keyframes loadingShimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}"""

payload = {
    "docs_html": docs_html,
    "docs_js": docs_js,
    "ai_html": ai_html,
    "ai_js": ai_js,
    "css": css
}

os.makedirs(r"D:\My Own Artificial Intelligance\scratch", exist_ok=True)
with open(r"D:\My Own Artificial Intelligance\scratch\docs_ai.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)

print("docs_ai.json successfully created!")
