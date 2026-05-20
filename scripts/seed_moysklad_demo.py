#!/usr/bin/env python3
"""
Seed a test MoySklad account with richer demo data for diploma screenshots.

Default mode is dry-run. To write data, set MOYSKLAD_TOKEN and pass --apply.
The script intentionally uses only Python stdlib so it can run without pip.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import gzip
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


BASE_URL = "https://api.moysklad.ru/api/remap/1.2"


@dataclass(frozen=True)
class ProductSpec:
    name: str
    category: str
    price: int


EMPLOYEES = [
    "Иванов Иван",
    "Петрова Мария",
    "Сидоров Алексей",
    "Козлова Анна",
    "Новиков Дмитрий",
    "Смирнова Екатерина",
    "Васильев Артем",
    "Морозова Дарья",
    "Федоров Павел",
    "Соколова Юлия",
    "Орлов Никита",
    "Михайлова Полина",
    "Андреев Максим",
    "Волкова Алина",
    "Лебедев Кирилл",
    "Кузнецова Софья",
    "Егоров Роман",
    "Николаева Вероника",
]

COUNTERPARTIES = [
    "ООО Ритейл Плюс",
    "ИП Кузьмин А. В.",
    "ООО Северный Маркет",
    "ООО Техника Дом",
    "ИП Белова М. С.",
    "ООО Онлайн Заказ",
    "ООО Южная Витрина",
    "ИП Громов Д. П.",
    "ООО Быстрый Склад",
    "ООО Городские Продажи",
    "ИП Романова Е. К.",
    "ООО Маркет Лайн",
    "ООО Альфа Торг",
    "ИП Фролов Н. И.",
    "ООО Восток Ритейл",
    "ООО Профи Снаб",
    "ИП Алексеева О. В.",
    "ООО Команда Продаж",
    "ООО Партнер Маркет",
    "ИП Миронов С. А.",
]

PRODUCTS = [
    ProductSpec("Ноутбук ASUS VivoBook 15", "Ноутбуки", 74990),
    ProductSpec("Ноутбук Lenovo IdeaPad 5", "Ноутбуки", 68990),
    ProductSpec("Ноутбук Apple MacBook Air 13", "Ноутбуки", 119990),
    ProductSpec("Монитор Samsung 27", "Мониторы", 24990),
    ProductSpec("Монитор LG UltraGear 24", "Мониторы", 21990),
    ProductSpec("Монитор AOC 32", "Мониторы", 32990),
    ProductSpec("Клавиатура Logitech MX Keys", "Периферия", 12990),
    ProductSpec("Клавиатура Keychron K2", "Периферия", 10990),
    ProductSpec("Мышь Razer DeathAdder", "Периферия", 6990),
    ProductSpec("Мышь Logitech MX Master 3S", "Периферия", 11990),
    ProductSpec("Наушники Sony WH-1000XM5", "Аудио", 34990),
    ProductSpec("Наушники JBL Tune 770NC", "Аудио", 9990),
    ProductSpec("Колонка JBL Charge 5", "Аудио", 14990),
    ProductSpec("Смартфон Samsung Galaxy A55", "Смартфоны", 42990),
    ProductSpec("Смартфон Xiaomi Redmi Note 13", "Смартфоны", 23990),
    ProductSpec("Смартфон Apple iPhone 15", "Смартфоны", 89990),
    ProductSpec("Планшет Samsung Galaxy Tab S9", "Планшеты", 69990),
    ProductSpec("Планшет Apple iPad Air", "Планшеты", 74990),
    ProductSpec("Принтер HP LaserJet", "Офисная техника", 18990),
    ProductSpec("МФУ Canon i-SENSYS", "Офисная техника", 27990),
    ProductSpec("Веб-камера Logitech C920", "Периферия", 8990),
    ProductSpec("SSD Samsung 1TB", "Комплектующие", 9990),
    ProductSpec("Роутер Keenetic Viva", "Сеть", 11990),
    ProductSpec("ИБП APC Back-UPS", "Офисная техника", 15990),
]


class MoySkladApi:
    def __init__(self, token: str, apply: bool, prefix: str, delay: float = 0.08):
        self.token = token
        self.apply = apply
        self.prefix = prefix
        self.delay = delay

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = BASE_URL + path
        if not self.apply and method == "GET":
            print(f"DRY {method} {path}")
            return {"rows": []}
        if not self.apply and method != "GET":
            print(f"DRY {method} {path}: {json.dumps(body, ensure_ascii=False)}")
            return {"meta": {"href": url, "type": path.rsplit('/', 1)[-1], "mediaType": "application/json"}, "name": body.get("name", "") if body else ""}

        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/json;charset=utf-8")
        req.add_header("Accept-Encoding", "gzip")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw_payload = resp.read()
                if "gzip" in (resp.headers.get("Content-Encoding") or "").lower():
                    raw_payload = gzip.decompress(raw_payload)
                payload = raw_payload.decode("utf-8")
                time.sleep(self.delay)
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} failed: HTTP {exc.code}: {text}") from exc

    def get_rows(self, entity: str, limit: int = 100) -> list[dict]:
        data = self.request("GET", f"/entity/{entity}?limit={limit}")
        return data.get("rows", [])

    def find_by_name(self, entity: str, name: str) -> dict | None:
        encoded = urllib.parse.quote(f'name="{name}"')
        rows = self.request("GET", f"/entity/{entity}?filter={encoded}&limit=1").get("rows", [])
        if rows:
            return rows[0]

        # Some MoySklad entities, especially employees, may normalize display names.
        # Fall back to a local exact-name scan to make reruns safer.
        rows = self.request("GET", f"/entity/{entity}?limit=1000").get("rows", [])
        for row in rows:
            if row.get("name") == name:
                return row
        return None

    def upsert_by_name(self, entity: str, body: dict) -> dict:
        existing = self.find_by_name(entity, body["name"]) if self.apply else None
        if existing:
            print(f"SKIP {entity}: {body['name']}")
            return existing
        print(f"CREATE {entity}: {body['name']}")
        return self.request("POST", f"/entity/{entity}", body)


def meta(obj: dict) -> dict:
    return obj["meta"]


def ref(obj: dict) -> dict:
    return {"meta": meta(obj)}


def ensure_base_objects(api: MoySkladApi) -> tuple[dict, dict, dict, dict]:
    if not api.apply:
        organization = {"meta": {"href": BASE_URL + "/entity/organization/dry", "type": "organization", "mediaType": "application/json"}, "name": f"{api.prefix} ООО Демо Организация"}
        store = {"meta": {"href": BASE_URL + "/entity/store/dry", "type": "store", "mediaType": "application/json"}, "name": f"{api.prefix} Основной склад"}
        currency = {"meta": {"href": BASE_URL + "/entity/currency/dry", "type": "currency", "mediaType": "application/json"}, "name": "руб"}
        price_type = {"meta": {"href": BASE_URL + "/context/companysettings/pricetype/dry", "type": "pricetype", "mediaType": "application/json"}, "name": "Цена продажи"}
        return organization, store, currency, price_type

    organizations = api.get_rows("organization", 1)
    if organizations:
        organization = organizations[0]
    else:
        organization = api.upsert_by_name("organization", {"name": f"{api.prefix} ООО Демо Организация"})

    stores = api.get_rows("store", 1)
    if stores:
        store = stores[0]
    else:
        store = api.upsert_by_name("store", {"name": f"{api.prefix} Основной склад"})

    currencies = api.get_rows("currency", 1)
    if not currencies:
        raise RuntimeError("В аккаунте не найдена валюта. Создайте базовые настройки МойСклад в интерфейсе.")

    price_types = api.request("GET", "/context/companysettings/pricetype")
    if not isinstance(price_types, list) or not price_types:
        raise RuntimeError("В аккаунте не найден тип цены. Проверьте настройки компании МойСклад.")
    return organization, store, currencies[0], price_types[0]


def create_employees(api: MoySkladApi) -> list[dict]:
    created = []
    for name in EMPLOYEES:
        parts = name.split()
        last_name = parts[0]
        first_name = parts[1] if len(parts) > 1 else "Продавец"
        middle_name = parts[2] if len(parts) > 2 else None
        body = {
            "lastName": f"{api.prefix} {last_name}",
            "firstName": first_name,
            "name": f"{api.prefix} {name}",
        }
        if middle_name:
            body["middleName"] = middle_name
        existing = None
        if api.apply:
            rows = api.get_rows("employee", 1000)
            for row in rows:
                if row.get("lastName") == body["lastName"] and row.get("firstName") == body["firstName"]:
                    existing = row
                    break
        if existing:
            print(f"SKIP employee: {body['name']}")
            created.append(existing)
        else:
            print(f"CREATE employee: {body['name']}")
            created.append(api.request("POST", "/entity/employee", body))
    return created


def create_counterparties(api: MoySkladApi) -> list[dict]:
    created = []
    for name in COUNTERPARTIES:
        created.append(api.upsert_by_name("counterparty", {"name": f"{api.prefix} {name}", "companyType": "legal"}))
    return created


def create_products(api: MoySkladApi, currency: dict, price_type: dict) -> list[dict]:
    created = []
    for idx, product in enumerate(PRODUCTS, 1):
        body = {
            "name": f"{api.prefix} {product.name}",
            "code": f"DB{idx:04d}",
            "description": f"Тестовый товар для дипломной демонстрации. Категория: {product.category}.",
            "salePrices": [
                {
                    "value": product.price * 100,
                    "currency": currency,
                    "priceType": price_type,
                }
            ],
        }
        created.append(api.upsert_by_name("product", body))
    return created


def create_customer_orders(api: MoySkladApi, organization: dict, counterparties: list[dict], employees: list[dict], products: list[dict]) -> None:
    random.seed(42)
    today = datetime.now()
    for idx in range(1, 91):
        agent = random.choice(counterparties)
        owner = random.choice(employees)
        order_products = random.sample(products, random.randint(1, 4))
        moment = today - timedelta(days=random.randint(0, 75), hours=random.randint(0, 8))
        positions = []
        for item in order_products:
            product_price = next((p.price for p in PRODUCTS if item.get("name", "").endswith(p.name)), random.randint(7000, 60000))
            positions.append(
                {
                    "quantity": random.randint(1, 5),
                    "price": product_price * 100,
                    "assortment": ref(item),
                }
            )
        body = {
            "name": f"{api.prefix}-ORDER-{idx:03d}",
            "moment": moment.strftime("%Y-%m-%d %H:%M:%S"),
            "organization": ref(organization),
            "agent": ref(agent),
            "owner": ref(owner),
            "positions": positions,
            "description": "Тестовый заказ для демонстрации аналитики продавцов.",
        }
        api.upsert_by_name("customerorder", body)


def write_preview_files(output_dir: Path, prefix: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "employees.csv").write_text("name\n" + "\n".join(f"{prefix} {x}" for x in EMPLOYEES) + "\n", encoding="utf-8")
    (output_dir / "counterparties.csv").write_text("name\n" + "\n".join(f"{prefix} {x}" for x in COUNTERPARTIES) + "\n", encoding="utf-8")
    products_lines = ["name,category,price"] + [f"{prefix} {p.name},{p.category},{p.price}" for p in PRODUCTS]
    (output_dir / "products.csv").write_text("\n".join(products_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed MoySklad demo data for Dashboard Battle.")
    parser.add_argument("--apply", action="store_true", help="Write data to MoySklad. Without this flag, only prints planned requests.")
    parser.add_argument("--prefix", default="DB-DEMO-2026", help="Prefix added to created entities.")
    parser.add_argument("--orders", action="store_true", help="Also create 90 customer orders. Products, employees and counterparties are always created.")
    parser.add_argument("--preview-dir", default="docs/moysklad_demo_seed", help="Directory for CSV preview files.")
    args = parser.parse_args()

    write_preview_files(Path(args.preview_dir), args.prefix)

    token = os.getenv("MOYSKLAD_TOKEN", "").strip()
    if args.apply and not token:
        print("MOYSKLAD_TOKEN is required for --apply.", file=sys.stderr)
        return 2
    if not args.apply:
        token = "dry-run-token"

    api = MoySkladApi(token=token, apply=args.apply, prefix=args.prefix)
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"CSV preview files written to: {args.preview_dir}")

    organization, store, currency, price_type = ensure_base_objects(api)
    print(f"Using organization: {organization.get('name')}")
    print(f"Using store: {store.get('name')}")
    print(f"Using currency: {currency.get('name')}")
    print(f"Using price type: {price_type.get('name')}")

    employees = create_employees(api)
    counterparties = create_counterparties(api)
    products = create_products(api, currency, price_type)
    if args.orders:
        create_customer_orders(api, organization, counterparties, employees, products)

    print("Done.")
    print("Created/planned: employees=18, counterparties=20, products=24, customer_orders=" + ("90" if args.orders else "0"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
