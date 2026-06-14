import json
import os

# Define CSS styles for both tabs
css_content = """
/* Circular Dials styling */
.dials-container {
  display: flex;
  justify-content: space-around;
  align-items: center;
  border-top: 1px solid var(--hairline-soft);
  padding-top: 12px;
  margin-top: 12px;
  margin-bottom: 12px;
}
.dial-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}
.dial-box svg {
  transform: rotate(-90deg);
}
.dial-box circle {
  fill: none;
  stroke-width: 4px;
}
.dial-box .dial-bg {
  stroke: var(--hairline);
}
.dial-box .dial-fill {
  stroke-dasharray: 150.8;
  stroke-dashoffset: 150.8;
  transition: stroke-dashoffset 0.4s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.4s ease;
}
.dial-label {
  position: absolute;
  top: 18px;
  left: 0;
  right: 0;
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  color: var(--ink);
}

/* Chaos Monkey Console */
.chaos-console {
  background: rgba(0, 0, 0, 0.85) !important;
  border: 1px solid var(--hairline) !important;
  color: #10b981 !important;
  font-family: 'JetBrains Mono', monospace;
  padding: 10px;
  border-radius: 8px;
  height: 110px;
  overflow-y: auto;
  font-size: 10px;
  line-height: 1.5;
  box-shadow: inset 0 2px 8px rgba(0,0,0,0.8);
  text-align: left;
}
.chaos-console .log-err {
  color: #ff4b4b;
}
.chaos-console .log-warn {
  color: #ffa726;
}
.chaos-console .log-info {
  color: #0099ff;
}
.chaos-console .log-success {
  color: #10b981;
}

/* Chaos Monkey Buttons */
.chaos-btn {
  background: var(--surface-1);
  border: 1px solid var(--hairline);
  color: var(--ink);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: 'Outfit', sans-serif;
  font-weight: 500;
}
.chaos-btn:hover {
  background: var(--surface-2);
  border-color: var(--ink-muted);
  transform: translateY(-1px);
}
.chaos-btn:active {
  transform: translateY(0);
}

/* Raft Ledger Table */
#raftTableContainer::-webkit-scrollbar {
  width: 4px;
}
#raftTableContainer::-webkit-scrollbar-track {
  background: transparent;
}
#raftTableContainer::-webkit-scrollbar-thumb {
  background: var(--hairline);
  border-radius: 2px;
}
#raftTableContainer table th, #raftTableContainer table td {
  border-bottom: 1px solid var(--hairline-soft);
  padding: 6px 8px;
}
#raftTableContainer table tbody tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

/* Ledger Badges */
.ledger-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 8px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  text-align: center;
  min-width: 65px;
}
.ledger-uncommitted {
  background: rgba(255, 167, 38, 0.1);
  color: #ffa726;
  border: 1px solid rgba(255, 167, 38, 0.2);
}
.ledger-replicated {
  background: rgba(0, 153, 255, 0.1);
  color: #0099ff;
  border: 1px solid rgba(0, 153, 255, 0.2);
}
.ledger-committed {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.2);
}
.ledger-offline {
  background: rgba(255, 75, 75, 0.1);
  color: #ff4b4b;
  border: 1px solid rgba(255, 75, 75, 0.2);
}
.ledger-stale {
  background: rgba(142, 142, 147, 0.1);
  color: #8e8e93;
  border: 1px solid rgba(142, 142, 147, 0.2);
}

/* System Architecture Diagram Container */
.arch-diagram-wrapper {
  position: relative;
  border: 1px solid var(--hairline);
  background: var(--surface-trans);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 1.75rem;
}
.arch-viewport-container {
  width: 100%;
  height: 280px;
  cursor: grab;
  overflow: hidden;
  position: relative;
}
.arch-viewport-container:active {
  cursor: grabbing;
}
.arch-controls {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  gap: 6px;
  z-index: 10;
}
.arch-ctrl-btn {
  width: 28px;
  height: 28px;
  background: var(--surface-2);
  border: 1px solid var(--hairline);
  border-radius: 6px;
  color: var(--ink);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
}
.arch-ctrl-btn:hover {
  background: var(--primary);
  color: var(--on-primary);
  border-color: var(--primary);
}

/* SVG Node Interactivity */
.arch-node {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}
.arch-node:hover {
  filter: drop-shadow(0 0 8px rgba(0, 153, 255, 0.6));
}
.arch-node.active {
  filter: drop-shadow(0 0 12px rgba(212, 77, 240, 0.8));
}

/* SVG Connection Heartbeats & Lines */
.heartbeat-active {
  stroke-dasharray: 4;
  animation: svgHeartbeat 1.5s linear infinite;
  stroke: var(--accent-blue);
  stroke-width: 2px;
}
.heartbeat-partitioned {
  stroke-dasharray: 2 4;
  stroke: #ffa726;
  stroke-width: 1.5px;
  opacity: 0.4;
  animation: none;
}
.heartbeat-broken {
  stroke: #ff4b4b;
  stroke-width: 1px;
  stroke-dasharray: 1 5;
  opacity: 0.2;
  animation: none;
}
@keyframes svgHeartbeat {
  to {
    stroke-dashoffset: -20;
  }
}

/* Arch Info Card */
.arch-info-card {
  border-top: 1px solid var(--hairline);
  background: rgba(0, 0, 0, 0.25);
  padding: 16px;
  text-align: left;
  min-height: 90px;
}
.arch-info-title {
  font-family: 'Outfit', sans-serif;
  font-size: 13px;
  font-weight: 700;
  color: var(--primary);
  margin-bottom: 4px;
}
.arch-info-desc {
  font-size: 11.5px;
  color: var(--ink-muted);
  line-height: 1.5;
}

/* API Key Console Container */
.api-key-console {
  display: grid;
  grid-template-columns: 1.2fr 1.8fr;
  gap: 20px;
  border: 1px solid var(--hairline);
  background: var(--surface-trans);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 1.75rem;
  text-align: left;
}
@media (max-width: 768px) {
  .api-key-console {
    grid-template-columns: 1fr;
  }
}
.api-field-group {
  margin-bottom: 14px;
}
.api-field-group label {
  display: block;
  font-size: 10px;
  font-weight: 700;
  color: var(--ink-muted);
  text-transform: uppercase;
  margin-bottom: 6px;
}
.api-input-text {
  width: 100%;
  background: var(--input-bg);
  border: 1px solid var(--input-border);
  color: var(--ink);
  padding: 8px 12px;
  font-size: 12px;
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
}
.api-input-text:focus {
  background: var(--input-bg-focus);
  border-color: var(--accent-blue);
  outline: none;
}

/* Sliders customizer styling */
.customizer-slider-group {
  margin-bottom: 14px;
  text-align: left;
}
.customizer-slider-header {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-muted);
  margin-bottom: 4px;
}
.customizer-slider-val {
  font-family: 'JetBrains Mono', monospace;
  color: var(--ink);
  font-weight: 700;
}
.customizer-input-range {
  width: 100%;
  height: 4px;
  background: var(--surface-2);
  border-radius: 2px;
  outline: none;
  -webkit-appearance: none;
}
.customizer-input-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--primary);
  cursor: pointer;
  transition: transform 0.1s ease;
}
.customizer-input-range::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

/* Cluster Sim Grid */
.cluster-sim-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

/* Privacy Accordion styling */
.privacy-accordion-header {
  border: 1px solid var(--hairline);
  background: var(--surface-trans);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s ease;
  margin-bottom: 12px;
  text-align: left;
}
.privacy-accordion-header:hover {
  background: var(--surface-2);
  border-color: var(--ink-muted);
}
.privacy-accordion-body {
  border: 1px solid var(--hairline);
  border-top: none;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 0 0 8px 8px;
  padding: 20px;
  margin-top: -12px;
  margin-bottom: 1.75rem;
  text-align: left;
  line-height: 1.6;
}
.privacy-item {
  margin-bottom: 16px;
}
.privacy-item:last-child {
  margin-bottom: 0;
}
.privacy-item-title {
  font-family: 'Outfit', sans-serif;
  font-size: 12.5px;
  font-weight: 700;
  color: var(--primary);
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.privacy-item-desc {
  font-size: 11.5px;
  color: var(--ink-muted);
}
"""

