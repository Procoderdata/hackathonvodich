# Quickstart

## 1) Cài dependencies

```bash
pip install -r requirements.txt
cd orrery_component/frontend && npm install
```

## 2) Refresh catalog orbital data thật

```bash
python scripts/refresh_orbital_catalog.py
```

Kết quả mong đợi:
- `data/orbital_elements.csv`
- `data/orbital_elements.meta.json`

## 3) Build frontend React (JSX)

```bash
cd orrery_component/frontend
npm run build
```

## 4) Chạy backend

```bash
python server.py
```

Mở `http://localhost:5000`.

## Keyboard shortcuts

- `T`: track object đang chọn
- `U`: unlock track
- `Q`: giảm simulation speed
- `E`: tăng simulation speed

## Troubleshooting

### API `/api/orbital-objects` trả 500

- Thiếu hoặc lỗi `data/orbital_elements.csv`
- Chạy lại: `python scripts/refresh_orbital_catalog.py`

### Frontend không lên

- Chưa build React:
  - `cd orrery_component/frontend && npm run build`

### Lưu ý

- Hệ thống không dùng demo fallback cho orbital catalog.
- Nếu dữ liệu thật chưa sẵn sàng, UI sẽ báo `OFFLINE`.
