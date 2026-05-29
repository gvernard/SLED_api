// Shared coordinate transforms and the survey-footprint registry.
//
// Loaded before the per-survey footprint files (des.js, sdss.js, ...) and before
// lens_visualise.js. Each survey file self-registers into SURVEY_FOOTPRINTS as
//   SURVEY_FOOTPRINTS.<key> = { color, style, build }
// where build() returns an array of [RA, Dec] loops (a null entry marks an
// intentional gap). lens_visualise.js iterates the registry to build and draw the
// overlays. All transforms are J2000 and numerically verified.
window.SURVEY_FOOTPRINTS = window.SURVEY_FOOTPRINTS || {};

const ECL_OBLIQUITY = 23.43928;

// Galactic (l, b) deg -> equatorial (RA, Dec) deg.
function gal2equ(l, b) {
    const d2r = Math.PI / 180;
    const aGP = 192.85948 * d2r, dGP = 27.12825 * d2r, lCP = 122.93192 * d2r;
    l *= d2r; b *= d2r;
    const sinb = Math.sin(b), cosb = Math.cos(b);
    const dec = Math.asin(Math.sin(dGP) * sinb + Math.cos(dGP) * cosb * Math.cos(lCP - l));
    const y = cosb * Math.sin(lCP - l);
    const x = Math.cos(dGP) * sinb - Math.sin(dGP) * cosb * Math.cos(lCP - l);
    let ra = (aGP + Math.atan2(y, x)) / d2r;
    ra = ((ra % 360) + 360) % 360;
    return [ra, dec / d2r];
}

// Ecliptic (lon, lat) deg -> equatorial (RA, Dec) deg.
function ecl2equ(lon, lat) {
    const d2r = Math.PI / 180, eps = ECL_OBLIQUITY * d2r;
    const l = lon * d2r, b = lat * d2r;
    const dec = Math.asin(Math.sin(b) * Math.cos(eps) + Math.cos(b) * Math.sin(eps) * Math.sin(l));
    const y = Math.sin(l) * Math.cos(eps) - Math.tan(b) * Math.sin(eps);
    const x = Math.cos(l);
    let ra = Math.atan2(y, x) / d2r;
    ra = ((ra % 360) + 360) % 360;
    return [ra, dec / d2r];
}

// SDSS survey great-circle coords (eta, lambda) deg -> equatorial (RA, Dec) deg.
// Node = 95 deg, eta pole = 32.5 deg, matching idlutils etalambda_to_radec.
function sdssEtaLambda2equ(eta, lambda) {
    const d2r = Math.PI / 180, node = 95.0, etaPole = 32.5;
    const l = lambda * d2r, e = (eta + etaPole) * d2r;
    const x = -Math.sin(l);
    const y = Math.cos(l) * Math.cos(e);
    const z = Math.cos(l) * Math.sin(e);
    let ra = Math.atan2(y, x) / d2r + node;
    ra = ((ra % 360) + 360) % 360;
    return [ra, Math.asin(z) / d2r];
}

// Equatorial (RA, Dec) -> galactic latitude b, deg.
function equ2galLat(ra, dec) {
    const d2r = Math.PI / 180, aGP = 192.85948 * d2r, dGP = 27.12825 * d2r;
    ra *= d2r; dec *= d2r;
    const sinb = Math.sin(dGP) * Math.sin(dec) + Math.cos(dGP) * Math.cos(dec) * Math.cos(ra - aGP);
    return Math.asin(sinb) / d2r;
}

// Equatorial (RA, Dec) -> ecliptic latitude beta, deg.
function equ2eclLat(ra, dec) {
    const d2r = Math.PI / 180, eps = ECL_OBLIQUITY * d2r;
    ra *= d2r; dec *= d2r;
    const sinb = Math.sin(dec) * Math.cos(eps) - Math.cos(dec) * Math.sin(eps) * Math.sin(ra);
    return Math.asin(sinb) / d2r;
}

// Subdivide polygon edges so they curve correctly through the projection.
// Interpolates RA along the shortest direction so seam-wrapping edges behave.
function densifyPolygon(vertices, stepDeg) {
    const pts = [];
    for (let i = 0; i < vertices.length - 1; i++) {
        const a = vertices[i], b = vertices[i + 1];
        const dRa = ((b[0] - a[0] + 540) % 360) - 180;
        const dDec = b[1] - a[1];
        const steps = Math.max(1, Math.ceil(Math.max(Math.abs(dRa), Math.abs(dDec)) / stepDeg));
        for (let s = 0; s < steps; s++) {
            const t = s / steps;
            pts.push([a[0] + dRa * t, a[1] + dDec * t]);
        }
    }
    pts.push(vertices[vertices.length - 1]);
    return pts;
}