cluster_html = """
        <span class="section-badge">Distributed System</span>
        <h2 class="display-header">Worker Nodes & Consensus Cluster</h2>
        <p class="section-sub">Monitor active sharded vector workers, Raft consensus roles, and view local index sizes.</p>
        
        <!-- Coordinator Health Status -->
        <div class="status-card grad-spot-card-violet" style="margin-bottom: 24px; padding: 20px;">
          <div class="cluster-header-row" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
              <h3 style="font-family:'Outfit'; font-size:18px; font-weight:700; margin-bottom:4px; display:flex; align-items:center; gap:8px;">
                <i class="ti ti-binary" style="color:var(--grad-violet);"></i> Coordinator Node Status
              </h3>
              <p style="font-size:12px; color:var(--ink-muted);" id="coordinatorHost">Host: Checking...</p>
            </div>
            <div style="display:flex; align-items:center; gap:16px; flex-wrap:wrap;">
              <!-- Manual Toggle -->
              <label class="switch-container size-lg">
                <span class="switch-label size-lg" style="color:var(--switch-label-on);" id="toggle-label-coordinator">ON</span>
                <input type="checkbox" id="toggle-checkbox-coordinator" checked onclick="toggleNode('coordinator')" style="display:none;" />
                <div class="switch-slider size-lg" id="slider-coordinator" style="background:var(--switch-track-on);">
                  <div class="switch-knob size-lg" id="knob-coordinator" style="left:18px;"></div>
                </div>
              </label>
              
              <span class="res-badge" id="coordinatorStatus" style="background:#00ff66; color:#000; font-weight:600; font-size:11px; margin-bottom:0; padding:6px 12px; border-radius:20px; text-transform:uppercase; letter-spacing:0.5px;">Checking...</span>
              <button class="btn-secondary" onclick="fetchClusterHealth()" style="padding:6px 12px; font-size:11px; border-radius:20px;">Refresh Cluster</button>
            </div>
          </div>
          <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:16px; margin-top:20px; border-top:1px solid var(--hairline-soft); padding-top:16px;">
            <div>
              <div style="font-size:11px; color:var(--ink-muted); text-transform:uppercase; margin-bottom:4px;">Routing Algorithm</div>
              <div style="font-weight:600; font-family:monospace; font-size:13px; color:var(--ink);">Consistent Hashing (MD5)</div>
            </div>
            <div>
              <div style="font-size:11px; color:var(--ink-muted); text-transform:uppercase; margin-bottom:4px;">Distributed Consensus</div>
              <div style="font-weight:600; font-family:monospace; font-size:13px; color:var(--ink);">Raft (pysyncobj)</div>
            </div>
            <div>
              <div style="font-size:11px; color:var(--ink-muted); text-transform:uppercase; margin-bottom:4px;">Sharding Strategy</div>
              <div style="font-weight:600; font-family:monospace; font-size:13px;">Scatter-Gather (Parallel Query)</div>
            </div>
          </div>
        </div>

        <!-- Worker Grid -->
        <h3 style="font-family:'Outfit'; font-size:16px; font-weight:600; margin-bottom:12px; color:var(--ink);">Active Cluster Workers</h3>
        <div class="worker-grid" id="workerContainer" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:20px; margin-bottom:24px;">
          <!-- Worker-1 Card -->
          <div class="status-card" id="card-worker-1" style="border:1px solid var(--border-trans); transition:all 0.3s ease;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600;"><i class="ti ti-server" style="margin-right:6px; color:var(--accent-blue);"></i>worker-1</h4>
              
              <div style="display:flex; align-items:center; gap:8px;">
                <!-- Manual Toggle -->
                <label class="switch-container size-sm">
                  <span class="switch-label size-sm" style="color:var(--switch-label-on);" id="toggle-label-worker-1">ON</span>
                  <input type="checkbox" id="toggle-checkbox-worker-1" checked onclick="toggleNode('worker-1')" style="display:none;" />
                  <div class="switch-slider size-sm" id="slider-worker-1" style="background:var(--switch-track-on);">
                    <div class="switch-knob size-sm" id="knob-worker-1" style="left:15px;"></div>
                  </div>
                </label>
                <span class="res-badge" id="status-worker-1" style="background:#ff4b4b; color:#fff; font-size:10px; margin:0; padding:3px 8px; border-radius:10px;">Offline</span>
              </div>
            </div>
            <div style="font-size:12px; color:var(--ink-muted); margin-bottom:12px;">
              <div>API: <span style="font-family:monospace;">http://127.0.0.1:8081</span></div>
              <div>Raft: <span style="font-family:monospace;">8181</span></div>
            </div>
            <div style="border-top:1px solid var(--hairline-soft); padding-top:10px; margin-bottom:14px; font-size:12px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">
              <div>
                <span style="font-size:10px; color:var(--ink-muted); text-transform:uppercase;">Role</span>
                <div id="role-worker-1" style="font-weight:600; font-family:monospace;">—</div>
              </div>
              <div>
                <span style="font-size:10px; color:var(--ink-muted); text-transform:uppercase;">Vectors</span>
                <div id="vec-worker-1" style="font-weight:600; font-family:monospace;">—</div>
              </div>
              <div>
                <span style="font-size:10px; color:var(--ink-muted); text-transform:uppercase;">Log Size</span>
                <div id="log-worker-1" style="font-weight:600; font-family:monospace;">—</div>
              </div>
            </div>
            
            <!-- Circular Telemetry Dials -->
            <div class="dials-container">
              <div class="dial-box">
                <svg width="56" height="56" viewBox="0 0 60 60">
                  <circle class="dial-bg" cx="30" cy="30" r="24"></circle>
                  <circle class="dial-fill" id="dial-fill-cpu-worker-1" cx="30" cy="30" r="24" stroke="var(--accent-blue)"></circle>
                </svg>
                <div class="dial-label" id="cpu-val-worker-1">0%</div>
                <span style="font-size: 8px; color: var(--ink-muted); margin-top: 4px; text-transform: uppercase; font-weight: 600;">CPU</span>
              </div>
              <div class="dial-box">
                <svg width="56" height="56" viewBox="0 0 60 60">
                  <circle class="dial-bg" cx="30" cy="30" r="24"></circle>
                  <circle class="dial-fill" id="dial-fill-mem-worker-1" cx="30" cy="30" r="24" stroke="var(--grad-violet)"></circle>
                </svg>
                <div class="dial-label" id="mem-val-worker-1">0%</div>
                <span style="font-size: 8px; color: var(--ink-muted); margin-top: 4px; text-transform: uppercase; font-weight: 600;">Memory</span>
              </div>
            </div>

            <div style="background:var(--code-bg); border-radius:6px; padding:8px; position:relative; border:1px solid var(--hairline-soft);">
              <button onclick="copyText(this, 'python worker.py --port 8081 --node-id worker-1 --raft-host 127.0.0.1 --raft-port 8181 --partners 127.0.0.1:8182,127.0.0.1:8183')" style="position:absolute; right:6px; top:6px; background:none; border:none; color:var(--ink-muted); cursor:pointer; font-size:10px; font-family:sans-serif;">Copy</button>
              <div style="font-size:10px; color:var(--ink-muted); text-transform:uppercase; margin-bottom:4px;">Run Command</div>
              <code style="font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--code-clr); display:block; padding-right:32px; word-break:break-all;">python worker.py --port 8081 --node-id worker-1 --raft-host 127.0.0.1 --raft-port 8181 --partners 127.0.0.1:8182,127.0.0.1:8183</code>
            </div>
          </div>

          <!-- Worker-2 Card -->
          <div class="status-card" id="card-worker-2" style="border:1px solid var(--border-trans); transition:all 0.3s ease;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600;"><i class="ti ti-server" style="margin-right:6px; color:var(--accent-blue);"></i>worker-2</h4>
              
              <div style="display:flex; align-items:center; gap:8px;">
                <!-- Manual Toggle -->
                <label class="switch-container size-sm">
                  <span class="switch-label size-sm" style="color:var(--switch-label-on);" id="toggle-label-worker-2">ON</span>
                  <input type="checkbox" id="toggle-checkbox-worker-2" checked onclick="toggleNode('worker-2')" style="display:none;" />
                  <div class="switch-slider size-sm" id="slider-worker-2" style="background:var(--switch-track-on);">
                    <div class="switch-knob size-sm" id="knob-worker-2" style="left:15px;"></div>
                  </div>
                </label>
                <span class="res-badge" id="status-worker-2" style="background:#ff4b4b; color:#fff; font-size:10px; margin:0; padding:3px 8px; border-radius:10px;">Offline</span>
              </div>
            </div>
            <div style="font-size:12px; color:var(--ink-muted); margin-bottom:12px;">
              <div>API: <span style="font-family:monospace;">http://127.0.0.1:8082</span></div>
              <div>Raft: <span style="font-family:monospace;">8182</span></div>
            </div>
            <div style="border-top:1px solid var(--hairline-soft); padding-top:10px; margin-bottom:14px; font-size:12px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">
              <div>
                <span style="font-size:10px; color:var(--ink-muted); text-transform:uppercase;">Role</span>
                <div id="role-worker-2" style="font-weight:600; font-family:monospace;">—</div>
              </div>
              <div>
                <span style="font-size:10px; color:var(--ink-muted); text-transform:uppercase;">Vectors</span>
                <div id="vec-worker-2" style="font-weight:600; font-family:monospace;">—</div>
              </div>
              <div>
                <span style="font-size:10px; color:var(--ink-muted); text-transform:uppercase;">Log Size</span>
                <div id="log-worker-2" style="font-weight:600; font-family:monospace;">—</div>
              </div>
            </div>
            
            <!-- Circular Telemetry Dials -->
            <div class="dials-container">
              <div class="dial-box">
                <svg width="56" height="56" viewBox="0 0 60 60">
                  <circle class="dial-bg" cx="30" cy="30" r="24"></circle>
                  <circle class="dial-fill" id="dial-fill-cpu-worker-2" cx="30" cy="30" r="24" stroke="var(--accent-blue)"></circle>
                </svg>
                <div class="dial-label" id="cpu-val-worker-2">0%</div>
                <span style="font-size: 8px; color: var(--ink-muted); margin-top: 4px; text-transform: uppercase; font-weight: 600;">CPU</span>
              </div>
              <div class="dial-box">
                <svg width="56" height="56" viewBox="0 0 60 60">
                  <circle class="dial-bg" cx="30" cy="30" r="24"></circle>
                  <circle class="dial-fill" id="dial-fill-mem-worker-2" cx="30" cy="30" r="24" stroke="var(--grad-violet)"></circle>
                </svg>
                <div class="dial-label" id="mem-val-worker-2">0%</div>
                <span style="font-size: 8px; color: var(--ink-muted); margin-top: 4px; text-transform: uppercase; font-weight: 600;">Memory</span>
              </div>
            </div>

            <div style="background:var(--code-bg); border-radius:6px; padding:8px; position:relative; border:1px solid var(--hairline-soft);">
              <button onclick="copyText(this, 'python worker.py --port 8082 --node-id worker-2 --raft-host 127.0.0.1 --raft-port 8182 --partners 127.0.0.1:8181,127.0.0.1:8183')" style="position:absolute; right:6px; top:6px; background:none; border:none; color:var(--ink-muted); cursor:pointer; font-size:10px; font-family:sans-serif;">Copy</button>
              <div style="font-size:10px; color:var(--ink-muted); text-transform:uppercase; margin-bottom:4px;">Run Command</div>
              <code style="font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--code-clr); display:block; padding-right:32px; word-break:break-all;">python worker.py --port 8082 --node-id worker-2 --raft-host 127.0.0.1 --raft-port 8182 --partners 127.0.0.1:8181,127.0.0.1:8183</code>
            </div>
          </div>

          <!-- Worker-3 Card -->
          <div class="status-card" id="card-worker-3" style="border:1px solid var(--border-trans); transition:all 0.3s ease;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600;"><i class="ti ti-server" style="margin-right:6px; color:var(--accent-blue);"></i>worker-3</h4>
              
              <div style="display:flex; align-items:center; gap:8px;">
                <!-- Manual Toggle -->
                <label class="switch-container size-sm">
                  <span class="switch-label size-sm" style="color:var(--switch-label-on);" id="toggle-label-worker-3">ON</span>
                  <input type="checkbox" id="toggle-checkbox-worker-3" checked onclick="toggleNode('worker-3')" style="display:none;" />
                  <div class="switch-slider size-sm" id="slider-worker-3" style="background:var(--switch-track-on);">
                    <div class="switch-knob size-sm" id="knob-worker-3" style="left:15px;"></div>
                  </div>
                </label>
                <span class="res-badge" id="status-worker-3" style="background:#ff4b4b; color:#fff; font-size:10px; margin:0; padding:3px 8px; border-radius:10px;">Offline</span>
              </div>
            </div>
            <div style="font-size:12px; color:var(--ink-muted); margin-bottom:12px;">
              <div>API: <span style="font-family:monospace;">http://127.0.0.1:8083</span></div>
              <div>Raft: <span style="font-family:monospace;">8183</span></div>
            </div>
            <div style="border-top:1px solid var(--hairline-soft); padding-top:10px; margin-bottom:14px; font-size:12px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">
              <div>
                <span style="font-size:10px; color:var(--ink-muted); text-transform:uppercase;">Role</span>
                <div id="role-worker-3" style="font-weight:600; font-family:monospace;">—</div>
              </div>
              <div>
                <span style="font-size:10px; color:var(--ink-muted); text-transform:uppercase;">Vectors</span>
                <div id="vec-worker-3" style="font-weight:600; font-family:monospace;">—</div>
              </div>
              <div>
                <span style="font-size:10px; color:var(--ink-muted); text-transform:uppercase;">Log Size</span>
                <div id="log-worker-3" style="font-weight:600; font-family:monospace;">—</div>
              </div>
            </div>
            
            <!-- Circular Telemetry Dials -->
            <div class="dials-container">
              <div class="dial-box">
                <svg width="56" height="56" viewBox="0 0 60 60">
                  <circle class="dial-bg" cx="30" cy="30" r="24"></circle>
                  <circle class="dial-fill" id="dial-fill-cpu-worker-3" cx="30" cy="30" r="24" stroke="var(--accent-blue)"></circle>
                </svg>
                <div class="dial-label" id="cpu-val-worker-3">0%</div>
                <span style="font-size: 8px; color: var(--ink-muted); margin-top: 4px; text-transform: uppercase; font-weight: 600;">CPU</span>
              </div>
              <div class="dial-box">
                <svg width="56" height="56" viewBox="0 0 60 60">
                  <circle class="dial-bg" cx="30" cy="30" r="24"></circle>
                  <circle class="dial-fill" id="dial-fill-mem-worker-3" cx="30" cy="30" r="24" stroke="var(--grad-violet)"></circle>
                </svg>
                <div class="dial-label" id="mem-val-worker-3">0%</div>
                <span style="font-size: 8px; color: var(--ink-muted); margin-top: 4px; text-transform: uppercase; font-weight: 600;">Memory</span>
              </div>
            </div>

            <div style="background:var(--code-bg); border-radius:6px; padding:8px; position:relative; border:1px solid var(--hairline-soft);">
              <button onclick="copyText(this, 'python worker.py --port 8083 --node-id worker-3 --raft-host 127.0.0.1 --raft-port 8183 --partners 127.0.0.1:8181,127.0.0.1:8182')" style="position:absolute; right:6px; top:6px; background:none; border:none; color:var(--ink-muted); cursor:pointer; font-size:10px; font-family:sans-serif;">Copy</button>
              <div style="font-size:10px; color:var(--ink-muted); text-transform:uppercase; margin-bottom:4px;">Run Command</div>
              <code style="font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--code-clr); display:block; padding-right:32px; word-break:break-all;">python worker.py --port 8083 --node-id worker-3 --raft-host 127.0.0.1 --raft-port 8183 --partners 127.0.0.1:8181,127.0.0.1:8182</code>
            </div>
          </div>
        </div>

        <!-- Consensus Simulation Grid -->
        <div class="cluster-sim-grid">
          <!-- 1. Raft Topology SVG -->
          <div class="status-card" style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; margin-bottom:0;">
            <div>
              <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600; margin-bottom:4px; color:var(--grad-violet); display:flex; align-items:center; gap:8px;">
                <i class="ti ti-git-fork" style="font-size:18px;"></i> Raft Topology & Heartbeats
              </h4>
              <p style="font-size:11px; color:var(--ink-muted); line-height:1.4; margin-bottom:12px;">Consensus heartbeat pathways, active roles, and partition bounds.</p>
              <div class="raft-flow-box" style="display:flex; justify-content:center; padding:10px 0;">
                <svg id="raftFlowSvg" width="280" height="200" viewBox="0 0 280 200" style="background:none;">
                  <!-- Connections -->
                  <path id="svgPath-1-2" class="heartbeat-active" d="M 125 55 L 75 125" stroke="var(--hairline)" stroke-width="2" />
                  <path id="svgPath-1-3" class="heartbeat-active" d="M 155 55 L 205 125" stroke="var(--hairline)" stroke-width="2" />
                  <path id="svgPath-2-3" class="heartbeat-active" d="M 82 140 L 198 140" stroke="var(--hairline)" stroke-width="2" />

                  <!-- Nodes -->
                  <!-- Node 1 -->
                  <g class="raft-node-svg" id="svgNode-worker-1" style="cursor:pointer;" onclick="toggleNodeDirect('worker-1')">
                    <circle cx="140" cy="40" r="22" fill="var(--surface-1)" stroke="var(--accent-blue)" stroke-width="2" />
                    <text x="140" y="44" text-anchor="middle" font-size="9" fill="var(--ink)" font-family="monospace">W1</text>
                    <text id="svgNodeRole-worker-1" x="140" y="74" text-anchor="middle" font-size="8" fill="var(--accent-blue)">Leader</text>
                  </g>
                  <!-- Node 2 -->
                  <g class="raft-node-svg" id="svgNode-worker-2" style="cursor:pointer;" onclick="toggleNodeDirect('worker-2')">
                    <circle cx="60" cy="140" r="22" fill="var(--surface-1)" stroke="var(--grad-violet)" stroke-width="2" />
                    <text x="60" y="144" text-anchor="middle" font-size="9" fill="var(--ink)" font-family="monospace">W2</text>
                    <text id="svgNodeRole-worker-2" x="60" y="174" text-anchor="middle" font-size="8" fill="var(--ink-muted)">Follower</text>
                  </g>
                  <!-- Node 3 -->
                  <g class="raft-node-svg" id="svgNode-worker-3" style="cursor:pointer;" onclick="toggleNodeDirect('worker-3')">
                    <circle cx="220" cy="140" r="22" fill="var(--surface-1)" stroke="var(--grad-violet)" stroke-width="2" />
                    <text x="220" y="144" text-anchor="middle" font-size="9" fill="var(--ink)" font-family="monospace">W3</text>
                    <text id="svgNodeRole-worker-3" x="220" y="174" text-anchor="middle" font-size="8" fill="var(--ink-muted)">Follower</text>
                  </g>
                </svg>
              </div>
            </div>
            <div style="font-size: 11px; color: var(--ink-muted); text-align: center; border-top: 1px solid var(--hairline-soft); padding-top: 12px; margin-top: 12px;">
              <span style="color: var(--accent-blue); font-weight:600;">Manual Control:</span> Click node circles above to toggle online/offline state.
            </div>
          </div>
          
          <!-- 2. Chaos Monkey Panel -->
          <div class="status-card" style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; margin-bottom:0;">
            <div>
              <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600; margin-bottom:4px; color:var(--grad-coral); display:flex; align-items:center; gap:8px;">
                <i class="ti ti-ghost" style="font-size:18px;"></i> Chaos Monkey Simulator
              </h4>
              <p style="font-size:11px; color:var(--ink-muted); line-height:1.4; margin-bottom:16px;">Trigger cluster faults, partitions, and leader dropouts to test Raft consensus recovery.</p>
              
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:16px;">
                <button class="chaos-btn" onclick="triggerMonkeyFailNode()" style="font-size:11px; padding:8px; border-radius:6px; display:flex; align-items:center; justify-content:center; gap:6px;">
                  <i class="ti ti-plug-off" style="color:var(--grad-coral);"></i> Fail Node
                </button>
                <button class="chaos-btn" onclick="triggerMonkeyPartition()" style="font-size:11px; padding:8px; border-radius:6px; display:flex; align-items:center; justify-content:center; gap:6px;">
                  <i class="ti ti-git-pull-request" style="color:#ffa726;"></i> Partition
                </button>
                <button class="chaos-btn" onclick="triggerMonkeyHeal()" style="font-size:11px; padding:8px; border-radius:6px; display:flex; align-items:center; justify-content:center; gap:6px;">
                  <i class="ti ti-shield-heart" style="color:#22c55e;"></i> Heal Net
                </button>
                <button class="chaos-btn" onclick="triggerMonkeyElection()" style="font-size:11px; padding:8px; border-radius:6px; display:flex; align-items:center; justify-content:center; gap:6px;">
                  <i class="ti ti-refresh" style="color:var(--accent-blue);"></i> Re-Elect
                </button>
              </div>
              
              <!-- Scrolling Console -->
              <div class="chaos-console" id="chaosConsole">
                <div>[SYSTEM] Chaos Engine online. Awaiting directive...</div>
              </div>
            </div>
          </div>

          <!-- 3. Raft Log Table -->
          <div class="status-card" style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; margin-bottom:0;">
            <div>
              <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600; margin-bottom:4px; color:var(--grad-magenta); display:flex; align-items:center; gap:8px;">
                <i class="ti ti-list-check" style="font-size:18px;"></i> Raft Replication Ledger
              </h4>
              <p style="font-size:11px; color:var(--ink-muted); line-height:1.4; margin-bottom:12px;">Live database write operations being replicated across sharded log indices.</p>
              
              <div style="border:1px solid var(--hairline); border-radius:6px; overflow:hidden;">
                <div style="max-height:110px; overflow-y:auto; background:var(--code-bg);" id="raftTableContainer">
                  <table style="width:100%; border-collapse:collapse; font-size:10px; font-family:monospace; text-align:left;">
                    <thead style="background:var(--surface-2); position:sticky; top:0; color:var(--ink); border-bottom:1px solid var(--hairline); z-index: 5;">
                      <tr>
                        <th style="padding:6px 8px; font-weight:600;">Idx</th>
                        <th style="padding:6px 8px; font-weight:600;">Term</th>
                        <th style="padding:6px 8px; font-weight:600;">Cmd</th>
                        <th style="padding:6px 8px; font-weight:600; text-align:center;">W1</th>
                        <th style="padding:6px 8px; font-weight:600; text-align:center;">W2</th>
                        <th style="padding:6px 8px; font-weight:600; text-align:center;">W3</th>
                      </tr>
                    </thead>
                    <tbody id="raftLogBody" style="color:var(--ink-muted);">
                      <!-- Populated by JS -->
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
            <div style="font-size: 11px; display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--hairline-soft); padding-top:12px; margin-top:12px;">
              <span style="color:var(--ink-muted);">Auto-ingest writes:</span>
              <label class="switch-container size-sm" style="margin:0;">
                <span class="switch-label size-sm" style="color:var(--switch-label-on);" id="toggle-label-auto-writes">ON</span>
                <input type="checkbox" id="toggle-checkbox-auto-writes" checked onclick="toggleAutoWrites()" style="display:none;" />
                <div class="switch-slider size-sm" id="slider-auto-writes" style="background:var(--switch-track-on);">
                  <div class="switch-knob size-sm" id="knob-auto-writes" style="left:15px;"></div>
                </div>
              </label>
            </div>
          </div>
        </div>

        <!-- Tips Section -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:20px; margin-top:24px;">
          <!-- Setup Tips -->
          <div class="status-card" style="padding: 20px; margin-bottom: 0;">
            <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600; margin-bottom:12px; color:var(--accent-blue); display:flex; align-items:center; gap:8px;">
              <i class="ti ti-settings" style="font-size:18px;"></i> Cluster Setup & Operations
            </h4>
            <p style="font-size:12px; color:var(--ink-muted); line-height:1.6; margin-bottom:10px;">
              For maximum throughput and high availability, NuroSearch nodes should run concurrently. Follow these operational guidelines:
            </p>
            <ul style="font-size:12px; color:var(--ink-muted); padding-left:16px; line-height:1.7; display:flex; flex-direction:column; gap:6px; text-align:left;">
              <li><strong>Terminal Setup:</strong> Launch three separate terminals and run each worker command to establish independent worker shards.</li>
              <li><strong>Coordinator Binding:</strong> The coordinator routes write commands to specific shards using MD5 hashing, enabling horizontal scalability.</li>
              <li><strong>Consensus Quorum:</strong> Raft requires a majority of nodes to be online (2 out of 3) to elect a leader and commit replicate logs. If a quorum is lost, writes are rejected to prevent split-brain.</li>
              <li><strong>Auto-Recovery:</strong> Bringing an offline worker back online will trigger Raft catch-up, synchronizing its local index state automatically.</li>
            </ul>
          </div>

          <!-- Uses Tips -->
          <div class="status-card" style="padding: 20px; margin-bottom: 0;">
            <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600; margin-bottom:12px; color:#c7a2ff; display:flex; align-items:center; gap:8px;">
              <i class="ti ti-layers-intersect" style="font-size:18px;"></i> Practical Uses of Cluster
            </h4>
            <p style="font-size:12px; color:var(--ink-muted); line-height:1.6; margin-bottom:10px;">
              Distributed architectures like the NuroSearch Cluster solve several database and scalability challenges:
            </p>
            <ul style="font-size:12px; color:var(--ink-muted); padding-left:16px; line-height:1.7; display:flex; flex-direction:column; gap:6px; text-align:left;">
              <li><strong>Horizontal Scale-Out:</strong> Sharding splits massive vector datasets across multiple workers, bypassing the single-machine RAM limits.</li>
              <li><strong>Query Parallelism:</strong> Scatter-Gather searches workers in parallel, reducing search latencies for large-scale operations.</li>
              <li><strong>High Availability (HA):</strong> Automatic leader election ensures index read operations stay online even if some worker shards fail.</li>
              <li><strong>Consistent Hashing Routing:</strong> Minimizes data movement when worker nodes are added or removed, ensuring stable partition boundaries.</li>
            </ul>
          </div>

          <!-- Cluster Name Tips -->
          <div class="status-card" style="padding: 20px; margin-bottom: 0;">
            <h4 style="font-family:'Outfit'; font-size:15px; font-weight:600; margin-bottom:12px; color:#00ff66; display:flex; align-items:center; gap:8px;">
              <i class="ti ti-tags" style="font-size:18px;"></i> Uses of Cluster Name
            </h4>
            <p style="font-size:12px; color:var(--ink-muted); line-height:1.6; margin-bottom:10px;">
              The Cluster Name parameter serves critical functions in cluster coordination, identification, and network boundaries:
            </p>
            <ul style="font-size:12px; color:var(--ink-muted); padding-left:16px; line-height:1.7; display:flex; flex-direction:column; gap:6px; text-align:left;">
              <li><strong>Namespace Isolation:</strong> Differentiates multiple distinct database clusters sharing the same physical network or subnet, preventing node collision.</li>
              <li><strong>Node Authentication:</strong> Serves as a primary handshake token; workers with a mismatching cluster name are rejected during discovery.</li>
              <li><strong>Discovery & Orchestration:</strong> Used in service discovery configuration registries (like Consul or ZooKeeper) to dynamically map coordinators.</li>
              <li><strong>Log Auditing & Metrics:</strong> Labels coordinator logs and telemetry data, ensuring analytics pipelines attribute requests to the correct cluster.</li>
            </ul>
          </div>
        </div>
"""

