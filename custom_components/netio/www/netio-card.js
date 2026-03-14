const CARD_VERSION = "1.0.0";

// ─── i18n ───────────────────────────────────────────────────────────
const _netioLang = () => {
  try { return document.querySelector('home-assistant')?.hass?.language || 'en'; } catch(e) { return 'en'; }
};
const _netioI18n = {
  de: {
    outputs: 'Ausgänge', output: 'Ausgang', output_1: 'Ausgang', output_n: 'Ausgänge',
    no_outputs: 'Keine Ausgänge gefunden',
    no_outputs_hint: 'NETIO Integration einrichten',
    on: 'Ein', off: 'Aus', power: 'Leistung', energy: 'Energie', current: 'Strom',
    voltage: 'Spannung', frequency: 'Frequenz', total_load: 'Gesamtleistung',
    power_factor: 'Leistungsfaktor',
    restart: 'Neustart', short_on: 'Kurz Ein', toggle: 'Umschalten',
    title: 'Titel', accent_color: 'Akzentfarbe', reset: 'Standard',
    accent_hint: 'Standard: #006B3F (NETIO Grün)', design: 'Design',
    auto: 'Automatisch', dark: 'Dunkel', light: 'Hell',
    show_energy: 'Energiedaten anzeigen', show_actions: 'Aktions-Buttons anzeigen',
    desc_main: 'Alle NETIO Ausgänge mit Steuerung und Metering',
    global: 'Gerät',
  },
  en: {
    outputs: 'Outputs', output: 'Output', output_1: 'Output', output_n: 'Outputs',
    no_outputs: 'No outputs found',
    no_outputs_hint: 'Set up NETIO integration',
    on: 'On', off: 'Off', power: 'Power', energy: 'Energy', current: 'Current',
    voltage: 'Voltage', frequency: 'Frequency', total_load: 'Total load',
    power_factor: 'Power factor',
    restart: 'Restart', short_on: 'Short ON', toggle: 'Toggle',
    title: 'Title', accent_color: 'Accent color', reset: 'Default',
    accent_hint: 'Default: #006B3F (NETIO Green)', design: 'Design',
    auto: 'Automatic', dark: 'Dark', light: 'Light',
    show_energy: 'Show energy data', show_actions: 'Show action buttons',
    desc_main: 'All NETIO outputs with control and metering',
    global: 'Device',
  },
};
function nT(key) { const l = _netioLang(); return (_netioI18n[l] || _netioI18n['en'])[key] || _netioI18n['en'][key] || key; }
function nPlural(c, one, many) { return c === 1 ? one : many; }

function nEscape(str) {
  return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;");
}

function nHexToRgb(hex) {
  const c = hex.replace("#","");
  return `${parseInt(c.substring(0,2),16)}, ${parseInt(c.substring(2,4),16)}, ${parseInt(c.substring(4,6),16)}`;
}

function nDebounce(fn, wait = 300) {
  let timer;
  return function(...args) { clearTimeout(timer); timer = setTimeout(() => fn.apply(this, args), wait); };
}

