# Sellio Cart REST API Documentation

Base URL: `http://localhost:8081` (Docker Compose) or `http://localhost:8080` (direct run)

## Table of Contents
- [Business Rules](#business-rules)
- [Read Endpoints](#read-endpoints)
- [Write Endpoints](#write-endpoints)
- [Data Models](#data-models)
- [Error Responses](#error-responses)

---

## Business Rules

### One Active Cart Per User Per Company
**Ключове правило:** Один користувач може мати лише **один активний** (status=ACTIVE) кошик для кожної компанії.

**Що це означає:**
- При додаванні товару через `/cart/add-item`, система автоматично знайде існуючий активний кошик або створить новий
- Якщо у користувача вже є активний кошик для компанії, всі нові товари додаються саме в нього
- Щоб створити новий кошик, потрібно змінити статус поточного на `LOCKED`, `CHECKED_OUT` або `CANCELLED`

**Технічна реалізація:**
Правило гарантується через partial unique constraints в PostgreSQL:
```sql
UNIQUE (company_id, user_id) WHERE status = 1 AND user_id IS NOT NULL
UNIQUE (company_id, cookie) WHERE status = 1 AND cookie IS NOT NULL
```

### Cart Status Lifecycle
Допустимі переходи статусів:
- `ACTIVE (1)` → `LOCKED (2)` - блокування перед оформленням
- `ACTIVE (1)` → `CANCELLED (4)` - відміна кошика
- `LOCKED (2)` → `CHECKED_OUT (3)` - завершення замовлення

**Після переходу до `LOCKED`, `CHECKED_OUT` або `CANCELLED`** користувач може створити новий активний кошик.

---

## Read Endpoints

### Get Cart by ID
Отримати повний кошик за його ID.

**Request:**
```http
GET /api/v1/cart/{cart_id}
```

**Parameters:**
- `cart_id` (path, required) - ID кошика

**Response:** `200 OK`
```json
{
  "id": 1,
  "company_id": 100,
  "user_id": 42,
  "cookie": null,
  "status": 1,
  "created_at": "2024-01-15T10:30:00+00:00",
  "items": [
    {
      "product_id": 501,
      "name": "Product Name",
      "price": "99.99",
      "quantity": 2
    }
  ],
  "total_amount": "199.98"
}
```

**Errors:**
- `404 Not Found` - кошик не знайдено

---

### Get Carts by User
Отримати список кошиків користувача з фільтрацією.

**Request:**
```http
GET /api/v1/carts/by-user?user_id={user_id}&company_id={company_id}&status={status}&limit={limit}&offset={offset}
```

**Query Parameters:**
- `user_id` (required) - ID користувача
- `company_id` (optional) - ID компанії для фільтрації
- `status` (optional) - статус кошика (1=ACTIVE, 2=LOCKED, 3=CHECKED_OUT, 4=CANCELLED)
- `limit` (optional, default=50) - кількість записів
- `offset` (optional, default=0) - зміщення для пагінації

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "company_id": 100,
    "user_id": 42,
    "cookie": null,
    "status": 1,
    "created_at": "2024-01-15T10:30:00+00:00",
    "items": [...],
    "total_amount": "199.98"
  }
]
```

---

### Get Carts by IDs
Масова вибірка кошиків за списком ID (зберігає порядок).

**Request:**
```http
POST /api/v1/carts/by-ids
Content-Type: application/json

{
  "ids": [1, 5, 10]
}
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "company_id": 100,
    ...
  },
  {
    "id": 5,
    "company_id": 100,
    ...
  }
]
```

---

### Get Active Cart
Отримати активний кошик для компанії (для залогіненого користувача або за cookie).

**Request:**
```http
GET /api/v1/cart/active?company_id={company_id}&user_id={user_id}
```

**Query Parameters:**
- `company_id` (required) - ID компанії
- `user_id` (optional) - ID користувача (якщо залогінений)

**Headers:**
- Cookie `sellio_cart` автоматично встановлюється для анонімних користувачів

**Response:** `200 OK`
```json
{
  "id": 1,
  "company_id": 100,
  "user_id": 42,
  "cookie": "random_cookie_string",
  "status": 1,
  "created_at": "2024-01-15T10:30:00+00:00",
  "items": [],
  "total_amount": "0.00"
}
```

**Errors:**
- `404 Not Found` - активний кошик не знайдено

---

### Health Check
Перевірка доступності сервісу.

**Request:**
```http
GET /healthz
```

**Response:** `200 OK`
```json
{
  "status": "ok"
}
```

---

## Write Endpoints

### Upsert Cart
Створити новий активний кошик або отримати існуючий.

**Request:**
```http
POST /api/v1/cart/upsert
Content-Type: application/json

{
  "company_id": 100,
  "user_id": 42,
  "cookie": null
}
```

**Body Parameters:**
- `company_id` (required) - ID компанії
- `user_id` (optional) - ID користувача (null для анонімів)
- `cookie` (optional) - cookie для анонімного користувача

**Response:** `201 Created`
```json
{
  "id": 1,
  "company_id": 100,
  "user_id": 42,
  "cookie": null,
  "status": 1,
  "created_at": "2024-01-15T10:30:00+00:00",
  "items": [],
  "total_amount": "0.00"
}
```

---

### Add Item to Cart (Auto-create)
**Рекомендований спосіб:** Додати товар у кошик (створює кошик автоматично якщо потрібно).

**⚠️ Важливе правило:** Один користувач може мати лише один ACTIVE кошик на компанію. Якщо активний кошик вже існує, товар додається в нього. Якщо немає - створюється новий.

**Request:**
```http
POST /api/v1/cart/add-item
Content-Type: application/json

{
  "company_id": 100,
  "user_id": 42,
  "cookie": null,
  "product_id": 501,
  "name": "Product Name",
  "price": "99.99",
  "quantity": 2
}
```

**Body Parameters:**
- `company_id` (required) - ID компанії
- `user_id` (optional) - ID користувача (null для анонімів)
- `cookie` (optional) - cookie для анонімного користувача
- `product_id` (required) - ID товару
- `name` (required) - назва товару
- `price` (required) - ціна товару (string decimal)
- `quantity` (required) - кількість (> 0)

**Response:** `201 Created`
```json
{
  "id": 1,
  "company_id": 100,
  "user_id": 42,
  "cookie": null,
  "status": 1,
  "created_at": "2024-01-15T10:30:00+00:00",
  "items": [
    {
      "product_id": 501,
      "name": "Product Name",
      "price": "99.99",
      "quantity": 2
    }
  ],
  "total_amount": "199.98"
}
```

**Примітка:** Цей ендпоінт автоматично створює активний кошик, якщо його ще немає для даного користувача/cookie + company_id, і додає товар в одній транзакції.

---

### Add/Update Item in Existing Cart
Додати товар у існуючий кошик або оновити існуючий (потрібен cart_id).

**Request:**
```http
POST /api/v1/cart/{cart_id}/item
Content-Type: application/json

{
  "product_id": 501,
  "name": "Product Name",
  "price": "99.99",
  "quantity": 2
}
```

**Parameters:**
- `cart_id` (path, required) - ID кошика

**Body Parameters:**
- `product_id` (required) - ID товару
- `name` (required) - назва товару
- `price` (required) - ціна товару (string decimal)
- `quantity` (required) - кількість (> 0)

**Response:** `200 OK`
```json
{
  "id": 1,
  "company_id": 100,
  "user_id": 42,
  "cookie": null,
  "status": 1,
  "created_at": "2024-01-15T10:30:00+00:00",
  "items": [
    {
      "product_id": 501,
      "name": "Product Name",
      "price": "99.99",
      "quantity": 2
    }
  ],
  "total_amount": "199.98"
}
```

**Errors:**
- `404 Not Found` - кошик не знайдено

---

### Update Item Quantity
Змінити кількість товару в кошику.

**Request:**
```http
PUT /api/v1/cart/{cart_id}/item/{product_id}/quantity
Content-Type: application/json

{
  "quantity": 5
}
```

**Parameters:**
- `cart_id` (path, required) - ID кошика
- `product_id` (path, required) - ID товару

**Body Parameters:**
- `quantity` (required) - нова кількість (> 0)

**Response:** `200 OK`
```json
{
  "id": 1,
  "company_id": 100,
  "items": [
    {
      "product_id": 501,
      "name": "Product Name",
      "price": "99.99",
      "quantity": 5
    }
  ],
  "total_amount": "499.95"
}
```

**Errors:**
- `404 Not Found` - кошик або товар не знайдено

---

### Remove Item from Cart
Видалити товар з кошика.

**Request:**
```http
DELETE /api/v1/cart/{cart_id}/item/{product_id}
```

**Parameters:**
- `cart_id` (path, required) - ID кошика
- `product_id` (path, required) - ID товару

**Response:** `200 OK`
```json
{
  "id": 1,
  "company_id": 100,
  "items": [],
  "total_amount": "0.00"
}
```

**Errors:**
- `404 Not Found` - кошик не знайдено

---

### Change Cart Status
Змінити статус кошика (перехід між станами).

**Request:**
```http
PUT /api/v1/cart/{cart_id}/status
Content-Type: application/json

{
  "status": 2
}
```

**Parameters:**
- `cart_id` (path, required) - ID кошика

**Body Parameters:**
- `status` (required) - новий статус кошика

**Status Values:**
- `1` - ACTIVE (активний)
- `2` - LOCKED (заблокований)
- `3` - CHECKED_OUT (оформлений)
- `4` - CANCELLED (скасований)

**Allowed Transitions:**
- ACTIVE → LOCKED
- ACTIVE → CANCELLED
- LOCKED → CHECKED_OUT

**Response:** `200 OK`
```json
{
  "id": 1,
  "company_id": 100,
  "status": 2,
  "items": [...],
  "total_amount": "199.98"
}
```

**Errors:**
- `400 Bad Request` - недопустимий перехід статусу
- `404 Not Found` - кошик не знайдено

---

## Data Models

### CartOut
```typescript
{
  id: number;
  company_id: number;
  user_id: number | null;
  cookie: string | null;
  status: number;  // 1=ACTIVE, 2=LOCKED, 3=CHECKED_OUT, 4=CANCELLED
  created_at: string;  // ISO8601
  items: CartItemOut[];
  total_amount: string;  // decimal as string
}
```

### CartItemOut
```typescript
{
  product_id: number;
  name: string;
  price: string;  // decimal as string
  quantity: number;
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid status transition or cart not found"
}
```

### 404 Not Found
```json
{
  "detail": "Cart not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "quantity"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Cookie Management

Для анонімних користувачів REST API автоматично встановлює cookie `sellio_cart`:
- **Name:** `sellio_cart`
- **HttpOnly:** true
- **Secure:** true
- **SameSite:** Lax
- **Max-Age:** 30 days

---

## Examples

### Simple Flow: Add Item (Recommended)

**Додати перший товар (кошик створюється автоматично):**
```bash
curl -X POST http://localhost:8080/api/v1/cart/add-item \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 100,
    "user_id": 42,
    "cookie": null,
    "product_id": 501,
    "name": "Laptop",
    "price": "999.99",
    "quantity": 1
  }'
```

**Відповідь містить cart_id=1:**
```json
{
  "id": 1,
  "company_id": 100,
  "user_id": 42,
  "status": 1,
  "items": [{"product_id": 501, "name": "Laptop", "price": "999.99", "quantity": 1}],
  "total_amount": "999.99"
}
```

**Додати ще один товар (іде в ТОЙ САМИЙ кошик):**
```bash
curl -X POST http://localhost:8080/api/v1/cart/add-item \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 100,
    "user_id": 42,
    "cookie": null,
    "product_id": 502,
    "name": "Mouse",
    "price": "29.99",
    "quantity": 2
  }'
```

**Відповідь - той самий cart_id=1 з двома товарами:**
```json
{
  "id": 1,
  "company_id": 100,
  "user_id": 42,
  "status": 1,
  "items": [
    {"product_id": 501, "name": "Laptop", "price": "999.99", "quantity": 1},
    {"product_id": 502, "name": "Mouse", "price": "29.99", "quantity": 2}
  ],
  "total_amount": "1059.97"
}
```

**Примітка:** Обидва запити повертають той самий `cart_id=1`, тому що користувач може мати лише один активний кошик на компанію.

**Оновити кількість:**
```bash
curl -X PUT http://localhost:8080/api/v1/cart/1/item/501/quantity \
  -H "Content-Type: application/json" \
  -d '{"quantity": 2}'
```

**Заблокувати кошик перед checkout:**
```bash
curl -X PUT http://localhost:8080/api/v1/cart/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": 2}'
```

---

### Alternative Flow: Create Cart Then Add Items

**Step 1: Create Cart**
```bash
curl -X POST http://localhost:8080/api/v1/cart/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 100,
    "user_id": null,
    "cookie": "random_anonymous_token"
  }'
```

**Step 2: Add Item**
```bash
curl -X POST http://localhost:8080/api/v1/cart/1/item \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 501,
    "name": "Laptop",
    "price": "999.99",
    "quantity": 1
  }'
```

---

## Interactive Documentation

Swagger UI доступний за адресою:
```
http://localhost:8081/docs  (Docker Compose)
http://localhost:8080/docs  (direct run)
```

ReDoc доступний за адресою:
```
http://localhost:8081/redoc  (Docker Compose)
http://localhost:8080/redoc  (direct run)
```

**Note:** В прикладах curl використовується порт `8080`, але для Docker Compose замініть на `8081`.