cluster_js = """
// State and configuration for Chaos Monkey & Raft Simulation
let chaosLogs = [];
let partitionActive = false;
let partitionA = ['worker-1', 'worker-2'];
let partitionB = ['worker-3'];
let raftTerm = 4;
let raftLogs = [
  { index: 1020, term: 3, command: "SET doc_782", states: { 'worker-1': 'committed', 'worker-2': 'committed', 'worker-3': 'committed' } },
  { index: 1021, term: 3, command: "SET doc_783", states: { 'worker-1': 'committed', 'worker-2': 'committed', 'worker-3': 'committed' } },
  { index: 1022, term: 3, command: "SET doc_784", states: { 'worker-1': 'committed', 'worker-2': 'committed', 'worker-3': 'committed' } },
  { index: 1023, term: 4, command: "UPSERT doc_785", states: { 'worker-1': 'committed', 'worker-2': 'committed', 'worker-3': 'committed' } },
  { index: 1024, term: 4, command: "DEL doc_109", states: { 'worker-1': 'committed', 'worker-2': 'committed', 'worker-3': 'committed' } }
];
let autoWritesEnabled = true;
let autoWritesInterval = null;
let simulatedLeader = 'worker-1';

// Override global nodeOverrides from index.html if necessary
if (typeof nodeOverrides === 'undefined') {
  window.nodeOverrides = {
    coordinator: true,
    'worker-1': true,
    'worker-2': true,
    'worker-3': true
  };
}

// Log message to Chaos Console
function monkeyLog(msg, type = 'info') {
  const consoleEl = document.getElementById('chaosConsole');
  if (!consoleEl) return;
  const time = new Date().toLocaleTimeString();
  const logDiv = document.createElement('div');
  logDiv.className = `log-${type}`;
  logDiv.innerHTML = `[${time}] ${msg}`;
  consoleEl.appendChild(logDiv);
  consoleEl.scrollTop = consoleEl.scrollHeight;
}

// Redefining toggleNode to hook into our UI
window.toggleNodeDirect = function(id) {
  const checkbox = document.getElementById('toggle-checkbox-' + id);
  if (checkbox) {
    checkbox.checked = !checkbox.checked;
    toggleNode(id);
  } else {
    nodeOverrides[id] = !nodeOverrides[id];
    recalculateLeader();
    fetchClusterHealth();
  }
  monkeyLog(`Directly toggled node ${id} to ${nodeOverrides[id] ? 'ONLINE' : 'OFFLINE'}`, nodeOverrides[id] ? 'success' : 'err');
};

// Update Circular Dials and UI Health
window.fetchClusterHealth = async function() {
  const coordStatus = document.getElementById('coordinatorStatus');
  const coordHost = document.getElementById('coordinatorHost');
  
  updateRaftSvgPaths();

  let coordOnline = nodeOverrides.coordinator !== false;
  if (coordStatus) {
    coordStatus.textContent = coordOnline ? 'Online (Simulated)' : 'Offline';
    coordStatus.style.background = coordOnline ? '#00ff66' : '#ff4b4b';
    coordStatus.style.color = coordOnline ? '#000' : '#fff';
  }
  if (coordHost) {
    coordHost.textContent = `Proxy: ${API}/cluster/coordinator/health (${coordOnline ? 'Simulated' : 'Offline'})`;
  }

  const workers = ['worker-1', 'worker-2', 'worker-3'];
  
  for (const id of workers) {
    const card = document.getElementById(`card-${id}`);
    const statusSpan = document.getElementById(`status-${id}`);
    const roleDiv = document.getElementById(`role-${id}`);
    const vecDiv = document.getElementById(`vec-${id}`);
    const logDiv = document.getElementById(`log-${id}`);
    
    const isOnline = nodeOverrides[id] !== false;
    
    if (statusSpan) {
      statusSpan.textContent = isOnline ? 'Online' : 'Offline';
      statusSpan.style.background = isOnline ? '#00ff66' : '#ff4b4b';
      statusSpan.style.color = isOnline ? '#000' : '#fff';
    }
    if (card) {
      card.style.borderColor = isOnline ? 'rgba(0, 255, 102, 0.2)' : 'rgba(255, 75, 75, 0.15)';
    }

    if (isOnline) {
      const isLeader = (simulatedLeader === id);
      const isIsolated = partitionActive && partitionB.includes(id);
      
      if (roleDiv) {
        if (isLeader) {
          roleDiv.textContent = 'Leader 👑';
          roleDiv.style.color = '#ff7a3d';
        } else {
          roleDiv.textContent = isIsolated ? 'Follower (Isolated)' : 'Follower';
          roleDiv.style.color = isIsolated ? '#ffa726' : '#0099ff';
        }
      }

      const mockVectors = { 'worker-1': 1084, 'worker-2': 1092, 'worker-3': 1079 };
      vecDiv.textContent = mockVectors[id] + (raftLogs.filter(l => l.states[id] === 'committed').length);
      logDiv.textContent = raftLogs.length;

      const cpuVal = Math.floor(Math.random() * 15) + (isLeader ? 15 : 5);
      const memVal = 48 + Math.floor(Math.random() * 4);
      
      updateCircularDial(id, 'cpu', cpuVal);
      updateCircularDial(id, 'mem', memVal);
    } else {
      if (roleDiv) {
        roleDiv.textContent = '—';
        roleDiv.style.color = '';
      }
      if (vecDiv) vecDiv.textContent = '—';
      if (logDiv) logDiv.textContent = '—';
      
      updateCircularDial(id, 'cpu', 0);
      updateCircularDial(id, 'mem', 0);
    }
  }

  updateRaftSvgNodes();
};

function updateCircularDial(nodeId, type, pct) {
  const circle = document.getElementById(`dial-fill-${type}-${nodeId}`);
  const text = document.getElementById(`${type}-val-${nodeId}`);
  if (!circle || !text) return;
  const radius = 24;
  const circumference = 2 * Math.PI * radius; // ~150.8
  const offset = circumference - (pct / 100) * circumference;
  circle.style.strokeDashoffset = offset;
  text.textContent = Math.round(pct) + '%';
}

function updateRaftSvgPaths() {
  const p12 = document.getElementById('svgPath-1-2');
  const p13 = document.getElementById('svgPath-1-3');
  const p23 = document.getElementById('svgPath-2-3');
  
  if (!p12 || !p13 || !p23) return;

  const w1 = nodeOverrides['worker-1'] !== false;
  const w2 = nodeOverrides['worker-2'] !== false;
  const w3 = nodeOverrides['worker-3'] !== false;

  if (w1 && w2) {
    p12.className.baseVal = "heartbeat-active";
  } else {
    p12.className.baseVal = "heartbeat-broken";
  }

  if (w1 && w3) {
    if (partitionActive) {
      p13.className.baseVal = "heartbeat-partitioned";
    } else {
      p13.className.baseVal = "heartbeat-active";
    }
  } else {
    p13.className.baseVal = "heartbeat-broken";
  }

  if (w2 && w3) {
    if (partitionActive) {
      p23.className.baseVal = "heartbeat-partitioned";
    } else {
      p23.className.baseVal = "heartbeat-active";
    }
  } else {
    p23.className.baseVal = "heartbeat-broken";
  }
}

function updateRaftSvgNodes() {
  const nodes = ['worker-1', 'worker-2', 'worker-3'];
  nodes.forEach(id => {
    const group = document.getElementById(`svgNode-${id}`);
    const roleText = document.getElementById(`svgNodeRole-${id}`);
    if (!group || !roleText) return;
    
    const circle = group.querySelector('circle');
    const isOnline = nodeOverrides[id] !== false;
    const isLeader = (simulatedLeader === id);
    const isIsolated = partitionActive && partitionB.includes(id);

    if (!isOnline) {
      circle.setAttribute('stroke', '#ff4b4b');
      roleText.textContent = "Offline";
      roleText.setAttribute('fill', '#ff4b4b');
    } else if (isLeader) {
      circle.setAttribute('stroke', '#ff7a3d');
      roleText.textContent = "Leader 👑";
      roleText.setAttribute('fill', '#ff7a3d');
    } else if (isIsolated) {
      circle.setAttribute('stroke', '#ffa726');
      roleText.textContent = "Isolated";
      roleText.setAttribute('fill', '#ffa726');
    } else {
      circle.setAttribute('stroke', '#0099ff');
      roleText.textContent = "Follower";
      roleText.setAttribute('fill', '#0099ff');
    }
  });
}

window.recalculateLeader = function() {
  const activeWorkers = ['worker-1', 'worker-2', 'worker-3'].filter(id => nodeOverrides[id] !== false);
  
  if (partitionActive) {
    const activeInA = activeWorkers.filter(id => partitionA.includes(id));
    const activeInB = activeWorkers.filter(id => partitionB.includes(id));

    if (activeInA.length >= 2) {
      if (!simulatedLeader || !activeInA.includes(simulatedLeader)) {
        simulatedLeader = activeInA[0];
        raftTerm++;
        monkeyLog(`[RAFT] Partition A achieved quorum. Elected new leader ${simulatedLeader} for Term ${raftTerm}.`, 'success');
      }
    } else {
      simulatedLeader = null;
      monkeyLog(`[RAFT] Quorum lost across all partition bounds. Leadership stepped down.`, 'warn');
    }
  } else {
    if (activeWorkers.length >= 2) {
      if (!simulatedLeader || !activeWorkers.includes(simulatedLeader)) {
        simulatedLeader = activeWorkers[0];
        raftTerm++;
        monkeyLog(`[RAFT] Quorum active (${activeWorkers.length}/3). Elected ${simulatedLeader} as Leader for Term ${raftTerm}.`, 'success');
      }
    } else {
      simulatedLeader = null;
      monkeyLog(`[RAFT] Quorum lost (${activeWorkers.length}/3 online). Database is in read-only safe mode.`, 'warn');
    }
  }
};

window.triggerMonkeyFailNode = function() {
  if (typeof playClickSound === 'function') playClickSound();
  
  const online = ['worker-1', 'worker-2', 'worker-3'].filter(id => nodeOverrides[id] !== false);
  if (online.length === 0) {
    monkeyLog("All nodes are already offline. Chaos Monkey has nothing to kill!", "warn");
    return;
  }
  const target = online[Math.floor(Math.random() * online.length)];
  
  nodeOverrides[target] = false;
  
  const label = document.getElementById('toggle-label-' + target);
  const checkbox = document.getElementById('toggle-checkbox-' + target);
  const slider = document.getElementById('slider-' + target);
  const knob = document.getElementById('knob-' + target);
  if (checkbox) checkbox.checked = false;
  if (label) {
    label.textContent = 'OFF';
    label.style.color = 'var(--switch-label-off)';
  }
  if (slider) slider.style.background = 'var(--switch-track-off)';
  if (knob) knob.style.left = '2px';

  monkeyLog(`Chaos Monkey terminated node <strong>${target}</strong>!`, 'err');
  showToast(`Chaos Monkey terminated ${target}!`, 'error');

  recalculateLeader();
  fetchClusterHealth();
};

window.triggerMonkeyPartition = function() {
  if (typeof playClickSound === 'function') playClickSound();
  if (partitionActive) {
    monkeyLog("A network partition is already active. Heal it first!", "warn");
    return;
  }

  partitionActive = true;
  monkeyLog("Chaos Monkey severed network connections! Quorum A: [W1, W2], Quorum B: [W3] (isolated).", "warn");
  showToast("Network Partition Active!", "warning");

  recalculateLeader();
  fetchClusterHealth();
};

window.triggerMonkeyHeal = function() {
  if (typeof playClickSound === 'function') playClickSound();
  if (!partitionActive) {
    monkeyLog("Network boundaries are normal. No partition to heal.", "info");
    return;
  }

  partitionActive = false;
  monkeyLog("Network partition healed. Re-establishing global quorum heartbeats.", "success");
  showToast("Network partition healed!", "success");

  const leader = simulatedLeader;
  if (leader) {
    raftLogs.forEach(log => {
      if (nodeOverrides['worker-3'] !== false && log.states['worker-3'] !== 'committed') {
        log.states['worker-3'] = 'committed';
      }
    });
    monkeyLog(`[RAFT] worker-3 successfully synchronized missing logs from Leader ${leader}.`, 'success');
  }

  recalculateLeader();
  fetchClusterHealth();
  renderRaftLedger();
};

window.triggerMonkeyElection = function() {
  if (typeof playClickSound === 'function') playClickSound();
  
  const online = ['worker-1', 'worker-2', 'worker-3'].filter(id => nodeOverrides[id] !== false);
  if (online.length < 2) {
    monkeyLog("Insufficient nodes to hold an election. Quorum lost.", "warn");
    return;
  }

  monkeyLog("Manual leader step-down triggered. Heartbeat cancelled.", "info");
  
  const oldLeader = simulatedLeader;
  simulatedLeader = null;
  fetchClusterHealth();

  setTimeout(() => {
    const candidates = online.filter(id => id !== oldLeader);
    const newLeader = candidates.length > 0 ? candidates[0] : online[0];
    
    simulatedLeader = newLeader;
    raftTerm++;
    
    monkeyLog(`[RAFT] Election complete. worker candidate <strong>${newLeader}</strong> won consensus for Term ${raftTerm}.`, 'success');
    showToast(`New Leader Elected: ${newLeader}`, 'success');
    fetchClusterHealth();
  }, 1200);
};

function renderRaftLedger() {
  const tbody = document.getElementById('raftLogBody');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  const logsToRender = raftLogs.slice(-8);
  logsToRender.forEach(log => {
    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid var(--hairline-soft)';
    
    const tdIdx = document.createElement('td');
    tdIdx.style.padding = '6px 8px';
    tdIdx.style.fontWeight = 'bold';
    tdIdx.textContent = `#${log.index}`;
    
    const tdTerm = document.createElement('td');
    tdTerm.style.padding = '6px 8px';
    tdTerm.textContent = `T${log.term}`;
    
    const tdCmd = document.createElement('td');
    tdCmd.style.padding = '6px 8px';
    tdCmd.style.color = 'var(--ink)';
    tdCmd.textContent = log.command;
    
    tr.appendChild(tdIdx);
    tr.appendChild(tdTerm);
    tr.appendChild(tdCmd);
    
    ['worker-1', 'worker-2', 'worker-3'].forEach(node => {
      const tdNode = document.createElement('td');
      tdNode.style.padding = '6px 8px';
      tdNode.style.textAlign = 'center';
      
      const state = log.states[node];
      const span = document.createElement('span');
      span.className = `ledger-badge ledger-${state}`;
      
      if (state === 'committed') {
        span.textContent = 'Commit';
      } else if (state === 'replicated') {
        span.textContent = 'Replicated';
      } else if (state === 'uncommitted') {
        span.textContent = 'Queue';
      } else if (state === 'offline') {
        span.textContent = 'Offline';
      } else if (state === 'stale') {
        span.textContent = 'Stale';
      }
      
      tdNode.appendChild(span);
      tr.appendChild(tdNode);
    });
    
    tbody.appendChild(tr);
  });
  
  const container = document.getElementById('raftTableContainer');
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}

window.appendRaftLog = function(cmd) {
  if (!simulatedLeader) {
    monkeyLog(`[RAFT] Rejected write "${cmd}". No active leader consensus.`, 'err');
    return;
  }

  const nextIndex = raftLogs.length > 0 ? raftLogs[raftLogs.length - 1].index + 1 : 1000;
  
  const initialStates = {};
  ['worker-1', 'worker-2', 'worker-3'].forEach(node => {
    const isOnline = nodeOverrides[node] !== false;
    if (!isOnline) {
      initialStates[node] = 'offline';
    } else if (partitionActive && partitionB.includes(node) && partitionA.includes(simulatedLeader)) {
      initialStates[node] = 'stale';
    } else if (partitionActive && partitionA.includes(node) && partitionB.includes(simulatedLeader)) {
      initialStates[node] = 'stale';
    } else {
      initialStates[node] = 'uncommitted';
    }
  });

  const newLog = {
    index: nextIndex,
    term: raftTerm,
    command: cmd,
    states: initialStates
  };

  raftLogs.push(newLog);
  renderRaftLedger();
  monkeyLog(`[LEADER] Appended client write #${nextIndex}: <code>${cmd}</code>. Broadcasting to quorum...`);

  setTimeout(() => {
    ['worker-1', 'worker-2', 'worker-3'].forEach(node => {
      if (newLog.states[node] === 'uncommitted') {
        newLog.states[node] = 'replicated';
      }
    });
    renderRaftLedger();
    
    setTimeout(() => {
      const activeInQuorum = ['worker-1', 'worker-2', 'worker-3'].filter(node => {
        return nodeOverrides[node] !== false && 
               (!partitionActive || 
                (partitionA.includes(simulatedLeader) && partitionA.includes(node)) || 
                (partitionB.includes(simulatedLeader) && partitionB.includes(node)));
      });

      if (activeInQuorum.length >= 2) {
        ['worker-1', 'worker-2', 'worker-3'].forEach(node => {
          if (newLog.states[node] === 'replicated' || node === simulatedLeader) {
            newLog.states[node] = 'committed';
          }
        });
        renderRaftLedger();
        monkeyLog(`[RAFT] Quorum achieved for #${nextIndex}. Committing index entry.`, 'success');
      } else {
        monkeyLog(`[RAFT] Consensus timeout. Failed to achieve quorum for #${nextIndex}. Entry is uncommitted.`, 'err');
      }
    }, 400);
  }, 350);
};

window.toggleAutoWrites = function() {
  const cb = document.getElementById('toggle-checkbox-auto-writes');
  if (!cb) return;
  autoWritesEnabled = cb.checked;
  
  const label = document.getElementById('toggle-label-auto-writes');
  const slider = document.getElementById('slider-auto-writes');
  const knob = document.getElementById('knob-auto-writes');
  if (label) {
    label.textContent = autoWritesEnabled ? 'ON' : 'OFF';
    label.style.color = autoWritesEnabled ? 'var(--switch-label-on)' : 'var(--switch-label-off)';
  }
  if (slider) {
    slider.style.background = autoWritesEnabled ? 'var(--switch-track-on)' : 'var(--switch-track-off)';
  }
  if (knob) {
    knob.style.left = autoWritesEnabled ? '15px' : '2px';
  }
  
  if (typeof playClickSound === 'function') playClickSound();

  if (autoWritesEnabled) {
    startAutoWrites();
    monkeyLog("Auto-ingestion simulation enabled.");
  } else {
    stopAutoWrites();
    monkeyLog("Auto-ingestion simulation suspended.");
  }
};

function startAutoWrites() {
  if (autoWritesInterval) clearInterval(autoWritesInterval);
  autoWritesInterval = setInterval(() => {
    if (!autoWritesEnabled) return;
    const cmds = [
      "SET vec_" + Math.floor(Math.random() * 1000),
      "UPSERT v_" + Math.floor(Math.random() * 1000),
      "DEL vec_" + Math.floor(Math.random() * 200),
      "COMMIT index_chunk",
      "PRUNE stale_node"
    ];
    const randCmd = cmds[Math.floor(Math.random() * cmds.length)];
    appendRaftLog(randCmd);
  }, 3500);
}

function stopAutoWrites() {
  if (autoWritesInterval) {
    clearInterval(autoWritesInterval);
    autoWritesInterval = null;
  }
}

setTimeout(() => {
  renderRaftLedger();
  startAutoWrites();
  fetchClusterHealth();
}, 500);
"""