const N_ICONS = {
  plug: '<path d="M16 9V4h1c.55 0 1-.45 1-1s-.45-1-1-1H7c-.55 0-1 .45-1 1s.45 1 1 1h1v5c0 1.66-1.34 3-3 3v2h5.97v7l1 1 1-1v-7H19v-2c-1.66 0-3-1.34-3-3z"/>',
  power: '<path d="M13 3h-2v10h2V3zm4.83 2.17l-1.42 1.42C17.99 7.86 19 9.81 19 12c0 3.87-3.13 7-7 7s-7-3.13-7-7c0-2.19 1.01-4.14 2.58-5.42L6.17 5.17C4.23 6.82 3 9.26 3 12c0 4.97 4.03 9 9 9s9-4.03 9-9c0-2.74-1.23-5.18-3.17-6.83z"/>',
  restart: '<path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>',
  timer: '<path d="M15 1H9v2h6V1zm-4 13h2V8h-2v6zm8.03-6.61l1.42-1.42c-.43-.51-.9-.99-1.41-1.41l-1.42 1.42C16.07 4.74 14.12 4 12 4c-4.97 0-9 4.03-9 9s4.02 9 9 9 9-4.03 9-9c0-2.12-.74-4.07-1.97-5.61zM12 20c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/>',
  toggle: '<path d="M17 7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h10c2.76 0 5-2.24 5-5s-2.24-5-5-5zM7 15c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3z"/>',
  bolt: '<path d="M11 21h-1l1-7H7.5c-.88 0-.33-.75-.31-.78C8.48 10.94 10.42 7.54 13.01 3h1l-1 7h3.51c.4 0 .62.19.4.66C12.97 17.55 11 21 11 21z"/>',
  meter: '<path d="M21 11h-3.17l2.54-2.54-1.42-1.42L15 11h-2V9l3.96-3.96-1.42-1.42L13 6.17V3h-2v3.17L8.46 3.63 7.04 5.04 11 9v2H9L5.04 7.04 3.63 8.46 6.17 11H3v2h3.17l-2.54 2.54 1.42 1.42L9 13h2v2l-3.96 3.96 1.42 1.42L11 17.83V21h2v-3.17l2.54 2.54 1.42-1.42L13 15v-2h2l3.96 3.96 1.42-1.42L17.83 13H21z"/>',
  chevron: '<path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>',
};

function nSvg(icon, size = 22) {
  return `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="currentColor">${N_ICONS[icon]}</svg>`;
}

function nThemeVars(isDark, accentHex) {
  const accent = accentHex || "#006B3F";
  const rgb = nHexToRgb(accent);
  return {
    bg: isDark ? "rgba(30, 33, 40, 0.95)" : "rgba(255, 255, 255, 0.95)",
    cardBg: isDark ? "rgba(40, 44, 52, 0.8)" : "rgba(245, 247, 250, 0.8)",
    cardBgHover: isDark ? "rgba(50, 55, 65, 0.9)" : "rgba(235, 238, 245, 0.9)",
    text: isDark ? "#e4e6eb" : "#1a1c20",
    textSec: isDark ? "rgba(228, 230, 235, 0.6)" : "rgba(26, 28, 32, 0.5)",
    accent,
    accentLight: isDark ? `rgba(${rgb}, 0.15)` : `rgba(${rgb}, 0.1)`,
    accentMid: isDark ? `rgba(${rgb}, 0.25)` : `rgba(${rgb}, 0.18)`,
    accentShadow: `rgba(${rgb}, 0.4)`,
    border: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)",
    onColor: "#4caf50", offColor: isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.25)",
    isDark,
    volBgStart: isDark ? `rgba(${rgb}, 0.38)` : `rgba(${rgb}, 0.26)`,
    volBgMid: isDark ? `rgba(${rgb}, 0.14)` : `rgba(${rgb}, 0.09)`,
  };
}

function nIsDark(theme) {
  return theme === "dark" || (theme === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);
}

function nAutoDiscover(hass) {
  if (!hass) return [];
  return Object.keys(hass.states)
    .filter(id => id.startsWith("switch.") && hass.states[id]?.attributes?.device_class === "outlet"
      && (id.includes("netio") || hass.states[id]?.attributes?.friendly_name?.toLowerCase().includes("netio")
          || hass.states[id]?.attributes?.friendly_name?.toLowerCase().includes("output")))
    .sort();
}

