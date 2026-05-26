import re
import csv
import os

# Создаем файл
if not os.path.exists("phonebook_raw.csv"):
    data = [["lastname","firstname","surname","organization","position","phone","email"],
            ["Усольцев Олег Валентинович","","ФНС","Инспектор","","+7(495)888-88-88",""],
            ["Иванов Семён Семёнович","","Минфин","","+7(495)777-77-77","",""],
            ["Мартиняхин Виталий Геннадьевич","","ФНС","","+7-495-111-11-11","",""],
            ["Иванов Семён Семёнович","","Минфин","","8-495-777-77-77 доб.123","",""],
            ["Усольцев Олег Валентинович","","ФНС","Инспектор","","8(495)888-88-88 доб.321",""]]
    with open("phonebook_raw.csv","w",newline="",encoding="utf-8") as f:
        csv.writer(f).writerows(data)

with open("phonebook_raw.csv",encoding="utf-8") as f:
    rows = csv.reader(f,delimiter=",")
    contacts = list(rows)

# 1. ФИО
for row in contacts[1:]:
    fio = " ".join(row[:3]).split()
    row[:3] = fio + [""]*(3-len(fio))

# 2.Телефоны
for row in contacts:
    if len(row)>5 and row[5]:
        phone = re.sub(r"\D","",row[5])
        if len(phone)==11 and phone.startswith(("7","8")):
            phone = phone[1:]
        if len(phone)==10:
            row[5]=f"+7({phone[:3]}){phone[3:6]}-{phone[6:8]}-{phone[8:]}"
            if "доб" in row[5].lower():
                ext=re.search(r"доб\.?\s*(\d+)",row[5],re.I)
                if ext:
                    row[5]=f"+7({phone[:3]}){phone[3:6]}-{phone[6:8]}-{phone[8:]} доб.{ext.group(1)}"

# 3.Дубликаты
unique={}
for row in contacts[1:]:
    key=(row[0],row[1])
    if key not in unique:
        unique[key]=row
    else:
        for i in range(len(row)):
            if row[i] and not unique[key][i]:
                unique[key][i]=row[i]

result=[contacts[0]]+list(unique.values())

with open("phonebook.csv","w",encoding="utf-8",newline="") as f:
    csv.writer(f).writerows(result)

print("Готово! Проверьте файл phonebook.csv")

# Вывод программы:

print("\n" + "=" * 60)
print("РЕЗУЛЬТАТ ОБРАБОТКИ:")
print("=" * 60)

# Читаем и выводим результат
with open("phonebook.csv", encoding="utf-8") as f:
    result = list(csv.reader(f))

print(f"Всего записей в результате: {len(result) - 1}")
print("\nСодержимое файла phonebook.csv:")
print("-" * 60)

for i, row in enumerate(result):
    if i == 0:
        print("Заголовок:", row)
    else:
        print(f"{i:2}. {row[0]:15} {row[1]:10} {row[2]:20} | Телефон: {row[5] if len(row) > 5 else ''}")

print("=" * 60)

# Сравнение с исходными данными
print("\nСравнение с исходными данными:")
print("-" * 60)
with open("phonebook_raw.csv", encoding="utf-8") as f:
    original = list(csv.reader(f))

print(f"Исходных записей: {len(original) - 1}")
print(f"Результирующих записей: {len(result) - 1}")
print(f"Удалено дубликатов: {len(original) - len(result)}")