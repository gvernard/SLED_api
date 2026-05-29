const canvas = document.getElementById('skymap');
const ctx = canvas.getContext('2d');
const tooltip = document.getElementById('tooltip');
const loading = document.getElementById('loading');
const stats = document.getElementById('stats');

let lensData = [];
let transform = { scale: 1, offsetX: 0, offsetY: 0 };
let isDragging = false;
let lastMouseX = 0;
let lastMouseY = 0;
let hoveredPoint = null;
let pinnedPoint = null;
let isTooltipPinned = false;

let config = {
    pointSize: 4,
    colorScheme: 'type',
    showAxisLabels: false,
    centerRA: 180,  // RA at the map center: 180 = RA=0 at the left edge; 0 = centered on RA=0
    overlays: { des: false, sdss: false, euclid: false, galactic: false }
};

// Source-type colors (normalized buckets), chosen for visibility on the light map
const sourceTypeColors = {
    'Galaxy': '#E63946',
    'Quasar': '#2A9D8F',
    'Unknown': '#E9A100'
};

// Deflector-type colors are assigned dynamically from this palette (saturated
// mid/dark tones that read clearly on the white map, led by the SLED brand purple)
const lensTypePalette = ['#6F73DD','#E63946','#2A9D8F','#E9A100','#9C27B0','#1565C0','#2E7D32','#C2185B','#EF6C00','#5E35B1','#455A64'];
const lensTypeColors = {};

let redshiftChart = null;

// Legend highlight filter (null = show all)
let highlightFilter = null;

function getSourceType(systemType) {
    if (!systemType) return 'Unknown';
    systemType = systemType.trim().toLowerCase();

    if (systemType.includes('-')) {
        const parts = systemType.split('-');
        const sourceType = parts[parts.length - 1].trim();
        if (sourceType.includes('qso') || sourceType.includes('quasar')) return 'Quasar';
        if (sourceType.includes('gal') || sourceType.includes('galaxy')) return 'Galaxy';
        if (sourceType.includes('star')) return 'Galaxy';
    }
    if (systemType.includes('qso') || systemType.includes('quasar')) return 'Quasar';
    if (systemType.includes('gal') || systemType.includes('galaxy')) return 'Galaxy';
    if (systemType.includes('cluster')) return 'Galaxy';
    return 'Unknown';
}

function lensTypeLabel(point) {
    return point.lens_type ? point.lens_type : 'Unknown';
}

function resizeCanvas() {
    const container = document.getElementById('skymap-panel');
    canvas.width = container.clientWidth - 30;
    canvas.height = container.clientHeight - 30;
    drawSkyMap();
}

// Aitoff projection (hardcoded — the only projection used)
function project(ra, dec) {
    const lambda = ((((ra - config.centerRA + 540) % 360) - 180) * Math.PI) / 180;
    const phi = dec * Math.PI / 180;
    const alpha = Math.acos(Math.cos(phi) * Math.cos(lambda / 2));
    const sinc = alpha < 0.001 ? 1 : Math.sin(alpha) / alpha;
    const x = 2 * Math.cos(phi) * Math.sin(lambda / 2) / sinc;
    const y = Math.sin(phi) / sinc;
    return { x, y };
}

function worldToScreen(x, y) {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const scale = Math.min(canvas.width, canvas.height) / 4.5 * transform.scale;
    return {
        x: centerX + x * scale + transform.offsetX,
        y: centerY - y * scale + transform.offsetY
    };
}

function getColorForPoint(point) {
    if (config.colorScheme === 'type') {
        return sourceTypeColors[point.source_type_norm] || sourceTypeColors['Unknown'];
    } else if (config.colorScheme === 'lenstype') {
        return lensTypeColors[lensTypeLabel(point)] || '#64b5f6';
    } else if (config.colorScheme === 'source_z') {
        const z = parseFloat(point.source_z) || 0;
        const hue = Math.min(z / 5 * 240, 240);
        return `hsl(${240 - hue}, 70%, 60%)`;
    } else if (config.colorScheme === 'lens_z') {
        const z = parseFloat(point.lens_z) || 0;
        const hue = Math.min(z / 2 * 240, 240);
        return `hsl(${240 - hue}, 70%, 60%)`;
    }
    return '#64b5f6';
}

