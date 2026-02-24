# Современный мессенджер: MVP → Production

## 1) Цель и контекст

Продукт: кроссплатформенный мессенджер для общения с друзьями и близкими, рассчитанный на запуск на собственном VPS и дальнейший рост в production.

Ключевые сценарии пользователя:
- Регистрация/вход.
- Поиск и добавление друзей, управление контактами.
- Личные чаты 1:1 и групповые чаты.
- Приглашения участников, управление ролями и правами.
- Отправка текста, фото, файлов.
- Удаление чатов/сообщений по прозрачным правилам.
- Уведомления и real-time обновления.
- История сообщений и поиск.

Принципы продукта:
- Быстрый UI (реакция интерфейса <100–150 мс локально).
- Надёжная доставка сообщений (ack/retry, идемпотентность).
- Приватность и безопасность по умолчанию.
- Элегантный premium-minimal дизайн.

---

## 2) Варианты стека (2–3)

### Вариант A (рекомендуемый): Web-first + API + Real-time
- Frontend: **Next.js (App Router, TypeScript, Tailwind + shadcn/ui)**
- Backend API: **NestJS (TypeScript)**
- DB: **PostgreSQL**
- Real-time: **WebSocket (Socket.IO или ws) + Redis adapter**
- Cache/queue: **Redis + BullMQ**
- Media storage: **S3-compatible** (MinIO на VPS или внешнее S3)
- Reverse proxy: **Nginx/Caddy**
- Контейнеризация: **Docker Compose**

Плюсы:
- Один язык (TS) на фронт/бэк, высокая скорость команды.
- Отличная экосистема для модульной архитектуры.
- Хороший баланс между time-to-market и масштабируемостью.

Минусы:
- Потребуется дисциплина по производительности Node при росте нагрузки.

Сложность: **средняя**.
Поддержка: **средняя стоимость**.
Скорость разработки: **высокая**.

### Вариант B: Mobile-first
- Client: **Flutter** (iOS/Android/Web)
- Backend: **FastAPI (Python)**
- DB: **PostgreSQL**
- Real-time: **WebSocket**
- Queue: **Celery/RQ + Redis**

Плюсы:
- Быстрый выход на мобильные платформы.
- Хорошая производительность клиента.

Минусы:
- Web UX обычно слабее, чем у нативного web-стека.
- Два языка (Dart + Python) увеличивают сложность поддержки.

Сложность: **средняя/высокая**.
Поддержка: **средняя/высокая стоимость**.
Скорость разработки: **средняя**.

### Вариант C: Fullstack Django
- Backend/SSR: **Django + DRF + Channels**
- DB: **PostgreSQL**
- Real-time: **Django Channels + Redis**

Плюсы:
- «Батарейки в комплекте», зрелая админка из коробки.
- Хорошо для быстрых бизнес-панелей/админки.

Минусы:
- Для modern SPA-like UX часто нужен отдельный frontend.
- Channels может быть сложнее на высоких нагрузках.

Сложность: **средняя**.
Поддержка: **средняя**.
Скорость разработки: **средняя/высокая**.

**Выбор для VPS + терминал с телефона:** Вариант A (Next.js + NestJS + Postgres + Redis + S3/MinIO).

---

## 3) Must-have функционал

## 3.1 Аутентификация и аккаунты

### Требования
- Регистрация: email+пароль (опционально телефон).
- Подтверждение email/SMS (опционально на MVP, обязательно в v1).
- Вход, refresh токен, logout all sessions.
- Сброс пароля через одноразовый токен.
- Профиль: имя, username, avatar, bio, статус, privacy.

### Реализация
- Access token (JWT) 15 мин + Refresh token 30 дней.
- Refresh хранить **в httpOnly secure cookie** (для web), для mobile — secure storage.
- Refresh токены хранить в БД в виде hash + device metadata + revoke flag.
- Пароли: Argon2id.
- 2FA (TOTP) — v2.

