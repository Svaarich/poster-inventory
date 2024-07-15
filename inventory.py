import requests
import json
import csv

class bcolors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKCYAN = '\033[96m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

print(f"{bcolors.OKBLUE}----------------------------------------------------{bcolors.ENDC}")
print(f"{bcolors.OKBLUE}|{bcolors.ENDC} - - - - - - -  {bcolors.HEADER}Автоінвентаризатор{bcolors.ENDC}  - - - - - - - {bcolors.OKBLUE}|{bcolors.ENDC}")
print(f"{bcolors.OKBLUE}----------------------------------------------------{bcolors.ENDC}\n")

token_input = input("Введіть токен інтеграції: \n")
print("")

if len(token_input) != 39:
    print(f"{bcolors.FAIL}Неправильний формат коду інтеграції. Спробуйте ще раз.{bcolors.ENDC}\n")
    input(f"Натисніть {bcolors.OKGREEN}ENTER{bcolors.ENDC} для виходу.")
else:
    token = "token=" + token_input
    storage_id_prefix = "&storage_id="
    inventory_id_prefix = "&inventory_id="
    get_all_storages_url = "https://joinposter.com/api/storage.getStorages?" + token
    get_all_storage_inventory_items_url = "https://joinposter.com/api/storage.getInventoryIngredients?" + token + storage_id_prefix
    get_storage_inventories_url = "https://joinposter.com/api/storage.getStorageInventories?" + token + storage_id_prefix
    all_items_url = "https://joinposter.com/api/storage.getStorageLeftovers?" + token + "&type=4"

    # list of headers
    headers = ["Назва"]
    filename = "inventory.csv"

    all_items_list = []
    storages = []
    all_items_inventory_in_storage = {}
    storage_inventories = {}



    # get all existed storages
    """
        [{
            "storage_id": "",
            "storage_name": "",
            "storage_adress": "",
            "delete": ""
        }]
    """
    def get_all_storages():
        url = get_all_storages_url
        response = requests.get(url)
        print("Завантажую список складів...\n")
        if response.status_code == 200:
            global storages
            storages = json.loads(response.text)["response"]
        else:
            print("Error: ", response.status_code)
    # -------------------------



    # get inventories for specified storage
    """
        [{
                "inventory_id": ,
                "storage_id": ,
                "date_start": "",
                "date_end": "",
                "date_set": "",
                "date_inventory": "",
                "sum": ,
                "sum_netto": ,
                "inventory_status": 
        }]
    """
    def get_storage_inventories(index, storageID):
        url = get_storage_inventories_url + storageID
        response = requests.get(url)
        if response.status_code == 200:
            global storage_inventories
            inventories = json.loads(response.text)["response"]
            if len(inventories) > 0:
                if index < len(inventories):
                    storage_inventories[storageID] = inventories[index]["inventory_id"]
                else:
                    return False
        return True
    # --------------------------------------



    # check if storage has inventory with "manufactures"
    # otherwise check next inventory
    """
        "response" : {
            "ingredients" : [],
            "manufactures" : [
                {item_1},
                {item_2}
            ],
            prepacks: []
        }
    """
    # check is valid and write to dict { storage_id : { "inventory" } }
    def get_and_parse_storage_inventories():
        print("Шукаю останні інвентаризації...\n")
        for storage in storages:
            id = storage["storage_id"]
            res = get_storage_inventories(0, id)
            print("Перевіряю склад: ", storage["storage_name"])
            if not res:
                print("ERR: Index out of range in last inventories list")
            if id in storage_inventories:
                response_text = get_inventory_for(id)
                index = 1
                while len(response_text["response"]["manufactures"]) <= 0:
                    result = get_storage_inventories(index, id)
                    if not result:
                        break
                    response_text = get_inventory_for(id)
                    index += 1
                else:
                    all_items_inventory_in_storage[id] = response_text["response"]["manufactures"]
            else:
                print()
                out = f"{bcolors.FAIL}! - Інвентаризацію не знайдено для: " + storage["storage_name"] + f"- !{bcolors.ENDC}"
                print(out)
                storages.remove(storage)
        print()

    # get inventory
    def get_inventory_for(storage_id):
        url = get_all_storage_inventory_items_url + storage_id + inventory_id_prefix + str(storage_inventories[storage_id])
        response = requests.get(url)
        if response.status_code == 200:
            global all_items_inventory_in_storage
            response_text = json.loads(response.text)
            if "response" in response_text:
                return response_text
            else:
                print("Error: ", response.status_code)
    # ---------------------------------------------------


    
    # get all items (tech cards) to extract names and ids
    """
        {
            "ingredient_id": "",
            "ingredient_name": "",
            "ingredient_left": "",
            "limit_value": "",
            "ingredient_unit": "kg",
            "ingredients_type": "",
            "storage_ingredient_sum": "",
            "prime_cost": ,
            "prime_cost_netto": "",
            "hidden": ""
        }
    """
    def get_all_items():
        url = all_items_url
        response = requests.get(url)
        print("Завантажую список товарів...\n")
        if response.status_code == 200:
            global all_items_list
            all_items_list = json.loads(response.text)["response"]
    #---------------------------------------------------------


    # check if storage inventory has intem from all items list and write to file
    def write_csv():
        create_file()
        print("Пишу елементи у таблицю...\n")
        with open(filename, "a", newline="", encoding="utf-8") as file:
            for item in all_items_list:
                row = []
                row.append(item["ingredient_name"]) # item name
                is_found = False
                # row creation
                for storage in all_items_inventory_in_storage:
                    is_found = False
                    for dish in all_items_inventory_in_storage[storage]:
                        if dish["item_id"] == item["ingredient_id"]:
                            gramms = float(dish["difference"]) * 1000
                            row.append(int(gramms))
                            is_found = True
                            # add empty cell if item is absent in the inventory list
                    if not is_found:
                        row.append("")
                # write
                writer = csv.writer(file)
                writer.writerow(row)
        # ------------------------------------------------------------------------

    # create file and write header
    def create_file():
        print("Створюю експорт файл...")
        # create header
        for storage in storages:
            name = storage["storage_name"]
            headers.append(name)
        # write header + create file
        with open(filename, "w+", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
    #-------------------------------


    # call get funcs
    get_all_storages()
    get_and_parse_storage_inventories()
    get_all_items()

    # call write func
    write_csv()

    # end of programm
    print("----------------------------------------------------")
    print(f"{bcolors.OKGREEN}Файл успішно створено.{bcolors.ENDC}")
    input(f"Натисніть {bcolors.OKGREEN}ENTER{bcolors.ENDC} для виходу.")