function nBaseStyles(t) {
  return `
    :host { display: block; --accent: ${t.accent}; --accent-light: ${t.accentLight}; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    .n-card {
      background: ${t.bg}; border-radius: 24px; padding: 20px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: ${t.text}; backdrop-filter: blur(20px); border: 1px solid ${t.border};
    }
    .n-header {
      display: flex; align-items: center; gap: 14px; margin-bottom: 16px; padding: 0 4px;
    }
    .n-header-icon {
      width: 42px; height: 42px; border-radius: 14px;
      background: linear-gradient(135deg, ${t.accent}, #2e9e6e);
      display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0;
    }
    .n-header-content { flex: 1; min-width: 0; }
    .n-header-title { font-size: 16px; font-weight: 700; letter-spacing: -0.3px; line-height: 1.3; }
    .n-header-sub { font-size: 11px; color: ${t.textSec}; font-weight: 500; }
    .n-header-badge {
      background: ${t.accentLight}; color: ${t.accent};
      font-size: 13px; font-weight: 700; padding: 5px 11px; border-radius: 12px; white-space: nowrap;
    }
    .n-global {
      display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; padding: 0 4px;
    }
    .n-global-chip {
      font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 10px;
      background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)'}; color: ${t.textSec};
      white-space: nowrap;
    }
    .n-global-chip b { color: ${t.text}; font-weight: 700; }
    .outputs-container { display: flex; flex-direction: column; gap: 8px; }
    .output-card {
      background: ${t.cardBg}; border-radius: 18px; overflow: hidden;
      transition: all 0.3s cubic-bezier(0.25,0.1,0.25,1); border: 1px solid transparent;
    }
    .output-card:hover { background: ${t.cardBgHover}; }
    .output-card.expanded {
      border-color: ${t.isDark ? 'rgba(0,107,63,0.25)' : 'rgba(0,107,63,0.15)'};
      background: ${t.isDark ? 'rgba(45,48,58,0.9)' : 'rgba(240,242,248,0.95)'};
    }
    .output-card.off { opacity: 0.6; }
    .output-card.off .out-power-bg { opacity: 0 !important; }
    .out-main { position: relative; cursor: pointer; padding: 14px 16px; overflow: hidden; }
    .out-power-bg {
      position: absolute; top: 0; left: 0; height: 100%; width: 100%;
      background: linear-gradient(90deg, ${t.volBgStart} 0%, ${t.volBgMid} 70%, transparent 100%);
      transition: opacity 0.5s ease; pointer-events: none;
    }
    .out-content { position: relative; display: flex; align-items: center; gap: 12px; z-index: 1; }
    .out-icon {
      width: 40px; height: 40px; border-radius: 12px;
      background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'};
      display: flex; align-items: center; justify-content: center;
      color: ${t.textSec}; transition: all 0.3s ease; flex-shrink: 0;
    }
    .out-icon.on { background: linear-gradient(135deg, ${t.accent}, #2e9e6e); color: white; }
    .out-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
    .out-name { font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .out-detail { font-size: 11px; color: ${t.textSec}; font-weight: 500; }
    .out-badge {
      font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 10px;
      white-space: nowrap; min-width: 36px; text-align: center; flex-shrink: 0;
    }
    .out-badge.on { color: ${t.onColor}; background: ${t.isDark ? 'rgba(76,175,80,0.15)' : 'rgba(76,175,80,0.1)'}; }
    .out-badge.off { color: ${t.offColor}; background: ${t.isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)'}; }
    .out-chevron { color: ${t.textSec}; transition: transform 0.3s ease; flex-shrink: 0; }
    .out-chevron.rotated { transform: rotate(180deg); }
    .out-controls {
      padding: 4px 16px 16px; display: flex; flex-direction: column; gap: 12px;
      animation: slideDown 0.3s cubic-bezier(0.25,0.1,0.25,1);
    }
    @keyframes slideDown { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
    .ctrl-row { display: flex; gap: 8px; flex-wrap: wrap; }
    .n-btn {
      display: flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 12px; border: none;
      background: ${t.isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'};
      color: ${t.textSec}; cursor: pointer; font-size: 12px; font-weight: 600;
      transition: all 0.2s ease; white-space: nowrap;
    }
    .n-btn:hover { background: ${t.isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}; color: ${t.text}; }
    .n-btn.primary { background: ${t.accentLight}; color: ${t.accent}; }
    .n-btn.primary:hover { background: ${t.accentMid}; }
    .n-btn.danger { background: ${t.isDark ? 'rgba(239,83,80,0.12)' : 'rgba(239,83,80,0.08)'}; color: #ef5350; }
    .n-btn.danger:hover { background: ${t.isDark ? 'rgba(239,83,80,0.2)' : 'rgba(239,83,80,0.15)'}; }
    .n-btn.on-btn { background: ${t.isDark ? 'rgba(76,175,80,0.15)' : 'rgba(76,175,80,0.1)'}; color: #4caf50; }
    .n-btn.off-btn { background: ${t.isDark ? 'rgba(239,83,80,0.12)' : 'rgba(239,83,80,0.08)'}; color: #ef5350; }
    .energy-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 6px;
    }
    .energy-chip {
      padding: 8px 10px; border-radius: 10px;
      background: ${t.isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'};
      border: 1px solid ${t.border}; text-align: center;
    }
    .energy-val { font-size: 16px; font-weight: 700; color: ${t.text}; }
    .energy-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: ${t.textSec}; margin-top: 2px; }
    .n-empty {
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; padding: 30px 20px; gap: 8px; color: ${t.textSec};
    }
    .n-empty p { font-size: 14px; font-weight: 600; }
    .n-empty span { font-size: 12px; opacity: 0.6; text-align: center; }
  `;
}

