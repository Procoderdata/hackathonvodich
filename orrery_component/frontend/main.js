import { Streamlit } from "streamlit-component-lib";
import * as THREE from 'three';

// --- BIẾN TOÀN CỤC CHO THẾ GIỚI 3D ---
let scene, camera, renderer;
let starMesh, planetMeshes = [];

// --- HÀM KHỞI TẠO CẢNH 3D ---
function init() {
    // 1. Scene (Cảnh): Giống như một vũ trụ chứa tất cả vật thể
    scene = new THREE.Scene();

    // 2. Camera (Máy quay): Mắt của chúng ta để nhìn vào vũ trụ
    // PerspectiveCamera(góc nhìn, tỷ lệ khung hình, khoảng cách nhìn gần, khoảng cách nhìn xa)
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.setZ(30); // Đặt camera lùi ra xa để thấy được cảnh

    // 3. Renderer (Người vẽ): Dùng GPU để vẽ cảnh lên canvas
    renderer = new THREE.WebGLRenderer({
        canvas: document.querySelector('#bg'), // Lấy canvas từ file HTML
    });
    renderer.setSize(window.innerWidth, window.innerHeight);

    // 4. Lighting (Ánh sáng): Thêm một nguồn sáng để thấy được vật thể
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5); // Ánh sáng môi trường
    scene.add(ambientLight);

    // 5. Animation Loop (Vòng lặp hoạt ảnh): Bắt đầu vẽ liên tục
    animate();

    // 6. Xử lý khi cửa sổ thay đổi kích thước
    window.addEventListener('resize', onWindowResize, false);
}

// --- HÀM TẠO HỆ SAO DỰA TRÊN DỮ LIỆU TỪ PYTHON ---
function createSolarSystem(data) {
    // Xóa các vật thể cũ khỏi cảnh (quan trọng khi chọn hệ sao khác)
    if (starMesh) scene.remove(starMesh);
    planetMeshes.forEach(p => scene.remove(p));
    planetMeshes = [];

    // Tỷ lệ để phóng to khoảng cách cho dễ nhìn
    const DISTANCE_SCALE = 20;

    // 1. Tạo Ngôi sao
    if (data.star) {
        const star = data.star;
        const geometry = new THREE.SphereGeometry(star.radius * 5, 32, 32); // Phóng to gấp 5 lần
        const material = new THREE.MeshBasicMaterial({ color: star.color || 0xffff00 }); // Màu vàng nếu không có
        starMesh = new THREE.Mesh(geometry, material);
        scene.add(starMesh);
    }

    // 2. Tạo các Hành tinh
    if (data.planets) {
        data.planets.forEach(planet => {
            const geometry = new THREE.SphereGeometry(planet.radius * 5, 32, 32); // Phóng to gấp 5 lần
            const material = new THREE.MeshStandardMaterial({ color: planet.color || 0x0000ff }); // Màu xanh nếu không có
            const planetMesh = new THREE.Mesh(geometry, material);
            
            // Đặt vị trí hành tinh so với ngôi sao
            planetMesh.position.set(planet.distance * DISTANCE_SCALE, 0, 0);

            scene.add(planetMesh);
            planetMeshes.push(planetMesh);
        });
    }
}

// --- VÒNG LẶP HOẠT ẢNH ---
function animate() {
    requestAnimationFrame(animate); // Yêu cầu trình duyệt gọi lại hàm này ở khung hình tiếp theo
    
    // Ở đây chúng ta có thể thêm các chuyển động, ví dụ:
    // starMesh.rotation.y += 0.001;

    renderer.render(scene, camera); // Vẽ lại cảnh
}

// --- XỬ LÝ KHI CỬA SỔ THAY ĐỔI KÍCH THƯỚC ---
function onWindowResize() {
    const width = window.innerWidth;
    const height = window.innerHeight;

    camera.aspect = width / height;
    camera.updateProjectionMatrix();

    renderer.setSize(width, height);
    Streamlit.setFrameHeight(height); // Cập nhật chiều cao cho Streamlit
}

// --- CẦU NỐI VỚI STREAMLIT ---
function onRender(event) {
    const data = event.detail.args["data"];
    console.log("Dữ liệu nhận được để vẽ 3D:", data);
    
    // Dùng dữ liệu nhận được để tạo/cập nhật hệ sao
    createSolarSystem(data);
    
    // Cập nhật chiều cao của khung component
    onWindowResize(); 
}

// === KHỞI CHẠY ===
// 1. Khởi tạo thế giới 3D
init();
// 2. Lắng nghe dữ liệu từ Python
Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
// 3. Báo cho Streamlit rằng component đã sẵn sàng
Streamlit.setComponentReady();