Почему JWT+refresh:
- Хорошо масштабируется (stateless access).
- Гибко для web+mobile.

## 3.2 Система друзей

### Требования
- Поиск по username и (опционально) по телефону/email при разрешении пользователя.
- Friend request: create/accept/decline/cancel.
- Unfriend и block.
- Списки: friends/incoming/outgoing/blocked.
- Приватность: кто может писать, кто может добавлять, кто видит онлайн.

### Правила
- Нельзя отправлять запрос самому себе.
- При block автоматически рвётся friendship и отменяются pending requests.
- Для blocked пользователей сообщения запрещены.

## 3.3 Чаты

### Типы
- **Direct чат (1:1)**.
- **Group чат**.

### Роли
- owner, admin, member.

### Операции
- Создать чат (direct/group).
- Инвайт друзей в group.
- Leave group.
- Remove member (admin/owner).
- Transfer ownership.
- Pin chat, archive, mute.

### Удаление чата
- 1:1:
  - «Удалить у себя» = скрыть чат для конкретного пользователя.
  - «Очистить историю» = soft-delete messages visibility только у себя.
- Group:
  - Полное удаление чата — owner (или admin с policy) с soft-delete chat + members + messages.
  - При удалении сохранять audit след в admin_logs.

## 3.4 Сообщения

### Требования
- text, emoji, reactions.
- reply и forward.
- edit/delete с ограничением по времени (например 24 часа).
- realtime доставка.
- статусы: sent/delivered/read.
- полнотекстовый поиск.

### Реализация статусов
- sent: сервер сохранил сообщение.
- delivered: хотя бы одно устройство получателя получило event.
- read: получатель отправил read receipt до конкретного message_id.

## 3.5 Медиа

### Требования
- Фото: предпросмотр + thumbnails.
- Файлы: лимиты и whitelist MIME.
- Объектное хранение (S3/MinIO).

### Реализация
- Клиент запрашивает signed URL.
- Загружает файл напрямую в object storage.
- Сервер получает callback/finalize и создаёт attachment.
- Фоновая задача: генерация thumbnail + вирус-скан (ClamAV опционально).

CDN/кэширование:
- Для production — CDN перед bucket.
- Cache-control для превью/аватаров.

## 3.6 Админка

### Возможности
- Admin auth + RBAC (superadmin/moderator/support).
- Бан/разбан пользователей.
- Просмотр жалоб и модерация контента.
- Метрики: DAU/MAU, messages/day, error rate.
- Feature flags и лимиты загрузок.
- Лог действий администратора (кто/что/когда).

---

## 4) Дополнительный функционал по приоритетам

### MVP
- Регистрация/логин/refresh/logout.
- Профиль.
- Friends + requests + block.
- Direct + group chats.
- Text messages + attachments.
- Realtime + read receipts.
- Базовый поиск по сообщениям.
- Минимальная админка (бан/разбан, жалобы, логи).

### v1
- Reactions, reply, forward.
- Typing indicator + online/presence.
- Pin message/chat, archive, mute.
- Invite links в group.
- Темная/светлая тема.
- Антиспам и rate control.

### v2
- Голосовые сообщения.
- E2EE для direct чатов (сложная миграция ключей).
- Экспорт/бэкап данных пользователя.
- Расширенный поиск (по вложениям, OCR).
- ML-антиабьюз/модерация.

---

## 5) UX/UI (premium minimal)

## 5.1 Дизайн-система

### Сетка и отступы
- Основа: 8pt system.
- Контейнеры: 16/24/32 px в зависимости от брейкпоинта.
- Радиусы: 10–14 px (карточки), 999 px (pill).
- Тени: мягкие, low elevation.

### Типографика
- Шрифт: Inter / SF Pro / Manrope.
- H1: 32/40 semibold.
- H2: 24/32 semibold.
- Body: 15–16/24 regular.
- Caption: 12–13/18 medium.

