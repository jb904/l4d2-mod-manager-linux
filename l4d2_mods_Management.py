import requests , os , time , json , shutil
from flask import Flask, jsonify, request, render_template, send_from_directory


##获取 mod_id ##
def get_mods_id(function_path_addons):
    mods_id = [i.replace(".vpk","") for i in os.listdir(function_path_addons) if i.endswith(".vpk")]
    return mods_id


##获取模组名字##
def get_mod_name(function_mod_id,function_get_sleep,function_error_num):
    url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    requests_data = {
        "itemcount" : 1,
        "publishedfileids[0]" : function_mod_id
    }

    mod_name = ""
    for i in range(function_error_num):
        try:
            if i:
                time.sleep(function_get_sleep)
            mod_information = requests.post(url,data=requests_data,timeout=15).json()
            mod_details = mod_information.get("response", {}).get("publishedfiledetails", [])
            if mod_details:
                mod_name = mod_details[0].get("title","").strip()
            return mod_name
        except (requests.RequestException,ValueError):
            continue
    else:
        return ""


##读取 data.json ##
def load_data():
    path_data_json = PATH_BASE + "/data.json"

    for i in (path_data_json, path_data_json + ".bak"):
        try:
            with open(i, "r", encoding="utf-8") as get_data_json:
                return json.load(get_data_json)
        except (ValueError, FileNotFoundError):
            continue

    return {}


##写入 data.json ##
def save_data(function_data):
    path_data_json = PATH_BASE + "/data.json"
    path_data_json_tmp = path_data_json + ".tmp"
    if os.path.exists(path_data_json):
        shutil.copy2(path_data_json, path_data_json + ".bak")

    with open(path_data_json_tmp,"w",encoding='utf-8') as save_data_json_tmp:
        json.dump(function_data,save_data_json_tmp,ensure_ascii=False,indent=2)
    os.replace(path_data_json_tmp,path_data_json)


##生成数据并写入 data.json ##
def sync_local():
    mods_id = get_mods_id(path_addons) + get_mods_id(path_data_ban)
    data = load_data()
    for i in mods_id:
        if i not in data:
            data[i] = {"mod_name" : "","mod_alias" : ""}
    save_data(data)
    return data


##获取 mod_name ##
def fetch_missing():
    data = load_data()
    mods_id = set(get_mods_id(path_addons)) | set(get_mods_id(path_data_ban))

    for i, m in data.items():
        if i not in mods_id or m["mod_name"]:
            continue
        name = get_mod_name(i, 1.5, 3)
        if name:
            m["mod_name"] = name
    save_data(data)
    return data


##禁用模组和启用模组##
def move_mods(mods_id,enabled):
    src_dir = path_data_ban if enabled else path_addons
    dst_dir = path_addons if enabled else path_data_ban
    result = {}
    for i in mods_id:
        src = src_dir + f"/{i}.vpk"
        dst = dst_dir + f"/{i}.vpk"
        if not os.path.exists(src):
            result[i] = "skipped"
        elif os.path.exists(dst):
            result[i] = "conflict"
        else:
            shutil.move(src, dst)
            result[i] = "ok"
    return result


##修改 mod_alias ##
def edit_mod_alias(function_data_alias):
    data = load_data()

    for item in function_data_alias:
        mid = item.get("id")
        if mid in data and "alias" in item:
            data[mid]["mod_alias"] = (item["alias"] or "").strip()
    save_data(data)
    return data


##
def mod_has_img(mid):
    for d in (path_addons, path_data_ban):
        if os.path.exists(os.path.join(d, mid + ".jpg")):
            return True
    return False


##创建 .l4d2-mod-management-data 目录##
raw = os.environ.get("L4D2_MOD_MANAGEMENT_DATA_PATH")
PATH_DATA = (raw or "").strip()

if not PATH_DATA:
    if raw is not None:
        print("环境变量为空或只有空格，将使用默认")
    home = os.environ.get("HOME")
    if not home:
        raise SystemExit("找不到 HOME 环境变量，请手动设置 L4D2_MOD_MANAGEMENT_DATA_PATH")
    PATH_DATA = home

PATH_BASE = PATH_DATA+"/.l4d2-mod-management-data"
if not os.path.exists(PATH_BASE):
    os.makedirs(PATH_BASE)


def get_mod_detail(mod_id, delay, retries):
    url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    payload = {"itemcount": 1, "publishedfileids[0]": mod_id}

    for i in range(retries):
        try:
            if i:
                time.sleep(delay)
            info = requests.post(url, data=payload, timeout=15).json()
            details = info.get("response", {}).get("publishedfiledetails", [])
            if not details:
                return {}
            d = details[0]
            return {
                "title": d.get("title", "").strip(),
                "preview_url": d.get("preview_url", ""),
            }
        except (requests.RequestException, ValueError):
            continue
    return {}


##获取 addons 路径##
path_config = PATH_BASE + "/config.txt"

path_addons = ""
if os.path.exists(path_config):
    with open(path_config, "r", encoding="utf-8") as f:
        path_addons = f.read().strip()

if not path_addons:
    for _ in range(5):
        path_addons = input("填写 addons 路径(绝对路径): ").strip()
        if os.path.isdir(path_addons):
            with open(path_config, "w", encoding="utf-8") as f:
                f.write(path_addons)
            break
        print("路径不存在，请重新填写")
    else:
        raise SystemExit("连续 5 次路径无效，已退出")


##创建 data-ban 目录##
path_data_ban = PATH_BASE + "/data-ban"

if not os.path.exists(path_data_ban):
    os.makedirs(path_data_ban)


app = Flask(__name__)
@app.route("/api/mods")
def api_mods():
    data = load_data()
    on = set(get_mods_id(path_addons))
    off = set(get_mods_id(path_data_ban))

    result = []
    for i, m in data.items():
        if i in on:
            status = "enabled"
        elif i in off:
            status = "disabled"
        else:
            status = "missing"

        result.append(
            {
                "mod_id" : i,
                "mod_name" : m["mod_name"],
                "mod_alias" : m["mod_alias"],
                "status" : status,
                "has_img": mod_has_img(i)
            }
        )

    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/img/<mod_id>.jpg")
def api_img(mod_id):
    for d in (path_addons, path_data_ban):
        if os.path.exists(os.path.join(d, mod_id + ".jpg")):
            return send_from_directory(d, mod_id + ".jpg")
    return "", 404


@app.route("/api/move", methods=["POST"])
def api_move():
    body = request.get_json(silent=True) or {}
    return jsonify(move_mods(body.get("ids", []), bool(body.get("enable", False))))


@app.route("/api/alias", methods=["POST"])
def api_alias():
    body = request.get_json(silent=True) or {}
    edit_mod_alias(body.get("mods", []))
    return jsonify({"ok": True})


@app.route("/api/refetch", methods=["POST"])
def api_refetch():
    body = request.get_json(silent=True) or {}
    data = load_data()

    for mid in body.get("ids", []):
        if mid not in data:
            continue

        info = get_mod_detail(mid, 1.5, 3)
        if not info:
            continue

        if info["title"]:
            data[mid]["mod_name"] = info["title"]

        img_path = os.path.join(path_addons, mid + ".jpg")
        if info["preview_url"] and not os.path.exists(img_path):
            try:
                r = requests.get(info["preview_url"], timeout=15)
                if r.status_code == 200:
                    with open(img_path, "wb") as f:
                        f.write(r.content)
            except requests.RequestException:
                pass

    save_data(data)
    return jsonify({"ok": True})


if __name__ == "__main__":
    sync_local()
    app.run(host="127.0.0.1", port=5000, debug=False)