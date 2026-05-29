// Euclid Wide Survey region of interest (Scaramella et al. 2022, A&A 662, A112).
// The surveyed region is the EXTRA-galactic, EXTRA-ecliptic sky: |beta| >= 10 deg
// (ecliptic; the paper's exact zodiacal-light limit) AND |b| >= ~25 deg (galactic;
// the paper uses an E(B-V) dust contour relaxed from an original |b|>=20 cut, which
// we approximate by a constant galactic-latitude cut). The boundary is therefore
// made of ecliptic-cut arcs (kept only where the galactic cut is satisfied) and
// galactic-cut arcs (kept only where the ecliptic cut is satisfied), giving the
// characteristic two "mainlands" + two "islands" outline rather than four full
// circles. The real mask is a HEALPix file; this is an approximate reconstruction.
window.SURVEY_FOOTPRINTS = window.SURVEY_FOOTPRINTS || {};

const EUCLID_ECL_CUT = 10;   // |ecliptic latitude| >= 10 deg (exact, per paper)
const EUCLID_GAL_CUT = 25;   // |galactic latitude| >= ~25 deg (approx dust/density edge)

function euclidBoundary() {
    const segs = [];
    for (const beta of [EUCLID_ECL_CUT, -EUCLID_ECL_CUT]) {
        const seg = [];
        for (let lon = 0; lon <= 360; lon++) {
            const p = ecl2equ(lon, beta);
            seg.push(Math.abs(equ2galLat(p[0], p[1])) >= EUCLID_GAL_CUT ? p : null);
        }
        segs.push(seg);
    }
    for (const b of [EUCLID_GAL_CUT, -EUCLID_GAL_CUT]) {
        const seg = [];
        for (let l = 0; l <= 360; l++) {
            const p = gal2equ(l, b);
            seg.push(Math.abs(equ2eclLat(p[0], p[1])) >= EUCLID_ECL_CUT ? p : null);
        }
        segs.push(seg);
    }
    return segs;
}

window.SURVEY_FOOTPRINTS.euclid = {
    color: '#B26CFF',
    style: { width: 2 },
    build: euclidBoundary
};
