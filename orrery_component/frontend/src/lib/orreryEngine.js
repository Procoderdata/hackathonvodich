import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

const SIM_EPOCH_MS = Date.UTC(2025, 2, 21, 17, 49, 1);
const SPEED_STEPS = [-32, -8, -1, 0, 1, 8, 32];

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function formatSpeed(value) {
  if (value === 0) return 'PAUSED';
  const abs = Math.abs(value);
  const unit = abs === 1 ? 'day/second' : 'days/second';
  const direction = value < 0 ? 'REVERSE ' : '';
  return `${direction}${abs} ${unit}`;
}

function normalizeAngleRadians(angle) {
  return ((angle + Math.PI) % (Math.PI * 2)) - Math.PI;
}

function solveKeplerEquation(meanAnomaly, eccentricity) {
  const e = clamp(Number(eccentricity || 0), 0, 0.98);
  let E = e < 0.8 ? normalizeAngleRadians(meanAnomaly) : Math.PI;

  for (let i = 0; i < 20; i += 1) {
    const f = E - (e * Math.sin(E)) - meanAnomaly;
    const fp = 1 - (e * Math.cos(E));
    if (Math.abs(fp) < 1e-9) break;
    const delta = f / fp;
    E -= delta;
    if (Math.abs(delta) < 1e-10) break;
  }

  return E;
}

function applyOrbitalTransforms(vec, orbit) {
  const rotated = vec.clone();
  rotated.applyAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(Number(orbit.arg_peri_deg || 0)));
  rotated.applyAxisAngle(new THREE.Vector3(1, 0, 0), THREE.MathUtils.degToRad(Number(orbit.inclination_deg || 0)));
  rotated.applyAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(Number(orbit.node_deg || 0)));
  return rotated;
}

function safeJsonFetch(url) {
  return fetch(url).then((response) => {
    if (!response.ok) {
      throw new Error(`Request failed for ${url}: ${response.status}`);
    }
    return response.json();
  });
}

export class OrreryEngine {
  constructor({ mountElement, callbacks = {} }) {
    if (!mountElement) {
      throw new Error('mountElement is required for OrreryEngine');
    }

    this.mountElement = mountElement;
    this.callbacks = callbacks;

    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;

    this.centralStar = null;
    this.stars = null;
    this.nebula = null;

    this.satellites = [];
    this.pizSpheres = [];
    this.orbitBodies = [];
    this.scanBeams = [];

    this.selectedPiz = null;
    this.selectedSatelliteIndex = 0;
    this.selectedOrbitBody = null;

    this.isTrackingMode = false;
    this.trackedOrbitBody = null;

    this.discoveries = [];

    this.simElapsedDays = 0;
    this.timeScale = 1;
    this.lastFrameMs = null;
    this.hudTick = 0;

    this.dataMode = 'LIVE';
    this.dataSource = 'NASA Exoplanet Archive';
    this.solverName = 'kepler_newton';
    this.epochReferenceJd = (SIM_EPOCH_MS / 86400000.0) + 2440587.5;

    this.filterState = {
      showConfirmed: true,
      showHabitable: true,
      radiusMin: 0.3,
      radiusMax: 20.0,
      periodMin: 1,
      periodMax: 1200,
    };

    this.pointer = new THREE.Vector2();
    this.raycaster = new THREE.Raycaster();

    this.rafId = null;

    this.onWindowResize = this.onWindowResize.bind(this);
    this.onPointerDown = this.onPointerDown.bind(this);
    this.animate = this.animate.bind(this);
  }

  emitState(partial) {
    if (typeof this.callbacks.onStateChange === 'function') {
      this.callbacks.onStateChange(partial);
    }
  }

  log(message, type = 'info') {
    if (typeof this.callbacks.onLog === 'function') {
      this.callbacks.onLog({ message, type });
    }
  }

  notifyDiscovery(item) {
    if (typeof this.callbacks.onDiscovery === 'function') {
      this.callbacks.onDiscovery(item);
    }
  }

  notifyPlanetOpen(item) {
    if (typeof this.callbacks.onOpenPlanet === 'function') {
      this.callbacks.onOpenPlanet(item);
    }
  }

  notifyPizSelected(item) {
    if (typeof this.callbacks.onPizSelected === 'function') {
      this.callbacks.onPizSelected(item);
    }
  }