function drawMarker(ctx, x, y, size, markerType) {
    ctx.save();
    if (markerType === 'Quasar') {
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x - size, y - size); ctx.lineTo(x + size, y + size);
        ctx.moveTo(x + size, y - size); ctx.lineTo(x - size, y + size);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x - size, y); ctx.lineTo(x + size, y);
        ctx.moveTo(x, y - size); ctx.lineTo(x, y + size);
        ctx.stroke();
    } else if (markerType === 'Galaxy') {
        ctx.beginPath();
        ctx.arc(x, y, size, 0, 2 * Math.PI);
        ctx.fill();
    } else {
        ctx.beginPath();
        ctx.arc(x, y, size, 0, 2 * Math.PI);
        ctx.lineWidth = 2;
        ctx.stroke();
    }
    ctx.restore();
}

function drawPoint(ctx, screenX, screenY, point) {
    if (config.colorScheme === 'type') {
        drawMarker(ctx, screenX, screenY, config.pointSize, point.source_type_norm);
    } else {
        ctx.beginPath();
        ctx.arc(screenX, screenY, config.pointSize, 0, 2 * Math.PI);
        ctx.fill();
    }
}

// ---- Survey-footprint overlays ----
// Each survey's geometry lives in its own file under static/sled_visualise/footprints/
// (loaded before this script): galactic.js, euclid.js, des.js, sdss.js. Each self-
// registers into the global SURVEY_FOOTPRINTS registry as { color, style, build() },
// where build() returns an array of [RA, Dec] loops (a null entry marks an
// intentional gap). Shared coordinate transforms and densifyPolygon live in
// footprints/_coords.js. Draw order follows registry insertion order (= load order).

// A jump in projected-x larger than this means the path crossed the RA=0/360
// seam (left/right edge of the map) and the pen should lift rather than draw
// a line straight across the whole map.
const SEAM_THRESHOLD = 1.0;

// Per-survey [RA, Dec] loop lists, built once from the registry's build() fns.
const overlayGeom = {};
function buildOverlayGeom() {
    for (const key in SURVEY_FOOTPRINTS) {
        overlayGeom[key] = SURVEY_FOOTPRINTS[key].build();
    }
}

function strokeRaDecPolyline(pts, color, opts) {
    opts = opts || {};
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = opts.width || 2;
    if (opts.dashed) ctx.setLineDash([6, 5]);
    ctx.beginPath();
    let prev = null, penUp = true;
    for (let i = 0; i < pts.length; i++) {
        // A null entry is an intentional gap (e.g. clipped Euclid boundary): lift the pen.
        if (pts[i] === null) { penUp = true; prev = null; continue; }
        // Normalize RA into [0,360) so wrapping footprints (negative RA / RA>360)
        // stay within the projection's valid lambda range and don't shoot off-map.
        const ra = ((pts[i][0] % 360) + 360) % 360;
        const w = project(ra, pts[i][1]);
        const s = worldToScreen(w.x, w.y);
        if (prev && Math.abs(w.x - prev.x) > SEAM_THRESHOLD) penUp = true;
        if (penUp) { ctx.moveTo(s.x, s.y); penUp = false; } else { ctx.lineTo(s.x, s.y); }
        prev = w;
    }
    ctx.stroke();
    ctx.restore();
}

function drawOverlays() {
    for (const key in SURVEY_FOOTPRINTS) {
        if (!config.overlays[key]) continue;
        const fp = SURVEY_FOOTPRINTS[key];
        (overlayGeom[key] || []).forEach(loop => strokeRaDecPolyline(loop, fp.color, fp.style));
    }
}

