import ast
import glob
import json
import os

BASE = os.path.join("localization", "translations")

ARABIC_INDIC = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"]
DEVANAGARI = ["०", "१", "२", "३", "४", "५", "६", "७", "८", "९"]
THAI = ["๐", "๑", "๒", "๓", "๔", "๕", "๖", "๗", "๘", "๙"]
BENGALI = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"]
KHMER = ["០", "១", "២", "៣", "៤", "៥", "៦", "៧", "៨", "៩"]
LAO = ["໐", "໑", "໒", "໓", "໔", "໕", "໖", "໗", "໘", "໙"]
BURMESE = ["၀", "၁", "၂", "၃", "၄", "၅", "၆", "၇", "၈", "၉"]

DEVANAGARI_LOCALES = {"hi_IN", "ne_NP"}
ARABIC_LOCALES = {
    "fa_AF",
    "fa_IR",
    "ur_PK",
    # all ar_* locales
    *[
        f"ar_{cc}"
        for cc in [
            "AE",
            "BH",
            "DZ",
            "EG",
            "IQ",
            "JO",
            "KW",
            "LB",
            "LY",
            "MA",
            "MR",
            "OM",
            "PS",
            "QA",
            "SA",
            "SD",
            "SY",
            "TN",
            "YE",
        ]
    ],
}
THAI_LOCALES = {"th_TH"}
BENGALI_LOCALES = {"bn_BD"}
KHMER_LOCALES = {"km_KH"}
LAO_LOCALES = {"lo_LA"}
BURMESE_LOCALES = {"my_MM"}


def choose_digits(locale):
    if locale in ARABIC_LOCALES:
        return ARABIC_INDIC
    if locale in DEVANAGARI_LOCALES:
        return DEVANAGARI
    if locale in THAI_LOCALES:
        return THAI
    if locale in BENGALI_LOCALES:
        return BENGALI
    if locale in KHMER_LOCALES:
        return KHMER
    if locale in LAO_LOCALES:
        return LAO
    if locale in BURMESE_LOCALES:
        return BURMESE
    # Western Arabic numerals for everything else
    return ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]


for path in glob.glob(os.path.join(BASE, "*.json")):
    fname = os.path.basename(path)
    if fname == "key_reference.json" or fname.endswith(".done"):
        continue

    locale = fname.split(".")[0]

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1) Fix the “digits as string” bug (Arabic files today)
    digits = data.get("digits")
    if isinstance(digits, str):
        try:
            parsed = ast.literal_eval(digits)
            if isinstance(parsed, (list, tuple)) and len(parsed) == 10:
                digits = list(parsed)
            else:
                digits = None
        except Exception:
            digits = None

    # 2) If no usable digits, assign based on locale
    if not (isinstance(digits, list) and len(digits) == 10):
        digits = choose_digits(locale)

    data["digits"] = digits

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Updated {locale}: digits = {''.join(digits)}")
