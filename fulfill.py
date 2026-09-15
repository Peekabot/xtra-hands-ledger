"""Map quote work type to TaskRabbit / Fiverr search URLs. No API."""
from urllib.parse import quote_plus

TR = {
    "husky bag pick up one time": "junk removal albany ny",
    "husky bag to wm holding": "junk removal albany ny",
    "on site wm bags": "handyman albany ny",
    "on site wm bags with pick up": "junk removal albany ny",
    "bag drop / pickup": "junk removal albany ny",
    "site prep": "yard work albany ny",
    "demo + haul": "junk removal albany ny",
    "surplus pickup": "junk removal albany ny",
    "other": "handyman albany ny",
}
FV = {
    "other": "flyer design",
}

def links(work=""):
    work = (work or "other").strip().lower()
    tr_q = TR.get(work, "junk removal albany ny")
    fv_q = FV.get(work, FV["other"])
    return {
        "tr_url": "https://www.taskrabbit.com/search?q=" + quote_plus(tr_q),
        "fv_url": "https://www.fiverr.com/search/gigs?query=" + quote_plus(fv_q),
    }