function drawGrid() {
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.08)';
    ctx.lineWidth = 1;

    for (let ra = 0; ra <= 360; ra += 30) {
        ctx.beginPath();
        let first = true;
        for (let dec = -90; dec <= 90; dec += 2) {
            const s = worldToScreen(...Object.values(project(ra, dec)));
            if (first) { ctx.moveTo(s.x, s.y); first = false; } else { ctx.lineTo(s.x, s.y); }
        }
        ctx.stroke();
    }
    for (let dec = -60; dec <= 60; dec += 30) {
        ctx.beginPath();
        let first = true;
        for (let ra = 0; ra <= 360; ra += 2) {
            const s = worldToScreen(...Object.values(project(ra, dec)));
            if (first) { ctx.moveTo(s.x, s.y); first = false; } else { ctx.lineTo(s.x, s.y); }
        }
        ctx.stroke();
    }

    ctx.strokeStyle = 'rgba(111, 115, 221, 0.4)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    let first = true;
    for (let ra = 0; ra <= 360; ra += 1) {
        const s = worldToScreen(...Object.values(project(ra, 0)));
        if (first) { ctx.moveTo(s.x, s.y); first = false; } else { ctx.lineTo(s.x, s.y); }
    }
    ctx.stroke();

    if (config.showAxisLabels) {
        ctx.font = "11px 'basic-sans', 'Segoe UI', sans-serif";
        ctx.fillStyle = '#666';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        for (let ra = 0; ra <= 330; ra += 30) {
            const s = worldToScreen(...Object.values(project(ra, 0)));
            ctx.fillText(`${Math.round(ra / 15)}h`, s.x, s.y + 15);
        }
        for (let dec = -60; dec <= 60; dec += 30) {
            if (dec === 0) continue;
            const s = worldToScreen(...Object.values(project(config.centerRA, dec)));
            ctx.fillText(dec > 0 ? `+${dec}°` : `${dec}°`, s.x - 20, s.y);
        }
        ctx.font = "12px 'basic-sans', 'Segoe UI', sans-serif";
        ctx.fillStyle = '#6F73DD';
        const raS = worldToScreen(...Object.values(project(config.centerRA, 0)));
        ctx.fillText('RA', raS.x, raS.y + 35);
        const decS = worldToScreen(...Object.values(project(config.centerRA, 0)));
        ctx.save();
        ctx.translate(decS.x - 45, decS.y);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('Dec', 0, 0);
        ctx.restore();
    }
}

function matchesHighlightFilter(point) {
    if (!highlightFilter) return true;
    if (config.colorScheme === 'type') return point.source_type_norm === highlightFilter;
    if (config.colorScheme === 'lenstype') return lensTypeLabel(point) === highlightFilter;
    return true;
}

// Trace the projection boundary (the all-sky ellipse): RA=0 down the left edge,
// RA=360 down the right edge. Used to fill the map area white and outline it so
// it reads as a defined plot panel against the light page.
function drawBoundary() {
    // The projection outline is the seam (lambda = +/-180), i.e. the meridian
    // opposite the map center; trace just inside it on both sides.
    const seam = (((config.centerRA + 180) % 360) + 360) % 360;
    ctx.beginPath();
    let first = true;
    for (let dec = -90; dec <= 90; dec += 1) {
        const s = worldToScreen(...Object.values(project(seam + 0.0001, dec)));
        if (first) { ctx.moveTo(s.x, s.y); first = false; } else { ctx.lineTo(s.x, s.y); }
    }
    for (let dec = 90; dec >= -90; dec -= 1) {
        const s = worldToScreen(...Object.values(project(seam - 0.0001, dec)));
        ctx.lineTo(s.x, s.y);
    }
    ctx.closePath();
    ctx.save();
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.25)';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();
}

function drawSkyMap() {
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawBoundary();
    drawGrid();
    drawOverlays();

    if (highlightFilter) {
        lensData.filter(p => !matchesHighlightFilter(p)).forEach(point => {
            const s = worldToScreen(...Object.values(project(point.ra, point.dec)));
            ctx.globalAlpha = 0.15;
            const color = getColorForPoint(point);
            ctx.fillStyle = color; ctx.strokeStyle = color;
            drawPoint(ctx, s.x, s.y, point);
            ctx.globalAlpha = 1.0;
        });
    }

    const pointsToDraw = highlightFilter ? lensData.filter(matchesHighlightFilter) : lensData;
    pointsToDraw.forEach(point => {
        const s = worldToScreen(...Object.values(project(point.ra, point.dec)));
        const color = getColorForPoint(point);
        ctx.fillStyle = color; ctx.strokeStyle = color;
        drawPoint(ctx, s.x, s.y, point);

        if (hoveredPoint === point || pinnedPoint === point) {
            ctx.strokeStyle = '#1a1a1a';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(s.x, s.y, config.pointSize + 3, 0, 2 * Math.PI);
            ctx.stroke();
        }
    });

    const shownCount = pointsToDraw.length;
    const highlightText = highlightFilter ? ` | Highlighted: ${highlightFilter} (${shownCount})` : '';
    stats.textContent = `Showing ${lensData.length} system${lensData.length === 1 ? '' : 's'}${highlightText}`;
}