  notifyPizCatalog(items) {
    if (typeof this.callbacks.onPizCatalog === 'function') {
      this.callbacks.onPizCatalog(items);
    }
  }

  initializeScene() {
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x02060f, 0.0022);

    const width = this.mountElement.clientWidth || window.innerWidth;
    const height = this.mountElement.clientHeight || window.innerHeight;

    this.camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1400);
    this.camera.position.set(0, 35, 75);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.renderer.setClearColor(0x000000, 1);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.14;
    this.mountElement.innerHTML = '';
    this.mountElement.appendChild(this.renderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.maxDistance = 400;

    window.addEventListener('resize', this.onWindowResize);
    this.renderer.domElement.addEventListener('pointerdown', this.onPointerDown);
  }

  createStarfield() {
    const starsGeometry = new THREE.BufferGeometry();
    const starsCount = 10000;
    const positions = new Float32Array(starsCount * 3);
    const colors = new Float32Array(starsCount * 3);

    for (let i = 0; i < starsCount; i += 1) {
      const i3 = i * 3;
      const radius = 140 + Math.random() * 520;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos((Math.random() * 2) - 1);

      positions[i3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i3 + 2] = radius * Math.cos(phi);

      colors[i3] = 0.78 + Math.random() * 0.22;
      colors[i3 + 1] = 0.8 + Math.random() * 0.2;
      colors[i3 + 2] = 0.9 + Math.random() * 0.1;
    }

    starsGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    starsGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const starsMaterial = new THREE.PointsMaterial({
      size: 1,
      vertexColors: true,
      sizeAttenuation: true,
    });

    this.stars = new THREE.Points(starsGeometry, starsMaterial);
    this.scene.add(this.stars);
  }

  createCentralStar() {
    const starGeometry = new THREE.SphereGeometry(2.6, 32, 32);
    const starMaterial = new THREE.MeshBasicMaterial({ color: 0xffe48b });
    this.centralStar = new THREE.Mesh(starGeometry, starMaterial);
    this.scene.add(this.centralStar);

    const glowGeometry = new THREE.SphereGeometry(4.8, 24, 24);
    const glowMaterial = new THREE.MeshBasicMaterial({
      color: 0xffbb55,
      transparent: true,
      opacity: 0.13,
      side: THREE.BackSide,
    });
    const glow = new THREE.Mesh(glowGeometry, glowMaterial);
    this.centralStar.add(glow);

    const ambient = new THREE.AmbientLight(0x335070, 0.35);
    this.scene.add(ambient);

    const point = new THREE.PointLight(0xffd98a, 1.35, 900, 1.25);
    point.position.set(0, 0, 0);
    this.scene.add(point);
  }

  createSatelliteFleet() {
    const satelliteData = [
      { name: 'NEOSSat-1', position: [0, 0, 0], status: 'IDLE' },
      { name: 'NEOSSat-2', position: [10, 5, 5], status: 'IDLE' },
      { name: 'NEOSSat-3', position: [-10, -5, 5], status: 'IDLE' },
    ];

    satelliteData.forEach((data, index) => {
      const satGeometry = new THREE.BoxGeometry(0.5, 0.5, 1);
      const satMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff });
      const satellite = new THREE.Mesh(satGeometry, satMaterial);
      satellite.position.set(...data.position);
      satellite.userData = { ...data, index };

      const antennaGeometry = new THREE.CylinderGeometry(0.05, 0.05, 1, 8);
      const antennaMaterial = new THREE.MeshBasicMaterial({ color: 0xcccccc });
      const antenna = new THREE.Mesh(antennaGeometry, antennaMaterial);
      antenna.rotation.x = Math.PI / 2;
      antenna.position.z = 0.5;
      satellite.add(antenna);

      this.scene.add(satellite);
      this.satellites.push(satellite);
    });
  }

  createNebula() {
    const nebulaGeometry = new THREE.BufferGeometry();
    const particleCount = 500;
    const positions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i += 1) {
      const i3 = i * 3;
      positions[i3] = (Math.random() - 0.5) * 220;
      positions[i3 + 1] = (Math.random() - 0.5) * 220;
      positions[i3 + 2] = (Math.random() - 0.5) * 220;
    }

    nebulaGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const nebulaMaterial = new THREE.PointsMaterial({
      color: 0x4466ff,
      size: 10,
      transparent: true,
      opacity: 0.05,
      blending: THREE.AdditiveBlending,
    });

    this.nebula = new THREE.Points(nebulaGeometry, nebulaMaterial);
    this.scene.add(this.nebula);
  }

  createOrbitBodyMesh(data) {
    const size = Math.max(0.22, Math.min(3.0, Number(data.size || 0.8)));
    const color = data.habitable ? 0x44ff88 : 0xff9b55;
    const geometry = new THREE.SphereGeometry(size, 18, 18);
    const material = new THREE.MeshStandardMaterial({
      color,
      emissive: data.habitable ? 0x1e5f44 : 0x5a2a12,
      emissiveIntensity: 0.45,
      roughness: 0.8,
      metalness: 0.08,
      transparent: true,
      opacity: 0.18,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.userData = { ...data, discovered: false, kind: 'orbit-body' };
    return mesh;
  }

  createOrbitLine(orbit, habitable) {
    const a = Math.max(4, Number(orbit.semi_major || 18));
    const e = clamp(Number(orbit.eccentricity || 0), 0, 0.85);
    const segments = 180;
    const positions = new Float32Array((segments + 1) * 3);
    const colors = new Float32Array((segments + 1) * 3);

    const nearColor = new THREE.Color(habitable ? 0x7fffd4 : 0xf7c174);
    const farColor = new THREE.Color(habitable ? 0x2f7d66 : 0x4063a8);

    for (let i = 0; i <= segments; i += 1) {
      const t = i / segments;
      const angle = t * Math.PI * 2;
      const radius = (a * (1 - (e * e))) / (1 + (e * Math.cos(angle)));
      const point = applyOrbitalTransforms(new THREE.Vector3(radius * Math.cos(angle), 0, radius * Math.sin(angle)), orbit);

      const idx = i * 3;
      positions[idx] = point.x;
      positions[idx + 1] = point.y;
      positions[idx + 2] = point.z;

      const depthMix = clamp((point.z / (a * 1.25) + 1) * 0.5, 0, 1);
      const shade = nearColor.clone().lerp(farColor, clamp((t * 0.42) + ((1 - depthMix) * 0.58), 0, 1));
      colors[idx] = shade.r;
      colors[idx + 1] = shade.g;
      colors[idx + 2] = shade.b;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const coreMaterial = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.31,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const glowMaterial = new THREE.LineBasicMaterial({
      color: habitable ? 0x55ffd9 : 0xffcf8a,
      transparent: true,
      opacity: 0.11,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const coreLine = new THREE.Line(geometry, coreMaterial);
    const glowLine = new THREE.Line(geometry.clone(), glowMaterial);
    glowLine.scale.multiplyScalar(1.003);

    const group = new THREE.Group();
    group.add(glowLine);
    group.add(coreLine);
    group.userData = { coreLine, glowLine };
    return group;
  }

  async loadPizZones() {
    const pizData = await safeJsonFetch('/api/piz-zones');
    this.emitState({ priorityCount: pizData.length });
    this.notifyPizCatalog(pizData);
    this.log(`Loaded ${pizData.length} Priority Investigation Zones from NASA data`, 'success');

    pizData.forEach((data) => {
      const geometry = new THREE.SphereGeometry(3.0, 24, 24);
      const material = new THREE.MeshBasicMaterial({
        color: 0x00aaff,
        transparent: true,
        opacity: 0.42,
      });

      const sphere = new THREE.Mesh(geometry, material);
      sphere.position.set(...data.position);
      sphere.userData = { ...data, kind: 'piz' };

      const glowGeometry = new THREE.SphereGeometry(3.8, 24, 24);
      const glowMaterial = new THREE.MeshBasicMaterial({
        color: 0x0088ff,
        transparent: true,
        opacity: 0.12,
        side: THREE.BackSide,
      });
      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      glow.position.set(...data.position);
      glow.scale.multiplyScalar(1.35);

      this.scene.add(sphere);
      this.scene.add(glow);
      this.pizSpheres.push({ sphere, glow, data });
    });
  }

  async loadOrbitalCatalog() {
    const payload = await safeJsonFetch('/api/orbital-objects');
    const catalog = payload.objects || [];
    if (!catalog.length) {
      throw new Error('Orbital catalog is empty');
    }

    this.dataMode = 'LIVE';
    this.dataSource = payload.meta?.source || this.dataSource;
    this.solverName = payload.meta?.solver || this.solverName;
    this.epochReferenceJd = Number(payload.meta?.epoch_reference_jd || this.epochReferenceJd);

    this.emitState({
      dataStatus: this.dataMode,
      dataSource: this.dataSource,
      solverName: this.solverName,
      refreshedAtUtc: payload.meta?.refreshed_at_utc || 'unknown',
      catalogTotal: catalog.length,
      catalogVisible: catalog.length,
      habitableCount: payload.meta?.habitable_candidates || 0,
    });

    this.log(
      `Loaded ${catalog.length} orbital objects from NASA archive (${this.solverName}, refresh ${payload.meta?.refreshed_at_utc || 'unknown'})`,
      'success'
    );

    this.orbitBodies.forEach((item) => {
      this.scene.remove(item.mesh);
      this.scene.remove(item.orbitLine);
    });
    this.orbitBodies = [];

    catalog.forEach((data) => {
      const mesh = this.createOrbitBodyMesh(data);
      const orbitLine = this.createOrbitLine(data.orbit || {}, data.habitable);
      this.scene.add(mesh);
      this.scene.add(orbitLine);
      this.orbitBodies.push({
        mesh,
        orbitLine,
        data: { ...data, discovered: false },
      });
    });
  }

  updateOrbitPositions() {
    const currentJd = (SIM_EPOCH_MS / 86400000.0) + 2440587.5 + this.simElapsedDays;

    this.orbitBodies.forEach((item) => {
      const orbit = item.data.orbit || {};
      const period = Math.max(0.1, Number(orbit.period_days || item.data.period || 20));
      const a = Math.max(0.1, Number(orbit.semi_major || 18));
      const e = clamp(Number(orbit.eccentricity || 0), 0, 0.98);
      const tPeri = Number(orbit.t_peri_jd || this.epochReferenceJd || currentJd);

      const meanMotion = (Math.PI * 2) / period;
      const meanAnomaly = normalizeAngleRadians(meanMotion * (currentJd - tPeri));
      const eccAnomaly = solveKeplerEquation(meanAnomaly, e);
      const trueAnomaly = 2 * Math.atan2(
        Math.sqrt(1 + e) * Math.sin(eccAnomaly / 2),
        Math.sqrt(Math.max(1e-9, 1 - e)) * Math.cos(eccAnomaly / 2)
      );
      const radius = a * (1 - (e * Math.cos(eccAnomaly)));

      const orbitPlanePos = new THREE.Vector3(radius * Math.cos(trueAnomaly), 0, radius * Math.sin(trueAnomaly));
      item.mesh.position.copy(applyOrbitalTransforms(orbitPlanePos, orbit));
    });
  }

  updateDepthCues() {
    this.orbitBodies.forEach((item) => {
      if (!item.mesh.visible) return;
      const distance = this.camera.position.distanceTo(item.mesh.position);
      const proximity = clamp(1 - (distance / 420), 0, 1);
      const meshOpacity = item.data.discovered
        ? clamp(0.75 + (proximity * 0.2), 0.75, 1)
        : clamp(0.12 + (proximity * 0.24), 0.1, 0.4);
      const orbitOpacity = clamp(0.08 + (proximity * 0.22), 0.08, 0.34);
      const orbitCore = item.orbitLine.userData?.coreLine || item.orbitLine;
      const orbitGlow = item.orbitLine.userData?.glowLine || null;

      item.mesh.material.opacity = meshOpacity;
      orbitCore.material.opacity = orbitOpacity;
      if (orbitGlow) {
        orbitGlow.material.opacity = clamp(orbitOpacity * 0.48, 0.04, 0.2);
      }
    });
  }

  applyOrbitFilters() {
    let visibleCount = 0;

    this.orbitBodies.forEach((item) => {
      const data = item.data;
      const radiusEarth = Number(data.radius || 0.3);
      const period = Number(data.period || data.orbit?.period_days || 1);
      const categoryVisible = (data.habitable && this.filterState.showHabitable)
        || (!data.habitable && this.filterState.showConfirmed);
      const sizeVisible = radiusEarth >= this.filterState.radiusMin && radiusEarth <= this.filterState.radiusMax;
      const periodVisible = period >= this.filterState.periodMin && period <= this.filterState.periodMax;
      const visible = categoryVisible && sizeVisible && periodVisible;

      item.mesh.visible = visible;
      item.orbitLine.visible = visible;

      if (visible) {
        visibleCount += 1;
      }
    });

    this.emitState({ catalogVisible: visibleCount, catalogTotal: this.orbitBodies.length });
  }

  setFilters(nextFilters) {
    this.filterState = { ...this.filterState, ...nextFilters };
    this.applyOrbitFilters();
  }

  setTimeScale(nextValue, log = false) {
    this.timeScale = Number(nextValue);
    this.emitState({ simSpeedText: formatSpeed(this.timeScale), timeScale: this.timeScale });
    if (log) this.log(`Simulation speed set to ${formatSpeed(this.timeScale)}.`, 'command');
  }

  stepTimeScale(direction) {
    let idx = SPEED_STEPS.indexOf(this.timeScale);
    if (idx < 0) {
      idx = SPEED_STEPS.findIndex((v) => v > this.timeScale);
      if (idx < 0) idx = SPEED_STEPS.length - 1;
    }
    const nextIdx = clamp(idx + direction, 0, SPEED_STEPS.length - 1);
    this.setTimeScale(SPEED_STEPS[nextIdx], true);
  }

  resetTime() {
    this.simElapsedDays = 0;
    this.updateOrbitPositions();
    this.updateHud();
    this.log('Simulation timeline reset to baseline epoch.', 'info');
  }

  selectSatellite(index) {
    this.selectedSatelliteIndex = clamp(Number(index), 0, this.satellites.length - 1);
    const sat = this.satellites[this.selectedSatelliteIndex];
    if (sat) {
      this.log(`Selected ${sat.userData.name} for deployment.`, 'command');
    }
  }

  setTrackingMode(enabled) {
    const nextEnabled = Boolean(enabled);
    if (nextEnabled && !this.selectedOrbitBody) {
      this.log('No object selected. Click an orbiting body before enabling track mode.', 'warning');
      return;
    }

    this.isTrackingMode = nextEnabled;
    if (nextEnabled) {
      this.trackedOrbitBody = this.selectedOrbitBody;
      this.log(`Track mode enabled for ${this.trackedOrbitBody.data.id}.`, 'success');
      this.emitState({ trackingTarget: this.trackedOrbitBody.data.id });
      return;
    }

    this.trackedOrbitBody = null;
    this.controls.target.set(0, 0, 0);
    this.emitState({ trackingTarget: 'OFF' });
    this.log('Track mode disabled. Camera target reset to command center.', 'info');
  }

  selectPizById(pizId) {
    const id = String(pizId || '');
    const picked = this.pizSpheres.find((item) => item.data?.id === id);
    if (!picked) return false;

    this.selectedPiz = picked;
    this.notifyPizSelected(picked.data);
    this.controls.target.lerp(picked.sphere.position, 0.6);
    this.log(
      `Selected ${picked.data.id} for investigation. Targets: ${picked.data.targets}, Priority: ${picked.data.priority}`,
      'info'
    );
    return true;
  }

  zoomStep(direction = 1) {
    if (!this.camera || !this.controls) return;
    const sign = direction >= 0 ? 1 : -1;
    const target = this.controls.target.clone();
    const offset = this.camera.position.clone().sub(target);
    const currentDistance = offset.length();
    const step = Math.max(4, currentDistance * 0.15);
    const maxDistance = Number(this.controls.maxDistance || 400);
    const nextDistance = clamp(currentDistance + (sign * step), 8, maxDistance);

    if (currentDistance <= 1e-6) return;
    offset.normalize().multiplyScalar(nextDistance);
    this.camera.position.copy(target.add(offset));
    this.controls.update();
  }

  onPointerDown(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.pointer, this.camera);

    const pizTargets = this.pizSpheres.map((item) => item.sphere);
    const pizHit = this.raycaster.intersectObjects(pizTargets, false)[0];
    if (pizHit) {
      const picked = this.pizSpheres.find((item) => item.sphere === pizHit.object);
      if (picked) {
        this.selectedPiz = picked;
        this.notifyPizSelected(picked.data);
        this.log(
          `Selected ${picked.data.id} for investigation. Targets: ${picked.data.targets}, Priority: ${picked.data.priority}`,
          'info'
        );
      }
      return;
    }

    const bodyTargets = this.orbitBodies.map((item) => item.mesh).filter((mesh) => mesh.visible);
    const bodyHit = this.raycaster.intersectObjects(bodyTargets, false)[0];
    if (!bodyHit) return;

    const pickedBody = this.orbitBodies.find((item) => item.mesh === bodyHit.object);
    if (!pickedBody) return;

    this.selectedOrbitBody = pickedBody;
    this.controls.target.copy(pickedBody.mesh.position);

    this.emitState({ selectedObjectId: pickedBody.data.id });

    if (this.isTrackingMode) {
      this.trackedOrbitBody = pickedBody;
      this.emitState({ trackingTarget: pickedBody.data.id });
    }

    if (pickedBody.data.discovered) {
      this.notifyPlanetOpen(pickedBody.data);
    } else {
      this.log(`Target ${pickedBody.data.id} locked. Deploy scan to confirm classification.`, 'warning');
    }
  }

  startScan(pattern) {
    if (!this.selectedPiz) {
      this.log('No PIZ selected. Click a blue investigation sphere first.', 'warning');
      return;
    }

    const satellite = this.satellites[this.selectedSatelliteIndex];
    if (!satellite) return;

    const targetPosition = this.selectedPiz.sphere.position.clone();
    this.animateSatelliteToPosition(satellite, targetPosition, () => {
      this.startScanningSequence(satellite, pattern);
    });
  }

  animateSatelliteToPosition(satellite, targetPosition, callback) {
    this.log(`${satellite.userData.name} moving to target position...`, 'info');
    const startPosition = satellite.position.clone();
    const distance = startPosition.distanceTo(targetPosition);
    const duration = Math.max(700, distance * 12);
    let startTime = null;

    const animateMove = (time) => {
      if (!startTime) startTime = time;
      const elapsed = time - startTime;
      const progress = Math.min(elapsed / duration, 1);
      satellite.position.lerpVectors(startPosition, targetPosition, progress);

      if (progress < 1) {
        requestAnimationFrame(animateMove);
        return;
      }

      this.log(`${satellite.userData.name} arrived at target. Beginning scan...`, 'success');
      if (callback) callback();
    };

    requestAnimationFrame(animateMove);
  }

  createScanBeam(satellite) {
    const beamGeometry = new THREE.ConeGeometry(1, 10, 8);
    const beamMaterial = new THREE.MeshBasicMaterial({
      color: 0x00ffff,
      transparent: true,
      opacity: 0.28,
      side: THREE.DoubleSide,
    });
    const beam = new THREE.Mesh(beamGeometry, beamMaterial);
    beam.rotation.x = Math.PI / 2;
    beam.position.copy(satellite.position);
    this.scene.add(beam);
    this.scanBeams.push(beam);
    return beam;
  }

  startScanningSequence(satellite, pattern) {
    const scanBeam = this.createScanBeam(satellite);
    const anomalyDelay = pattern === 'grid' ? 900 : 1400;

    setTimeout(() => {
      this.log('Anomaly 23-B analyzed... High probability of stellar flare.', 'anomaly');
      setTimeout(() => {
        this.log('Anomaly 17-C analyzed... Binary star system interference.', 'anomaly');
        setTimeout(() => {
          this.log('HIGH-CONFIDENCE TRANSIT SIGNATURE DETECTED!', 'confirmed');
          this.log('Exoplanet candidate confirmed. Locking on target.', 'success');
          this.revealNearestPlanet(this.selectedPiz.sphere.position);
          this.scene.remove(scanBeam);
          this.scanBeams = this.scanBeams.filter((b) => b !== scanBeam);
        }, anomalyDelay);
      }, anomalyDelay);
    }, 1000);
  }

  revealNearestPlanet(position) {
    const hiddenBodies = this.orbitBodies.filter((item) => !item.data.discovered && item.mesh.visible);
    if (!hiddenBodies.length) {
      this.log('No hidden targets in current filter window.', 'warning');
      return;
    }

    let nearest = null;
    let minDistance = Infinity;
    hiddenBodies.forEach((item) => {
      const distance = item.mesh.position.distanceTo(position);
      if (distance < minDistance) {
        minDistance = distance;
        nearest = item;
      }
    });

    if (!nearest) return;

    nearest.data.discovered = true;
    nearest.mesh.userData.discovered = true;

    let opacity = nearest.mesh.material.opacity;
    const fadeIn = () => {
      opacity = Math.min(1, opacity + 0.03);
      nearest.mesh.material.opacity = opacity;
      if (opacity < 1) {
        requestAnimationFrame(fadeIn);
        return;
      }

      const orbitCore = nearest.orbitLine.userData?.coreLine || nearest.orbitLine;
      orbitCore.material.opacity = Math.max(orbitCore.material.opacity, 0.32);

      if (!this.discoveries.some((item) => item.id === nearest.data.id)) {
        this.discoveries.push(nearest.data);
        this.emitState({ discoveryCount: this.discoveries.length });
        this.notifyDiscovery(nearest.data);
      }

      this.notifyPlanetOpen(nearest.data);
    };

    fadeIn();
  }

  updateHud() {
    const simDate = new Date(SIM_EPOCH_MS + (this.simElapsedDays * 86400000));
    const isoText = `${simDate.toISOString().replace('T', ' ').slice(0, 19)} UTC`;
    this.emitState({ simDateText: isoText, simSpeedText: formatSpeed(this.timeScale), timeScale: this.timeScale });
  }

  onWindowResize() {
    if (!this.camera || !this.renderer) return;
    const width = this.mountElement.clientWidth || window.innerWidth;
    const height = this.mountElement.clientHeight || window.innerHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  animate(now = 0) {
    this.rafId = requestAnimationFrame(this.animate);
    if (!this.lastFrameMs) this.lastFrameMs = now;

    const deltaSeconds = Math.min((now - this.lastFrameMs) / 1000, 0.25);
    this.lastFrameMs = now;

    this.simElapsedDays += deltaSeconds * this.timeScale;
    this.updateOrbitPositions();

    if (this.isTrackingMode && this.trackedOrbitBody && this.trackedOrbitBody.mesh.visible) {
      this.controls.target.lerp(this.trackedOrbitBody.mesh.position, 0.14);
    }

    if (this.stars) {
      this.stars.rotation.y += 0.00007;
    }

    this.pizSpheres.forEach((item) => {
      item.sphere.rotation.y += 0.01;
      item.glow.rotation.y += 0.01;
    });

    this.scanBeams.forEach((beam) => {
      beam.rotation.z += 0.05;
    });

    this.hudTick += 1;
    if (this.hudTick % 2 === 0) this.updateDepthCues();
    if (this.hudTick % 6 === 0) this.updateHud();

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  async init() {
    try {
      this.initializeScene();
      this.createStarfield();
      this.createCentralStar();
      this.createSatelliteFleet();
      this.createNebula();

      await Promise.all([this.loadPizZones(), this.loadOrbitalCatalog()]);
      this.applyOrbitFilters();
      this.updateOrbitPositions();
      this.updateHud();

      this.emitState({
        dataStatus: this.dataMode,
        trackingTarget: 'OFF',
        discoveryCount: 0,
      });

      this.log('Orbital command stack online. Time controls and filters synchronized.', 'success');
      this.animate();
    } catch (error) {
      this.dataMode = 'OFFLINE';
      this.emitState({ dataStatus: 'OFFLINE' });
      this.log(`Initialization incomplete: ${error.message}`, 'warning');
      throw error;
    }
  }

  destroy() {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }

    window.removeEventListener('resize', this.onWindowResize);
    if (this.renderer?.domElement) {
      this.renderer.domElement.removeEventListener('pointerdown', this.onPointerDown);
    }

    if (this.controls) {
      this.controls.dispose();
    }

    if (this.renderer) {
      this.renderer.dispose();
      if (this.renderer.domElement && this.renderer.domElement.parentNode) {
        this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
      }
    }

    this.satellites = [];
    this.pizSpheres = [];
    this.orbitBodies = [];
    this.scanBeams = [];
    this.discoveries = [];
  }
}

export { SPEED_STEPS, formatSpeed };
