"""
Static catalog of popular car brands and their common models, used to drive
the brand → model pickers on the frontend. Bundled (no external dependency);
the endpoint shape is kept generic so a live source (e.g. NHTSA vPIC) can
back it later. Anything missing is handled by the frontend's free-text
"Other" fallback.
"""
from django.utils import timezone

MIN_YEAR = 1980

CATALOG = {
    "Audi": ["A1", "A3", "A4", "A6", "Q2", "Q3", "Q5", "Q7", "TT", "e-tron"],
    "BMW": ["1 Series", "2 Series", "3 Series", "5 Series", "7 Series", "X1", "X3", "X5", "X6", "i3", "iX"],
    "BYD": ["Atto 3", "Dolphin", "Seal", "Song Plus", "Tang"],
    "Chevrolet": ["Aveo", "Camaro", "Captiva", "Cruze", "Malibu", "Silverado", "Spark", "Trailblazer"],
    "Citroën": ["Berlingo", "C3", "C4", "C5 Aircross"],
    "Daihatsu": ["Charade", "Hijet", "Mira", "Move", "Terios"],
    "Fiat": ["500", "Doblo", "Panda", "Punto", "Tipo"],
    "Ford": ["EcoSport", "Escape", "Everest", "Explorer", "F-150", "Fiesta", "Focus", "Mustang", "Ranger", "Transit"],
    "Honda": ["Accord", "City", "Civic", "CR-V", "Fit", "HR-V", "Jazz", "Odyssey", "Pilot", "Vezel"],
    "Hyundai": ["Accent", "Creta", "Elantra", "i10", "i20", "Kona", "Santa Fe", "Sonata", "Tucson", "Venue"],
    "Isuzu": ["D-Max", "MU-X", "NPR", "Trooper"],
    "Jeep": ["Cherokee", "Compass", "Grand Cherokee", "Renegade", "Wrangler"],
    "Kia": ["Cerato", "Picanto", "Rio", "Seltos", "Sorento", "Soul", "Sportage", "Stonic"],
    "Land Rover": ["Defender", "Discovery", "Discovery Sport", "Freelander", "Range Rover", "Range Rover Evoque", "Range Rover Sport"],
    "Lexus": ["ES", "GX", "IS", "LX", "NX", "RX", "UX"],
    "Mazda": ["Atenza", "Axela", "BT-50", "CX-3", "CX-30", "CX-5", "CX-9", "Demio", "Mazda2", "Mazda3", "Mazda6", "MX-5"],
    "Mercedes-Benz": ["A-Class", "C-Class", "CLA", "E-Class", "G-Class", "GLA", "GLC", "GLE", "S-Class", "Sprinter", "Vito"],
    "Mitsubishi": ["ASX", "Canter", "Colt", "Eclipse Cross", "L200", "Lancer", "Mirage", "Outlander", "Pajero", "RVR"],
    "Nissan": ["Almera", "Altima", "Juke", "Kicks", "Leaf", "March", "Navara", "Note", "Patrol", "Qashqai", "Sentra", "Serena", "Sunny", "Tiida", "X-Trail"],
    "Peugeot": ["2008", "208", "3008", "308", "5008", "508", "Partner"],
    "Porsche": ["911", "Cayenne", "Macan", "Panamera", "Taycan"],
    "Renault": ["Captur", "Clio", "Duster", "Kwid", "Megane"],
    "Subaru": ["Ascent", "BRZ", "Crosstrek", "Forester", "Impreza", "Legacy", "Levorg", "Outback", "WRX", "XV"],
    "Suzuki": ["Alto", "Baleno", "Celerio", "Ertiga", "Grand Vitara", "Jimny", "Swift", "Vitara", "Wagon R"],
    "Tesla": ["Model 3", "Model S", "Model X", "Model Y"],
    "Toyota": ["4Runner", "Allion", "Alphard", "Aqua", "Avensis", "C-HR", "Camry", "Corolla", "Fortuner", "Harrier", "Hiace", "Hilux", "Ist", "Kluger", "Land Cruiser", "Land Cruiser Prado", "Mark X", "Noah", "Passo", "Premio", "Probox", "RAV4", "Rush", "Sienta", "Succeed", "Vanguard", "Vitz", "Voxy", "Wish", "Yaris"],
    "Volkswagen": ["Amarok", "Golf", "Jetta", "Passat", "Polo", "T-Cross", "Tiguan", "Touareg", "Transporter"],
    "Volvo": ["S60", "S90", "V40", "V60", "XC40", "XC60", "XC90"],
}


def get_catalog():
    current_year = timezone.localdate().year
    return {
        "brands": [
            {"name": brand, "models": models}
            for brand, models in sorted(CATALOG.items())
        ],
        "years": list(range(current_year, MIN_YEAR - 1, -1)),
        "min_year": MIN_YEAR,
    }