// ─── Registration ───────────────────────────────────────────────────
window.customCards = window.customCards || [];
if (!window.customCards.find(c => c.type === "netio-card")) {
  window.customCards.push({
    type: "netio-card",
    name: "NETIO",
    description: "NETIO PDU control card with energy metering",
    preview: true,
    documentationURL: "https://github.com/tuldener/ha-netio",
  });
}

// ─── Main Card ──────────────────────────────────────────────────────
class NetioCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._expanded = {};
    this._rendered = false;
  }

  static getConfigElement() { return document.createElement("netio-card-editor"); }
  static getStubConfig() { return { title: "NETIO", entities: [], show_energy: true, show_actions: true, theme: "auto", accent_color: "" }; }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { title: "NETIO", entities: [], show_energy: true, show_actions: true, theme: "auto", accent_color: "", ...config };
    this._rendered = false;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) { this._render(); return; }
    this._updateExisting();
  }

  _getOutputs() {
    if (!this._hass) return [];
    let entityIds = this._config.entities || [];
    if (!entityIds.length) entityIds = nAutoDiscover(this._hass);
    return entityIds.map(eid => {
      const entity = this._hass.states[eid];
      if (!entity) return null;
      return { entityId: eid, entity, name: entity.attributes.friendly_name || eid };
    }).filter(Boolean);
  }

  _shortName(fullName) {
    if (!fullName) return fullName;
    return fullName.replace(/^NETIO\s+/i, "").replace(/^netio_/i, "") || fullName;
  }

  _isOn(o) { return o.entity.state === "on"; }

  _sensorVal(outputName, suffix) {
    if (!this._hass) return null;
    const prefix = outputName.toLowerCase().replace(/[^a-z0-9]/g, "_");
    for (const [id, state] of Object.entries(this._hass.states)) {
      if (id.startsWith("sensor.") && id.includes(prefix) && id.endsWith(suffix)) {
        const v = parseFloat(state.state);
        return isNaN(v) ? null : v;
      }
    }
    return null;
  }

  _globalSensor(suffix) {
    if (!this._hass) return null;
    for (const [id, state] of Object.entries(this._hass.states)) {
      if (id.startsWith("sensor.") && id.includes("netio") && id.endsWith(suffix) && !id.includes("output")) {
        const v = parseFloat(state.state);
        return isNaN(v) ? null : v;
      }
    }
    return null;
  }

  _findButtonEntity(outputEntityId, action) {
    if (!this._hass) return null;
    const base = outputEntityId.replace("switch.", "button.").replace(/_output_/, "_output_");
    const candidates = Object.keys(this._hass.states).filter(id =>
      id.startsWith("button.") && id.includes(action)
    );
    // Match by trying to find the button that shares the same output name segment
    const switchName = outputEntityId.replace("switch.", "");
    return candidates.find(id => {
      const btnName = id.replace("button.", "");
      // They share a common prefix (the device + output part)
      const commonParts = switchName.split("_");
      return commonParts.some(p => p.length > 2 && btnName.includes(p)) && btnName.includes(action);
    }) || null;
  }

  _toggleExpand(entityId) {
    const was = this._expanded[entityId];
    this._expanded = {};
    if (!was) this._expanded[entityId] = true;
    this._rendered = false;
    this._render();
  }

  async _callService(domain, service, data) {
    if (this._hass) await this._hass.callService(domain, service, data);
  }

  async _pressButton(entityId) {
    if (this._hass) await this._hass.callService("button", "press", { entity_id: entityId });
  }

  _updateExisting() {
    const r = this.shadowRoot; if (!r) return;
    const outputs = this._getOutputs();
    const existing = r.querySelectorAll(".output-card");
    if (!existing || existing.length !== outputs.length) { this._rendered = false; this._render(); return; }

    const onCount = outputs.filter(o => this._isOn(o)).length;
    const badge = r.querySelector(".n-header-badge");
    if (badge) badge.textContent = `${onCount}/${outputs.length}`;

    // Update global sensors
    const globalChips = r.querySelectorAll(".n-global-chip");
    const voltage = this._globalSensor("voltage");
    const frequency = this._globalSensor("frequency");
    const totalLoad = this._globalSensor("total_load");
    // Simple refresh of chips is handled by full render on significant changes

    outputs.forEach(o => {
      const card = r.querySelector(`.output-card[data-entity="${o.entityId}"]`);
      if (!card) return;
      const isOn = this._isOn(o);
      card.classList.toggle("off", !isOn);
      const icon = card.querySelector(".out-icon");
      if (icon) { icon.classList.toggle("on", isOn); icon.innerHTML = nSvg(isOn ? "plug" : "power"); }
      const badge = card.querySelector(".out-badge");
      if (badge) { badge.className = `out-badge ${isOn ? 'on' : 'off'}`; badge.textContent = isOn ? nT("on") : nT("off"); }
      const bg = card.querySelector(".out-power-bg");
      if (bg) bg.style.opacity = isOn ? "1" : "0";
    });
  }

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    const outputs = this._getOutputs();
    const t = nThemeVars(nIsDark(this._config.theme), this._config.accent_color || "");
    const onCount = outputs.filter(o => this._isOn(o)).length;
    const voltage = this._globalSensor("voltage");
    const frequency = this._globalSensor("frequency");
    const totalLoad = this._globalSensor("total_load");

    this.shadowRoot.innerHTML = `
      <style>${nBaseStyles(t)}</style>
      <div class="n-card">
        <div class="n-header">
          <div class="n-header-icon">${nSvg('plug', 24)}</div>
          <div class="n-header-content">
            <h2 class="n-header-title">${nEscape(this._config.title)}</h2>
            <span class="n-header-sub">${outputs.length} ${nPlural(outputs.length, nT('output_1'), nT('output_n'))}</span>
          </div>
          <div class="n-header-badge">${onCount}/${outputs.length}</div>
        </div>
        ${this._config.show_energy && (voltage != null || totalLoad != null) ? `
        <div class="n-global">
          ${voltage != null ? `<span class="n-global-chip"><b>${voltage.toFixed(1)} V</b> ${nT("voltage")}</span>` : ''}
          ${frequency != null ? `<span class="n-global-chip"><b>${frequency.toFixed(1)} Hz</b> ${nT("frequency")}</span>` : ''}
          ${totalLoad != null ? `<span class="n-global-chip"><b>${totalLoad} W</b> ${nT("total_load")}</span>` : ''}
        </div>` : ''}
        <div class="outputs-container">
          ${outputs.length > 0 ? outputs.map(o => this._renderOutput(o, t)).join("") :
            `<div class="n-empty">${nSvg('plug', 48)}<p>${nT("no_outputs")}</p><span>${nT("no_outputs_hint")}</span></div>`}
        </div>
      </div>
    `;
    this._rendered = true;
    this._attachEvents();
  }

  _renderOutput(o, t) {
    const exp = this._expanded[o.entityId] || false;
    const isOn = this._isOn(o);
    const load = this._sensorVal(o.name, "load");
    const detailParts = [];
    if (isOn && load != null) detailParts.push(`${load} W`);
    if (!isOn) detailParts.push(nT("off"));

    return `
      <div class="output-card ${exp ? 'expanded' : ''} ${isOn ? '' : 'off'}" data-entity="${o.entityId}">
        <div class="out-main" data-toggle="${o.entityId}">
          <div class="out-power-bg" style="opacity: ${isOn ? 1 : 0}"></div>
          <div class="out-content">
            <div class="out-icon ${isOn ? 'on' : ''}">${nSvg(isOn ? 'plug' : 'power')}</div>
            <div class="out-info">
              <span class="out-name">${nEscape(this._shortName(o.name))}</span>
              <span class="out-detail">${detailParts.join(' · ')}</span>
            </div>
            <div class="out-badge ${isOn ? 'on' : 'off'}">${isOn ? nT("on") : nT("off")}</div>
            <div class="out-chevron ${exp ? 'rotated' : ''}">${nSvg('chevron', 20)}</div>
          </div>
        </div>
        ${exp ? this._renderControls(o, t) : ''}
      </div>
    `;
  }

  _renderControls(o, t) {
    const isOn = this._isOn(o);
    const current = this._sensorVal(o.name, "current");
    const load = this._sensorVal(o.name, "load");
    const energy = this._sensorVal(o.name, "energy");
    const pf = this._sensorVal(o.name, "power_factor");

    const restartBtn = this._findButtonEntity(o.entityId, "restart");
    const shortOnBtn = this._findButtonEntity(o.entityId, "short_on");
    const toggleBtn = this._findButtonEntity(o.entityId, "toggle");

    return `
      <div class="out-controls">
        <div class="ctrl-row">
          <button class="n-btn ${isOn ? 'off-btn' : 'on-btn'}" data-switch="${o.entityId}">
            ${nSvg('power', 16)} ${isOn ? nT("off") : nT("on")}
          </button>
          ${this._config.show_actions && toggleBtn ? `<button class="n-btn primary" data-press="${toggleBtn}">${nSvg('toggle', 16)} ${nT("toggle")}</button>` : ''}
          ${this._config.show_actions && restartBtn ? `<button class="n-btn danger" data-press="${restartBtn}">${nSvg('restart', 16)} ${nT("restart")}</button>` : ''}
          ${this._config.show_actions && shortOnBtn ? `<button class="n-btn" data-press="${shortOnBtn}">${nSvg('timer', 16)} ${nT("short_on")}</button>` : ''}
        </div>
        ${this._config.show_energy && (current != null || load != null || energy != null) ? `
        <div class="energy-grid">
          ${load != null ? `<div class="energy-chip"><div class="energy-val">${load}</div><div class="energy-label">W</div></div>` : ''}
          ${current != null ? `<div class="energy-chip"><div class="energy-val">${current}</div><div class="energy-label">mA</div></div>` : ''}
          ${energy != null ? `<div class="energy-chip"><div class="energy-val">${energy}</div><div class="energy-label">Wh</div></div>` : ''}
          ${pf != null ? `<div class="energy-chip"><div class="energy-val">${pf.toFixed(2)}</div><div class="energy-label">PF</div></div>` : ''}
        </div>` : ''}
      </div>
    `;
  }

  _attachEvents() {
    const r = this.shadowRoot; if (!r) return;
    r.querySelectorAll("[data-toggle]").forEach(el => {
      el.addEventListener("click", e => {
        if (e.target.closest("[data-switch]") || e.target.closest("[data-press]")) return;
        this._toggleExpand(el.dataset.toggle);
      });
    });
    r.querySelectorAll("[data-switch]").forEach(el => {
      el.addEventListener("click", e => {
        e.stopPropagation();
        const eid = el.dataset.switch;
        const isOn = this._hass.states[eid]?.state === "on";
        this._callService("switch", isOn ? "turn_off" : "turn_on", { entity_id: eid });
      });
    });
    r.querySelectorAll("[data-press]").forEach(el => {
      el.addEventListener("click", e => {
        e.stopPropagation();
        this._pressButton(el.dataset.press);
      });
    });
  }

  getCardSize() { return 1 + this._getOutputs().length; }
}


