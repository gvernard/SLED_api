// DES (Dark Energy Survey) wide footprint (~5000 deg^2, South Galactic Cap).
// The real DR2/Y6 footprint is published only as a HEALPix mask; this is an
// approximate closed [RA, Dec] polygon tracing the paper's "tank"-shaped outline
// (arXiv 2101.05765): a wide quasi-rectangular far-south body (the SPT overlap,
// ~Dec -40..-68), a rounded intermediate region, and the equatorial Stripe-82
// extension (Dec ~ 0). It wraps across RA = 0 (spans RA ~ -54..+101), so with the
// default map centring (RA = 0 at the left edge) it draws split between the two
// map edges; the Map-centre toggle re-centres on RA = 0 to show it as one tank.
// The last vertex repeats the first to close the polygon.
window.SURVEY_FOOTPRINTS = window.SURVEY_FOOTPRINTS || {};

const DES_FOOTPRINT = [
    [-53, -55], [-43, -64], [-10, -68], [25, -67], [55, -60],
    [78, -50], [93, -35], [99, -18], [101, -3], [93, 1],
    [60, 3], [25, 4], [0, 4], [-25, 3], [-43, -2],
    [-50, -20], [-54, -38], [-53, -55]
];

window.SURVEY_FOOTPRINTS.des = {
    color: '#FF7B00',
    style: { width: 2 },
    build: function () {
        return [densifyPolygon(DES_FOOTPRINT, 1.5)];
    }
};