function findPointAtMouse(mouseX, mouseY) {
    const threshold = config.pointSize + 5;
    const rect = canvas.getBoundingClientRect();
    const cx = mouseX - rect.left;
    const cy = mouseY - rect.top;
    for (let point of lensData) {
        const s = worldToScreen(...Object.values(project(point.ra, point.dec)));
        const dx = s.x - cx;
        const dy = s.y - cy;
        if (Math.sqrt(dx * dx + dy * dy) < threshold) return point;
    }
    return null;
}

function infoRow(label, value) {
    const row = document.createElement('div');
    row.className = 'info-row';
    const l = document.createElement('span');
    l.className = 'info-label';
    l.textContent = label;
    const v = document.createElement('span');
    v.className = 'info-value';
    if (value instanceof Node) { v.appendChild(value); } else { v.textContent = value; }
    row.appendChild(l);
    row.appendChild(v);
    return row;
}

function showTooltip(point, x, y) {
    tooltip.innerHTML = '';

    const close = document.createElement('button');
    close.className = 'close-btn';
    close.textContent = '×';
    close.addEventListener('click', unpinTooltip);
    tooltip.appendChild(close);

    const h3 = document.createElement('h3');
    h3.textContent = point.name || 'Unknown System';
    tooltip.appendChild(h3);

    tooltip.appendChild(infoRow('RA:', `${point.ra.toFixed(4)}°`));
    tooltip.appendChild(infoRow('Dec:', `${point.dec.toFixed(4)}°`));
    tooltip.appendChild(infoRow('Source Redshift:', point.source_z != null ? String(point.source_z) : 'N/A'));
    tooltip.appendChild(infoRow('Deflector Redshift:', point.lens_z != null ? String(point.lens_z) : 'N/A'));
    tooltip.appendChild(infoRow('Source Type:', point.source_type || 'N/A'));
    tooltip.appendChild(infoRow('Deflector Type:', point.lens_type || 'N/A'));
    tooltip.appendChild(infoRow('Flag:', point.flag || 'N/A'));

    if (point.detail_url) {
        const link = document.createElement('a');
        link.href = point.detail_url;
        link.target = '_blank';
        link.textContent = 'View in SLED';
        tooltip.appendChild(infoRow('Details:', link));
    }

    tooltip.style.display = 'block';
    const rect = canvas.getBoundingClientRect();
    tooltip.style.left = (rect.left + x + 15) + 'px';
    tooltip.style.top = (rect.top + y + 15) + 'px';

    const tr = tooltip.getBoundingClientRect();
    if (tr.right > window.innerWidth) tooltip.style.left = (x - tr.width - 15) + 'px';
    if (tr.bottom > window.innerHeight) tooltip.style.top = (y - tr.height - 15) + 'px';
}

function hideTooltip() {
    if (!isTooltipPinned) tooltip.style.display = 'none';
}

function unpinTooltip() {
    isTooltipPinned = false;
    pinnedPoint = null;
    tooltip.classList.remove('pinned');
    tooltip.style.display = 'none';
    drawSkyMap();
}

function handleLegendClick(category) {
    highlightFilter = (highlightFilter === category) ? null : category;
    updateColorbar();
    drawSkyMap();
}

function makeLegendHeader(title) {
    const h4 = document.createElement('h4');
    h4.textContent = title + ' ';
    const hint = document.createElement('span');
    hint.className = 'legend-hint';
    hint.textContent = '(click to highlight)';
    h4.appendChild(hint);
    return h4;
}

function makeMarkerLegendItem(category, label, drawFn) {
    const item = document.createElement('div');
    item.className = 'legend-item' + (highlightFilter === category ? ' active' : '');
    const swatch = document.createElement('canvas');
    swatch.width = 30; swatch.height = 30;
    const span = document.createElement('span');
    span.className = 'legend-label';
    span.textContent = label;
    item.appendChild(swatch);
    item.appendChild(span);
    item.addEventListener('click', () => handleLegendClick(category));
    // draw swatch after it is in the DOM
    const sctx = swatch.getContext('2d');
    sctx.fillStyle = '#ffffff';
    sctx.fillRect(0, 0, 30, 30);
    drawFn(sctx);
    return item;
}