// ─── Card Editor ────────────────────────────────────────────────────
class NetioCardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._config = {}; }
  setConfig(config) { this._config = { ...config }; this._render(); }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .editor { padding: 16px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .field { margin-bottom: 12px; }
        label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 4px; color: var(--primary-text-color, #333); }
        input, select { width: 100%; padding: 8px 12px; border: 1px solid var(--divider-color, #ddd); border-radius: 8px; font-size: 14px; background: var(--card-background-color, #fff); color: var(--primary-text-color, #333); }
        .hint { font-size: 11px; color: var(--secondary-text-color, #888); margin-top: 2px; }
        .checkbox-field { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
        .checkbox-field input { width: auto; }
      </style>
      <div class="editor">
        <div class="field"><label>${nT("title")}</label><input type="text" id="title" value="${this._config.title || 'NETIO'}" /></div>
        <div class="field">
          <label>${nT("accent_color")}</label>
          <div style="display:flex;gap:8px;align-items:center;">
            <input type="color" id="accent_color" value="${this._config.accent_color || '#006B3F'}" style="width:48px;height:36px;padding:2px;border-radius:8px;cursor:pointer;" />
            <input type="text" id="accent_hex" value="${this._config.accent_color || '#006B3F'}" placeholder="#006B3F" style="flex:1;" />
            <button id="accent_reset" style="padding:6px 10px;border-radius:8px;border:1px solid var(--divider-color,#ddd);background:transparent;cursor:pointer;font-size:12px;">↺ ${nT("reset")}</button>
          </div>
          <div class="hint">${nT("accent_hint")}</div>
        </div>
        <div class="field"><label>${nT("design")}</label>
          <select id="theme">
            <option value="auto" ${this._config.theme === 'auto' ? 'selected' : ''}>${nT("auto")}</option>
            <option value="dark" ${this._config.theme === 'dark' ? 'selected' : ''}>${nT("dark")}</option>
            <option value="light" ${this._config.theme === 'light' ? 'selected' : ''}>${nT("light")}</option>
          </select>
        </div>
        <div class="checkbox-field"><input type="checkbox" id="show_energy" ${this._config.show_energy !== false ? 'checked' : ''} /><label for="show_energy">${nT("show_energy")}</label></div>
        <div class="checkbox-field"><input type="checkbox" id="show_actions" ${this._config.show_actions !== false ? 'checked' : ''} /><label for="show_actions">${nT("show_actions")}</label></div>
      </div>
    `;
    this.shadowRoot.getElementById("title").addEventListener("change", e => { this._config.title = e.target.value; this._fire(); });
    const cp = this.shadowRoot.getElementById("accent_color");
    const ch = this.shadowRoot.getElementById("accent_hex");
    cp.addEventListener("input", e => { ch.value = e.target.value; this._config.accent_color = e.target.value; this._fire(); });
    ch.addEventListener("change", e => { const v = e.target.value.trim(); if (/^#[0-9a-fA-F]{6}$/.test(v)) { cp.value = v; this._config.accent_color = v; this._fire(); } });
    this.shadowRoot.getElementById("accent_reset").addEventListener("click", () => { cp.value = "#006B3F"; ch.value = "#006B3F"; this._config.accent_color = ""; this._fire(); });
    this.shadowRoot.getElementById("theme").addEventListener("change", e => { this._config.theme = e.target.value; this._fire(); });
    this.shadowRoot.getElementById("show_energy").addEventListener("change", e => { this._config.show_energy = e.target.checked; this._fire(); });
    this.shadowRoot.getElementById("show_actions").addEventListener("change", e => { this._config.show_actions = e.target.checked; this._fire(); });
  }

  _fire() { this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true })); }
}

// ─── Define ─────────────────────────────────────────────────────────
const _def = (n, c) => { if (!customElements.get(n)) customElements.define(n, c); };
_def("netio-card", NetioCard);
_def("netio-card-editor", NetioCardEditor);

Promise.all([customElements.whenDefined("netio-card")]).then(() => {
  window.dispatchEvent(new Event("ll-rebuild"));
});

console.info(
  `%c NETIO-CARD %c v${CARD_VERSION} `,
  "color: white; background: #006B3F; font-weight: 700; padding: 2px 6px; border-radius: 4px 0 0 4px;",
  "color: #006B3F; background: #d4edda; font-weight: 700; padding: 2px 6px; border-radius: 0 4px 4px 0;"
);