# HTML for About tab including the Privacy Policy Accordion
about_html = about_html.strip() + """
        <!-- Privacy Policy Accordion (Local Compliance Boundaries) -->
        <div class="privacy-accordion-header" onclick="togglePrivacyAccordion()">
          <div>
            <h4 style="font-family:'Outfit'; font-size:13.5px; font-weight:700; color:var(--ink); margin:0; display:flex; align-items:center; gap:8px;">
              <i class="ti ti-shield-check" style="color:#22c55e; font-size:16px;"></i> Compliance, Privacy & Operational Terms
            </h4>
            <p style="font-size:11px; color:var(--ink-muted); margin:4px 0 0 0; line-height:1.3;">Zero-telemetry local sandboxes, regulatory privacy compliance, and hardware boundaries.</p>
          </div>
          <i class="ti ti-chevron-down" id="privacyChevron" style="font-size:16px; transition: transform 0.2s ease;"></i>
        </div>
        <div class="privacy-accordion-body" id="privacyAccordionBody" style="display:none;">
          <div class="privacy-item">
            <div class="privacy-item-title"><i class="ti ti-cloud-off" style="color:#ff4b4b;"></i> Zero Cloud Transmission</div>
            <div class="privacy-item-desc">NuroSearch runs entirely on local loopback (<code>127.0.0.1</code>). No vector weights, indexes, document raw content, or search logs are uploaded to any external analytics endpoint or server. Your machine is your firewall.</div>
          </div>
          <div class="privacy-item">
            <div class="privacy-item-title"><i class="ti ti-database" style="color:#0099ff;"></i> Sealed SQLite Storage</div>
            <div class="privacy-item-desc">All document metadata and sharded vector tables are cached locally within the <code>vectors.db</code> SQLite WAL database. Physical data containment is absolute, respecting all local host encryption boundaries.</div>
          </div>
          <div class="privacy-item">
            <div class="privacy-item-title"><i class="ti ti-binary" style="color:#a855f7;"></i> Local Queue isolation</div>
            <div class="privacy-item-desc">The ingestion broker binds exclusively to private loopback sockets. All message streams, partitions, and chunked vector payloads are recycled locally and never routed outside the active machine's host memory.</div>
          </div>
          <div class="privacy-item">
            <div class="privacy-item-title"><i class="ti ti-lock" style="color:#22c55e;"></i> Complete Regulatory Compliance</div>
            <div class="privacy-item-desc">By avoiding cloud dependencies, NuroSearch aligns natively with strict GDPR, HIPAA, and CCPA requirements for data residency. Developers can prototype AI search capabilities with sensitive documents in complete network isolation.</div>
          </div>
        </div>
"""

# Append JS code to about_js including the Privacy Accordion Toggler
about_js = about_js.strip() + """
// Privacy Accordion Toggle
window.togglePrivacyAccordion = function() {
  const body = document.getElementById('privacyAccordionBody');
  const chevron = document.getElementById('privacyChevron');
  if (!body || !chevron) return;
  const isOpen = body.style.display !== 'none';
  if (typeof playClickSound === 'function') playClickSound();
  
  if (isOpen) {
    body.style.display = 'none';
    chevron.style.transform = 'rotate(0deg)';
  } else {
    body.style.display = 'block';
    chevron.style.transform = 'rotate(180deg)';
  }
};
"""

# Compile to dictionary structure
dashboard_extensions = {
    "css": css_content.strip(),
    "cluster_html": cluster_html.strip(),
    "cluster_js": cluster_js.strip(),
    "about_html": about_html.strip(),
    "about_js": about_js.strip()
}

# Output file path
output_file = r"D:\My Own Artificial Intelligance\scratch\cluster_about.json"
os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(dashboard_extensions, f, indent=2, ensure_ascii=False)

print(f"Successfully compiled and saved JSON dashboard enhancements to: {output_file}")