function updateColorbar() {
    const colorbar = document.getElementById('colorbar');
    colorbar.innerHTML = '';

    if (config.colorScheme === 'type') {
        colorbar.appendChild(makeLegendHeader('Source Type'));
        const list = document.createElement('div');
        list.className = 'legend-list';
        [['Quasar', 'Quasar'], ['Galaxy', 'Galaxy'], ['Unknown', 'Unknown']].forEach(([cat, label]) => {
            list.appendChild(makeMarkerLegendItem(cat, label, (sctx) => {
                const color = sourceTypeColors[cat];
                sctx.fillStyle = color; sctx.strokeStyle = color;
                drawMarker(sctx, 15, 15, 6, cat);
            }));
        });
        colorbar.appendChild(list);

    } else if (config.colorScheme === 'lenstype') {
        colorbar.appendChild(makeLegendHeader('Deflector Type'));
        const list = document.createElement('div');
        list.className = 'legend-list';
        const types = [...new Set(lensData.map(lensTypeLabel))].sort();
        types.forEach(t => {
            list.appendChild(makeMarkerLegendItem(t, t, (sctx) => {
                const color = lensTypeColors[t] || '#64b5f6';
                sctx.fillStyle = color;
                sctx.beginPath();
                sctx.arc(15, 15, 6, 0, 2 * Math.PI);
                sctx.fill();
            }));
        });
        colorbar.appendChild(list);

    } else {
        const h4 = document.createElement('h4');
        h4.textContent = config.colorScheme === 'source_z' ? 'Source Redshift' : 'Deflector Redshift';
        colorbar.appendChild(h4);
        const grad = document.createElement('div');
        grad.className = 'legend-gradient';
        colorbar.appendChild(grad);
        const labels = document.createElement('div');
        labels.className = 'legend-labels';
        const ends = config.colorScheme === 'source_z' ? ['0', '2.5', '5+'] : ['0', '1', '2+'];
        ends.forEach(t => { const s = document.createElement('span'); s.textContent = t; labels.appendChild(s); });
        colorbar.appendChild(labels);
    }
}

function toggleInstructions() {
    const instructions = document.getElementById('instructions');
    const btn = instructions.querySelector('.toggle-btn');
    if (instructions.classList.contains('collapsed')) {
        instructions.classList.remove('collapsed');
        btn.textContent = '−';
    } else {
        instructions.classList.add('collapsed');
        btn.textContent = '+';
    }
}

function toggleAxisLabels() {
    config.showAxisLabels = !config.showAxisLabels;
    const btn = document.getElementById('toggleAxisLabels');
    btn.classList.toggle('active', config.showAxisLabels);
    btn.textContent = config.showAxisLabels ? 'On' : 'Off';
    drawSkyMap();
}

// Canvas interaction
canvas.addEventListener('mousedown', (e) => {
    const point = findPointAtMouse(e.clientX, e.clientY);
    if (point) {
        pinnedPoint = point;
        isTooltipPinned = true;
        tooltip.classList.add('pinned');
        const rect = canvas.getBoundingClientRect();
        showTooltip(point, e.clientX - rect.left, e.clientY - rect.top);
        drawSkyMap();
    } else {
        isDragging = true;
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;
    }
});

canvas.addEventListener('mousemove', (e) => {
    if (isDragging) {
        transform.offsetX += e.clientX - lastMouseX;
        transform.offsetY += e.clientY - lastMouseY;
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;
        drawSkyMap();
    } else if (!isTooltipPinned) {
        const point = findPointAtMouse(e.clientX, e.clientY);
        if (point !== hoveredPoint) {
            hoveredPoint = point;
            drawSkyMap();
            if (point) {
                const rect = canvas.getBoundingClientRect();
                showTooltip(point, e.clientX - rect.left, e.clientY - rect.top);
            } else {
                hideTooltip();
            }
        }
    }
});

canvas.addEventListener('mouseup', () => { isDragging = false; });
canvas.addEventListener('mouseleave', () => {
    isDragging = false;
    if (!isTooltipPinned) {
        hoveredPoint = null;
        hideTooltip();
        drawSkyMap();
    }
});

canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    transform.scale = Math.max(0.5, Math.min(transform.scale * delta, 5));
    drawSkyMap();
});

document.getElementById('pointSize').addEventListener('input', (e) => {
    config.pointSize = parseFloat(e.target.value);
    document.getElementById('pointSizeValue').textContent = config.pointSize;
    drawSkyMap();
});

document.getElementById('colorScheme').addEventListener('change', (e) => {
    config.colorScheme = e.target.value;
    highlightFilter = null;
    updateColorbar();
    drawSkyMap();
    if (redshiftChart) createRedshiftChart();
});

