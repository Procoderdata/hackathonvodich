# 🚀 Setup Guide - NASA Exoplanet Visualization

## Quick Start

### 1. Cài đặt dependencies
```bash
pip install flask flask-cors pandas
```

### 2. Test data
```bash
python test_data.py
```

### 3. Chạy server
```bash
export DEEPSEEK_API_KEY="your_deepseek_key_here"   # thêm sau nếu cần
python server.py
```

### 4. Mở browser
```
http://localhost:5000
```

### DeepSeek Council (4 agent debate)
- Endpoint `/api/council/respond` hỗ trợ 4-key / 4-role:
  - `DEEPSEEK_API_KEY_NAVIGATOR`
  - `DEEPSEEK_API_KEY_ASTROBIOLOGIST`
  - `DEEPSEEK_API_KEY_CLIMATE`
  - `DEEPSEEK_API_KEY_ARCHIVIST`
- Hoặc dùng 1 biến gộp theo đúng thứ tự role:
  - `DEEPSEEK_API_KEYS="key_nav,key_astro,key_climate,key_archivist"`
- Nếu chỉ có 1 key thì dùng fallback:
  - `DEEPSEEK_API_KEY`
- Khi có key, endpoint `/api/council/respond` sẽ gọi DeepSeek để tạo tranh luận 4 vai trò:
  - `Navigator`
  - `Astrobiologist`
  - `Climate`
  - `Archivist`
- Nếu chưa có key hoặc provider lỗi, hệ thống tự fallback sang deterministic council để demo không bị gãy.

## Cách sử dụng

1. **BEGIN SESSION** - Khởi động hệ thống
2. **Click PIZ sphere** - Chọn vùng điều tra (quả cầu xanh)
3. **Select satellite** - Chọn vệ tinh từ panel phải
4. **Choose scan pattern** - Chọn kiểu quét
5. **Discover planets!** - Xem hành tinh được phát hiện

## Data Sources

- **TOI**: TESS Objects of Interest (7,770 candidates)
- **Kepler**: Confirmed planets (9,619 entries)
- **K2**: K2 mission candidates (4,104 entries)

## API Endpoints

- `GET /` - Main visualization
- `GET /api/piz-zones` - Priority Investigation Zones
- `GET /api/planets` - Confirmed exoplanets
- `GET /api/planet/<id>` - Planet details

## Features

✨ Real NASA data integration  
🪐 30+ confirmed exoplanets  
🛰️ Satellite scanning simulation  
📊 Detailed planet information  
🎯 Habitability classification  

Enjoy exploring! 🌌