### Цвета
- Нейтральная шкала: gray 50..950.
- Акцент: синий/фиолетовый один основной.
- Семантика: success/warning/error/info.
- Контраст WCAG AA минимум.

### Компоненты
- Buttons (primary/secondary/ghost/danger).
- Inputs (text/search/password + states).
- Modal/Drawer.
- Dropdown/menu/context menu.
- Toast/snackbar.
- Chat list item, message bubble, avatar stack, badge.

## 5.2 Ключевые экраны
1. Login/Register.
2. Chat list (search + pinned + unread badges).
3. Chat screen (messages, composer, attachments).
4. Create chat / invite friends.
5. Profile.
6. Friends & requests.
7. Settings (privacy, notifications, theme).
8. Admin panel (users/reports/logs/metrics).

## 5.3 UX-поведение
- Empty states: дружелюбные иллюстрации + явный CTA.
- Loading: skeletons вместо спиннеров где возможно.
- Error states: понятный текст + retry.
- destructive actions: confirm modal + undo (если безопасно).
- Микро-анимации 150–220ms, без «тяжёлых» эффектов.

---

## 6) Архитектура системы

## 6.1 Компоненты
- Client (Web/Mobile).
- API (REST).
- Realtime Gateway (WS).
- PostgreSQL.
- Redis (cache, pub/sub, rate-limit).
- Queue workers (BullMQ/Celery).
- Object storage (S3/MinIO).
- Observability stack (Prometheus + Grafana + Loki + Sentry).

## 6.2 Модульность бэкенда
- auth
- users
- privacy
- friends
- chats
- messages
- media
- notifications
- admin
- moderation

## 6.3 Потоки взаимодействий

### Базовый HTTP flow
1. Клиент → API `/auth/login`.
2. API → PostgreSQL проверка пользователя.
3. API → клиент: access+refresh.

### Отправка сообщения
1. Клиент `POST /chats/:id/messages`.
2. API пишет message в PostgreSQL.
3. API публикует событие в Redis pub/sub.
4. WS gateway отправляет `message:new` получателям.
5. Получатель отправляет `receipt:delivered` / `receipt:read`.

### WebSocket
- Auth при подключении через short-lived WS token.
- room-level subscription: `user:{id}`, `chat:{id}`.
- Reconnect с backoff (1s, 2s, 5s...).
- Delivery guarantees: client-generated UUID + server idempotency key.

## 6.4 Очереди и фоновые задачи
- Генерация thumbnails.
- Push/email notifications.
- Очистка истёкших токенов.
- Data retention jobs.

## 6.5 Rate limit и антиспам
- Redis sliding window.
- Лимиты на login, search, send message, upload.
- Device fingerprint + IP reputation (v1+).

## 6.6 Логи/мониторинг
- Structured JSON logs (trace_id, user_id).
- Metrics: p95 latency, WS connected clients, queue lag.
- Tracing: OpenTelemetry.

---

## 7) Реальная база данных (PostgreSQL)

Почему PostgreSQL:
- ACID, сильная консистентность, зрелые индексы и JSONB.
- Отлично подходит для транзакций дружбы/членства/ролей.
- Полнотекстовый поиск по сообщениям через tsvector/Gin.

## 7.1 ER-модель (ядро)

### `users`
- id (uuid, pk)
- email (citext unique, nullable если phone-only)
- phone (unique nullable)
- username (citext unique)
- password_hash
- display_name
- avatar_url
- bio
- status_text
- privacy_settings (jsonb)
- is_banned
- created_at, updated_at, deleted_at

### `sessions`
- id
- user_id (fk users)
- refresh_token_hash
- device_info
- ip
- expires_at
- revoked_at
- created_at

### `friend_requests`
- id
- from_user_id (fk users)
- to_user_id (fk users)
- status (pending/accepted/declined/cancelled)
- created_at, updated_at
- unique(from_user_id, to_user_id)