[['overlayDES', 'des'], ['overlaySDSS', 'sdss'], ['overlayEuclid', 'euclid'], ['overlayGalactic', 'galactic']].forEach(([id, key]) => {
    const btn = document.getElementById(id);
    btn.addEventListener('click', () => {
        config.overlays[key] = !config.overlays[key];
        btn.classList.toggle('active', config.overlays[key]);
        drawSkyMap();
    });
});

document.getElementById('centerToggle').addEventListener('click', (e) => {
    config.centerRA = config.centerRA === 180 ? 0 : 180;
    e.currentTarget.classList.toggle('active', config.centerRA === 0);
    drawSkyMap();
});

document.getElementById('toggleAxisLabels').addEventListener('click', toggleAxisLabels);
document.getElementById('toggleInstructions').addEventListener('click', toggleInstructions);
document.getElementById('resetRedshiftZoom').addEventListener('click', () => { if (redshiftChart) redshiftChart.resetZoom(); });
document.getElementById('closeTooltip').addEventListener('click', unpinTooltip);
window.addEventListener('resize', resizeCanvas);

function createRedshiftChart() {
    const rctx = document.getElementById('redshiftChart').getContext('2d');
    const scatterData = lensData.map(point => ({
        x: parseFloat(point.lens_z),
        y: parseFloat(point.source_z),
        point: point
    })).filter(d => !isNaN(d.x) && !isNaN(d.y) && d.x > 0 && d.y > 0);

    if (redshiftChart) redshiftChart.destroy();

    redshiftChart = new Chart(rctx, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    type: 'line',
                    label: '1:1 (z_source = z_deflector)',
                    data: [{ x: 0, y: 0 }, { x: 10, y: 10 }],
                    borderColor: 'rgba(63, 87, 101, 0.7)',
                    borderDash: [6, 4],
                    borderWidth: 1.5,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    fill: false
                },
                {
                    type: 'scatter',
                    label: 'Lensing Systems',
                    data: scatterData,
                    backgroundColor: scatterData.map(d => getColorForPoint(d.point)),
                    pointRadius: 3,
                    pointHoverRadius: 5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            layout: { padding: 5 },
            scales: {
                x: {
                    type: 'linear', min: 0, max: 1.4,
                    title: { display: true, text: 'z_deflector', color: '#333', font: { size: 11 } },
                    ticks: { color: '#333', font: { size: 10 } },
                    grid: { color: 'rgba(0, 0, 0, 0.08)' }
                },
                y: {
                    type: 'linear', min: 0, max: 8.5,
                    title: { display: true, text: 'z_source', color: '#333', font: { size: 11 } },
                    ticks: { color: '#333', font: { size: 10 } },
                    grid: { color: 'rgba(0, 0, 0, 0.08)' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    filter: function(item) { return item.datasetIndex === 1; },
                    callbacks: {
                        label: function(context) {
                            const p = context.raw.point;
                            if (!p) return context.dataset.label;
                            return [
                                `System: ${p.name}`,
                                `Deflector: ${p.lens_type || 'N/A'}`,
                                `z_def: ${p.lens_z}`,
                                `z_src: ${p.source_z}`
                            ];
                        }
                    }
                },
                zoom: {
                    pan: { enabled: true, mode: 'xy' },
                    zoom: {
                        wheel: { enabled: true },
                        pinch: { enabled: true },
                        drag: { enabled: true, backgroundColor: 'rgba(100, 181, 246, 0.2)', borderColor: 'rgba(100, 181, 246, 0.8)', borderWidth: 1 },
                        mode: 'xy'
                    },
                    limits: { x: { min: 0, max: 2 }, y: { min: 0, max: 10 } }
                }
            }
        }
    });
}

function initData() {
    const raw = JSON.parse(document.getElementById('lens-data').textContent);
    lensData = raw.map(row => {
        row.ra = parseFloat(row.ra);
        row.dec = parseFloat(row.dec);
        row.source_type_norm = getSourceType(row.system_type);
        return row;
    }).filter(p => !isNaN(p.ra) && !isNaN(p.dec));

    // Assign a stable color to each deflector type present
    [...new Set(lensData.map(lensTypeLabel))].sort().forEach((t, i) => {
        lensTypeColors[t] = lensTypePalette[i % lensTypePalette.length];
    });

    buildOverlayGeom();
    loading.style.display = 'none';
    createRedshiftChart();
    updateColorbar();
    resizeCanvas();
}

initData();
