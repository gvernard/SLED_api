// Milky Way galactic plane (b = 0), drawn as a dashed great circle.
window.SURVEY_FOOTPRINTS = window.SURVEY_FOOTPRINTS || {};

window.SURVEY_FOOTPRINTS.galactic = {
    color: '#FF4DA6',
    style: { dashed: true, width: 1.5 },
    build: function () {
        const gp = [];
        for (let l = 0; l <= 360; l++) gp.push(gal2equ(l, 0));
        return [gp];
    }
};