### `friends`
- user_id
- friend_id
- created_at
- pk(user_id, friend_id)
- check(user_id <> friend_id)

### `blocks`
- user_id
- blocked_user_id
- created_at
- pk(user_id, blocked_user_id)

### `chats`
- id
- type (direct/group)
- title
- avatar_url
- created_by
- last_message_id
- deleted_at
- created_at, updated_at

### `chat_members`
- chat_id
- user_id
- role (owner/admin/member)
- joined_at
- left_at
- mute_until
- is_pinned
- is_archived
- last_read_message_id
- pk(chat_id, user_id)

### `messages`
- id (bigserial or uuidv7)
- chat_id
- sender_id
- client_uid (идемпотентность)
- type (text/system/media)
- text
- reply_to_message_id
- forwarded_from_message_id
- edited_at
- deleted_at
- created_at
- unique(chat_id, sender_id, client_uid)

### `message_receipts`
- message_id
- user_id
- delivered_at
- read_at
- pk(message_id, user_id)

### `attachments`
- id
- message_id
- kind (image/file/video/audio)
- storage_key
- file_name
- mime_type
- size_bytes
- width, height, duration
- thumbnail_key
- created_at

### `reports`
- id
- reporter_user_id
- target_user_id nullable
- target_message_id nullable
- reason
- status (open/reviewed/closed)
- created_at, resolved_at

### `admin_logs`
- id
- admin_user_id
- action
- entity_type
- entity_id
- payload jsonb
- created_at

## 7.2 Индексы и ограничения
- users(email), users(username), users(phone) unique.
- messages(chat_id, created_at desc) для пагинации.
- messages using GIN(to_tsvector('simple', text)) для поиска.
- chat_members(user_id, is_archived, is_pinned).
- receipts(user_id, read_at).
- FK с ON DELETE RESTRICT для audit-сущностей.

## 7.3 Стратегия удаления
- **Soft delete** для users/chats/messages (legal/audit/recovery).
- **Hard delete** для технических/эфемерных данных (expired sessions, temp uploads).
- GDPR сценарий: анонимизация персональных данных по запросу.

## 7.4 Миграции и сиды
- Миграции: Prisma/TypeORM/Alembic (в зависимости от стека).
- Сиды: admin user, feature flags, demo rooms (только dev).
- Версионирование схемы строго через CI.

---

## 8) API спецификация (REST + WebSocket)

