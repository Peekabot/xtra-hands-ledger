"""Map quote work type to TaskRabbit / Fiverr search URLs. No API."""
from urllib.parse import quote_plus

TR = {
    "bag drop / pickup": "junk removal albany ny",
    "site prep": "yard work albany ny",
    "demo + haul": "junk removal albany ny",
    "surplus pickup": "junk removal albany ny",
    "other": "handyman albany ny",
}
FV = {
    "bag drop / pickup": "product photo editing",
    "site prep": "site plan drawing",
    "demo + haul": "product photo editing",
    "surplus pickup": "marketplace listing photos",
    "other": "flyer design",
}

def links(work=""):
    work = (work or "other").strip().lower()
    tr_q = TR.get(work, TR["other"])
    fv_q = FV.get(work, FV["other"])
    return {
        "tr_url": "https://www.taskrabbit.com/search?q=" + quote_plus(tr_q),
        "fv_url": "https://www.fiverr.com/search/gigs?query=" + quote_plus(fv_q),
    }
