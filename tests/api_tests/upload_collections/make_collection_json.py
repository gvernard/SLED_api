import json

'''ras = [242.30810, 172.96440, 69.56190, 308.42570, 181.62361, 169.57035]
decs = [65.54110, -12.53290, -12.28745, -47.39560, 43.53856, 7.76627]
description = "The lensed quasars used by the H0LICOW (H0 Lenses in COSMOGRAIL's Wellspring) project. Note that the original papers intended to use HE1104 but this was replaced by SDSSJ1206."
name = 'H0LiCOW'
access = 'PUB' 

ras = [22.80585, 35.27285, 63.65719, 72.09163, 98.80131, 109.01510, 115.71333, 133.22323, 158.39177, 172.50041, 178.82639, 210.39820, 216.15871, 239.29990, 240.41854, 242.30810, 293.62875, 294.60538, 311.83479, 317.72530, 319.21160, 350.41995]
decs = [43.97032, 35.93716, 5.57862, 12.46539, 51.95050, 47.14735, 36.57881, 5.25435, 7.19000, 38.20086, 19.66146, 15.22361, 22.93350, 37.35999, 43.27994, 65.54110, 50.42312, 66.81471, 26.73367, 21.51640, 2.42970, 5.46011]
description = "The Cosmic Lens All-Sky Survey (CLASS) is a search for gravitationally lensed compact radio sources. CLASS includes the lenses of the previous search Jodrell Bank–Very Large Array Astrometric Survey (JVAS) and the MIT-Green Bank (MG) survey. "
name = 'CLASS'
access = 'PUB' '''

ras = [12.61580, 26.31940, 29.67240, 38.13829, 41.64204, 69.56190, 125.41210, 128.07110, 141.23240, 172.96440, 186.53340, 203.89496, 208.9308, 223.75782, 228.91060, 245.10931, 306.54346, 328.03110, 35.27285, 62.09050, 138.25425, 147.84404, 150.36876, 166.63938, 169.57035, 181.62361, 204.77999, 213.94267, 216.15871, 220.72820, 230.43679, 240.41854, 242.30810, 252.68100, 278.41625, 308.42570, 332.87638, 33.56813, 61.79258, 173.66880, 241.50074, 351.42170]
decs = [-17.66930, -9.75475, -43.41780, -21.29046, -8.42669, -12.28745, 12.29191, 4.06789, 2.32358, -12.53290, -0.10061, 1.30153, -22.9565, 14.79301, 15.19309, 12.06130, -45.60753, -27.53040, 35.93716, -53.89990, 52.99133, 26.58719, 50.46595, -18.35672, 7.76627, 43.53856, 13.17750, 11.49539, 22.93350, 40.92655, 52.91350, 43.27994, 65.54110, 42.86369, -21.06111, -47.39560, 19.48700, -21.09307, -50.10025, -21.05625, -23.55612, -52.48750]
description = "Lensed quasars with measured time delays (or attempted monitoring), mainly composed from the literature review of Millon et al. 2020a, b"
name = 'Time-delay lenses'
access = 'PUB' 


lenses = []
for i in range(len(ras)):
    lens = {}
    lens['ra'] = ras[i]
    lens['dec'] = decs[i]
    lenses.append(lens)

collection = {}
collection['name'] = name
collection['access'] = access
collection['description'] = description
collection['lenses'] = lenses

with open(name+'.json', 'w') as f:
    json.dump(collection, f)