Формат ошибок:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid payload",
    "details": {}
  }
}
```

## 8.1 Auth

### POST `/auth/register`
Body:
- email|phone, password, username, display_name

200:
- user, access_token

Ошибки:
- 400 validation
- 409 email/username exists

### POST `/auth/login`
Body:
- email|phone|username, password

200:
- user, access_token (+ refresh cookie)

401:
- invalid credentials

### POST `/auth/refresh`
- Использует refresh cookie/token.

200:
- new access_token

401:
- refresh invalid/revoked

### POST `/auth/logout`
- revoke current session

204

## 8.2 Профиль

### GET `/me`
200 user profile

### PATCH `/me`
Body: display_name, bio, avatar_url, status_text, privacy_settings

200 updated profile

## 8.3 Users/Friends

### GET `/users/search?q=`
200 list users (с учетом privacy)

### POST `/friends/request`
Body: `to_user_id`

201 request

### POST `/friends/accept`
Body: `request_id`

200 friendship created

### POST `/friends/decline`
Body: `request_id`

200

### DELETE `/friends/:id`
204

### POST `/block/:id`
200

## 8.4 Chats

### POST `/chats`
Body:
- type: direct|group
- member_ids[]
- title (для group)

201 chat

### GET `/chats`
- пагинация по курсору, сортировка по last activity

### GET `/chats/:id`
200 chat detail + member role

### POST `/chats/:id/invite`
Body: user_ids[]

### POST `/chats/:id/leave`
204

### DELETE `/chats/:id`
- direct: hide for self
- group: delete/archive by permission

## 8.5 Messages

### GET `/chats/:id/messages?cursor=`
200:
- items[], next_cursor

### POST `/chats/:id/messages`
Body:
- client_uid
- text
- reply_to_message_id?
- attachments[]?

201 message

### PATCH `/messages/:id`
Body: text

200 edited message

### DELETE `/messages/:id`
204

## 8.6 Media

### POST `/media/upload-url`
Body: file_name, mime_type, size

200:
- signed_url, storage_key, expires_in

### POST `/media/finalize`
Body: storage_key, metadata

201 attachment

## 8.7 Admin

### GET `/admin/metrics`
### GET `/admin/reports`
### POST `/admin/users/:id/ban`
### POST `/admin/users/:id/unban`
### GET `/admin/logs`

RBAC + audit обязательны.

---

## 8.8 WebSocket события

Подключение:
- namespace `/ws`
- auth token обязателен

События сервер → клиент:
- `message:new`
- `message:edited`
- `message:deleted`
- `chat:created`
- `chat:updated`
- `chat:deleted`
- `member:joined`
- `member:left`
- `typing:start`
- `typing:stop`
- `receipt:delivered`
- `receipt:read`
- `presence:update`

События клиент → сервер:
- `typing:start|stop` {chat_id}
- `receipt:delivered` {chat_id, message_id}
- `receipt:read` {chat_id, message_id}
- `presence:update` {status}

Общие коды ошибок:
- 400 bad payload
- 401 unauthorized
- 403 forbidden
- 404 not found
- 409 conflict
- 413 payload too large
- 429 rate limited
- 500 internal

---

## 9) Развёртывание на VPS (через терминал на телефоне)

## 9.1 Минимальный production-контур
- 1 VPS (первый этап):
  - Nginx/Caddy
  - App (API + Web)
  - PostgreSQL
  - Redis
  - MinIO (опционально)
- Docker Compose + `.env`.

## 9.2 Практика
- Использовать `make`/`just` команды (`make up`, `make migrate`, `make logs`).
- Авто-бэкапы PostgreSQL (pg_dump + restic/rclone).
- TLS через Let’s Encrypt.
- Fail2ban + UFW.
- Логи в stdout + ротация.

## 9.3 Масштабирование
- Этап 1: всё на одном VPS.
- Этап 2: вынести DB на managed Postgres.
- Этап 3: вынести Redis и object storage, добавить read replica.
- Этап 4: горизонтальный scaling API/WS + Redis adapter.

---

## 10) План реализации (дорожная карта)

### Sprint 1–2 (MVP core)
- Auth, users, friends.
- Direct/group chats.
- Text messaging + realtime + receipts.
- Базовые вложения.
- Минимальная админка.

### Sprint 3–4
- Поиск, архив/мут/пины.
- Reactions/reply/forward.
- Presence/typing.
- Улучшения UX и performance.

### Sprint 5+
- Security hardening, anti-spam.
- Бэкапы, observability, chaos testing.
- Подготовка к multi-node.

---

## 11) Безопасность (минимум production)
- Argon2id, secure cookies, CSRF protection (для cookie flows).
- CORS policy + strict headers (CSP, HSTS, X-Frame-Options).
- Валидация входных данных на всех слоях.
- Rate limit + brute force protection.
- Подпись URL для медиа + expiring links.
- Шифрование at-rest (диски/бакеты) и in-transit (TLS).
- Секреты только через env/secret manager, никогда в git.

---

## 12) Что важно не забыть
- Идемпотентность отправки сообщений (client_uid).
- Пагинация курсором, не offset.
- Soft delete + audit trail.
- Набор health-checks (`/health`, `/ready`).
- Версионирование API (`/v1`).
- Нагрузочное тестирование WS и базы до публичного релиза.

