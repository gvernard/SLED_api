// SDSS Legacy imaging footprint: the contiguous North Galactic Cap "lune" plus the
// three South Galactic Cap scan stripes. Each is a rectangle in SDSS survey
// (eta, lambda) coords transformed to RA/Dec. Bounds are approximate (the true
// edges are ragged). The last vertex of each loop repeats the first to close it.
window.SURVEY_FOOTPRINTS = window.SURVEY_FOOTPRINTS || {};

// SGC imaging is three 2.5-deg-wide scan stripes (numbers 76, 82, 86). idlutils
// maps stripe -> eta as eta = stripe*2.5 - 57.5 (minus 180 for stripe > 50):
// stripe 82 -> eta -32.5 (= the celestial equator), 76 -> -47.5, 86 -> -22.5.
// The SGC arc spans lambda ~125..234 (RA ~310 -> 59 through RA = 0).
const SDSS_SGC_STRIPES = [-47.5, -32.5, -22.5]; // stripes 76, 82, 86
const SDSS_SGC_LAM_MIN = 125, SDSS_SGC_LAM_MAX = 234, SDSS_STRIPE_HALF = 1.25;

// Trace the contiguous NGC region as a rectangle in (eta, lambda): the
// characteristic curved "lune". etaMin -32.5 = celestial equator (stripe 10);
// etaMax 35 = stripe 37, the northern edge (~Dec +67 at the top of the lune).
function sdssNgcBoundary() {
    const lamMin = -63, lamMax = 63, etaMin = -33, etaMax = 35, step = 1;
    const pts = [];
    for (let lam = lamMin; lam <= lamMax; lam += step) pts.push(sdssEtaLambda2equ(etaMin, lam));
    for (let eta = etaMin; eta <= etaMax; eta += step) pts.push(sdssEtaLambda2equ(eta, lamMax));
    for (let lam = lamMax; lam >= lamMin; lam -= step) pts.push(sdssEtaLambda2equ(etaMax, lam));
    for (let eta = etaMax; eta >= etaMin; eta -= step) pts.push(sdssEtaLambda2equ(eta, lamMin));
    pts.push(pts[0]);
    return pts;
}

// Trace one scan stripe as a closed constant-eta band (eta +/- half-width).
function sdssStripe(etaC, lamMin, lamMax, half) {
    const pts = [], step = 1;
    for (let lam = lamMin; lam <= lamMax; lam += step) pts.push(sdssEtaLambda2equ(etaC - half, lam));
    for (let lam = lamMax; lam >= lamMin; lam -= step) pts.push(sdssEtaLambda2equ(etaC + half, lam));
    pts.push(pts[0]);
    return pts;
}

window.SURVEY_FOOTPRINTS.sdss = {
    color: '#F2C200',
    style: { width: 2 },
    build: function () {
        const loops = [sdssNgcBoundary()];
        for (const eta of SDSS_SGC_STRIPES) {
            loops.push(sdssStripe(eta, SDSS_SGC_LAM_MIN, SDSS_SGC_LAM_MAX, SDSS_STRIPE_HALF));
        }
        return loops;
    }
};
