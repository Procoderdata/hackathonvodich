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
python exoplanet_server.py
```

### 4. Mở browser
```
http://localhost:5000
```

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
