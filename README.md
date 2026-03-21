# ATLAS Orrery (Real NASA Data)

Ứng dụng mô phỏng quỹ đạo exoplanet bằng Three.js + React (JSX), dùng dữ liệu thật từ NASA Exoplanet Archive.

## Kiến trúc

- Frontend: React + Vite tại `orrery_component/frontend/src`
- Backend API: Flask tại `server.py`
- Dữ liệu quỹ đạo: `data/orbital_elements.csv` + `data/orbital_elements.meta.json`

## Nguyên tắc dữ liệu

- Real-data only cho orbital catalog.
- Không còn demo fallback cho quỹ đạo.
- Propagation dùng Kepler solver với epoch thật (`pl_orbtper` hoặc `pl_tranmid`).

## Setup

```bash
pip install -r requirements.txt
cd orrery_component/frontend && npm install
```

## Refresh dữ liệu thật

```bash
python scripts/refresh_orbital_catalog.py
```

## Chạy ứng dụng

```bash
python server.py
```

Mở `http://localhost:5000`.

## API chính

- `GET /api/piz-zones`
- `GET /api/orbital-objects`
- `GET /api/orbital-meta`
- `GET /api/planet/<planet_id>`

## Nightly refresh (macOS)

```bash
python scripts/install_nightly_refresh_launchd.py --hour 2 --minute 15
```
