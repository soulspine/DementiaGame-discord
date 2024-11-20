import json
import os

defaultCode = "en"

def listModules(languageCode:str) -> list:
    if not os.path.exists(os.path.join("languages", languageCode)): return []
    return [f[:-5] for f in os.listdir(os.path.join("languages", languageCode)) if f.endswith(".json")]

def getModule(moduleName:str, languageCode:str) -> dict:
    path = os.path.join("languages", languageCode, f"{moduleName}.json")
    if not os.path.exists(path): return None
    with open(path, 'r', encoding="utf-8") as f:
        data = json.load(f)
    return data

def getCodes() -> dict:
    path = os.path.join("languages", "codes.json")
    if not os.path.exists(path): return None
    with open (path, 'r', encoding="utf-8") as f:
        data = json.load(f)
    return data