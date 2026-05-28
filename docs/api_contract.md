# API Contract

> Tài liệu này là nguồn sự thật duy nhất (single source of truth) cho toàn bộ team.  
> Mọi thay đổi endpoint/schema **phải** cập nhật ở đây trước khi code.

---

## Base URLs

| Service      | Local (direct) | Via Gateway       |
|--------------|----------------|-------------------|
| Gateway      | `localhost:8000` | —               |
| Auth         | `localhost:8001` | `localhost:8000/auth/...` |
| Product      | `localhost:8002` | `localhost:8000/products/...` |
| Order        | `localhost:8003` | `localhost:8000/orders/...` |
| Notification | `localhost:8004` | `localhost:8000/notifications/...` |

---

## Auth headers

Tất cả route (trừ `/auth/register`, `/auth/login`, `/health`) yêu cầu:

```
Authorization: Bearer <jwt_token>
```

---

## Auth Service `/auth`

### POST `/auth/register`
**Public — không cần token**

Request:
```json
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```
Response `201`:
```json
{
  "user_id": "uuid",
  "username": "string",
  "email": "string",
  "created_at": "ISO8601"
}
```

---

### POST `/auth/login`
**Public — không cần token**

Request:
```json
{
  "email": "string",
  "password": "string"
}
```
Response `200`:
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### GET `/auth/me`
**Requires token**

Response `200`:
```json
{
  "user_id": "uuid",
  "username": "string",
  "email": "string"
}
```

---

## Product Service `/products`

### GET `/products`
**Public**  
Query params: `?category=string&limit=int&offset=int`

Response `200`:
```json
{
  "total": 100,
  "products": [
    {
      "product_id": "uuid",
      "name": "string",
      "category": "string",
      "price": 0.0,
      "stock": 0
    }
  ]
}
```

---

### GET `/products/{product_id}`
**Public**

Response `200`:
```json
{
  "product_id": "uuid",
  "name": "string",
  "description": "string",
  "category": "string",
  "price": 0.0,
  "stock": 0,
  "created_at": "ISO8601"
}
```

---

### POST `/products`
**Requires token**

Request:
```json
{
  "name": "string",
  "description": "string",
  "category": "string",
  "price": 0.0,
  "stock": 0
}
```
Response `201`: product object (same as GET above)

---

### PUT `/products/{product_id}`
**Requires token**

Request: partial product fields  
Response `200`: updated product object

---

### DELETE `/products/{product_id}`
**Requires token**

Response `204`: no content

---

## Order Service `/orders`

### POST `/orders`
**Requires token**

Request:
```json
{
  "user_id": "uuid",
  "items": [
    {
      "product_id": "uuid",
      "quantity": 1,
      "unit_price": 0.0
    }
  ]
}
```
Response `201`:
```json
{
  "order_id": "uuid",
  "user_id": "uuid",
  "status": "pending",
  "total_amount": 0.0,
  "items": [...],
  "created_at": "ISO8601"
}
```

---

### GET `/orders`
**Requires token**  
Query: `?user_id=uuid&status=string&limit=int`

Response `200`:
```json
{
  "total": 0,
  "orders": [{ "order_id": "...", "status": "...", "total_amount": 0.0, "created_at": "..." }]
}
```

---

### GET `/orders/{order_id}`
**Requires token**

Response `200`: full order object

---

### PUT `/orders/{order_id}/status`
**Requires token**

Request:
```json
{ "status": "pending | confirmed | shipped | delivered | cancelled" }
```
Response `200`: updated order object

---

## Notification Service `/notifications`

> Called internally by Order Service — typically not exposed to end users.

### POST `/notifications/send`

Request:
```json
{
  "user_id": "uuid",
  "email": "string",
  "type": "order_confirmed | order_shipped | order_delivered",
  "order_id": "uuid",
  "message": "string"
}
```
Response `200`:
```json
{ "sent": true, "notification_id": "uuid" }
```

---

## Error format (all services)

```json
{
  "detail": "Human-readable error message"
}
```

HTTP status codes used: `200 201 204 400 401 403 404 422 429 503 504`

---

## orders.json schema
> Used by Order Service (write) and Databricks (read)

```json
{
  "order_id": "uuid",
  "user_id": "uuid",
  "status": "string",
  "total_amount": 0.0,
  "items": [
    {
      "product_id": "uuid",
      "quantity": 1,
      "unit_price": 0.0
    }
  ],
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```
